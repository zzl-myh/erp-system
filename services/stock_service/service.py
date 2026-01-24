"""库存中心 - 业务服务层"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.exceptions import BusinessException
from erp_common.utils.kafka_utils import KafkaProducer
from erp_common.utils.redis_utils import RedisClient

from .models import Stock, StockDetail, StockMove, StockLock
from .schemas import (
    StockInRequest, StockInItem, StockInResponse,
    StockOutRequest, StockOutItem, StockOutResponse,
    StockLockRequest, StockLockResponse,
    StockUnlockRequest, StockUnlockResponse,
    StockResponse, StockWithDetails, StockDetailResponse,
    StockMoveResponse, StockMoveQuery, StockLockRecordResponse,
    StockChangedEvent, MoveType, SourceType
)


def generate_move_no() -> str:
    """生成流水号"""
    return f"MV{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"


def generate_lock_no() -> str:
    """生成锁定单号"""
    return f"LK{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"


def generate_batch_no() -> str:
    """生成批次号"""
    return f"BN{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"


class StockService:
    """库存服务"""
    
    def __init__(self, db: AsyncSession, kafka: Optional[KafkaProducer] = None, redis: Optional[RedisClient] = None):
        self.db = db
        self.kafka = kafka
        self.redis = redis
    
    async def get_stock(self, sku_id: str, warehouse_id: int) -> Optional[Stock]:
        """获取库存记录"""
        result = await self.db.execute(
            select(Stock).where(
                and_(Stock.sku_id == sku_id, Stock.warehouse_id == warehouse_id)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_or_create_stock(self, sku_id: str, warehouse_id: int) -> Stock:
        """获取或创建库存记录"""
        stock = await self.get_stock(sku_id, warehouse_id)
        if not stock:
            stock = Stock(
                sku_id=sku_id,
                warehouse_id=warehouse_id,
                qty=Decimal("0"),
                locked_qty=Decimal("0"),
                available_qty=Decimal("0"),
                avg_cost=Decimal("0")
            )
            self.db.add(stock)
            await self.db.flush()
        return stock
    
    async def stock_in(self, request: StockInRequest, operator: str = None) -> StockInResponse:
        """
        库存入库
        - 更新库存主表数量和成本（移动加权平均）
        - 创建批次明细
        - 记录库存流水
        - 发布库存变动事件
        """
        move_nos = []
        
        for item in request.items:
            # 1. 获取或创建库存记录
            stock = await self.get_or_create_stock(item.sku_id, request.warehouse_id)
            before_qty = stock.qty
            
            # 2. 计算移动加权平均成本
            if stock.qty + item.qty > 0:
                total_value = stock.qty * stock.avg_cost + item.qty * item.unit_cost
                stock.avg_cost = total_value / (stock.qty + item.qty)
            
            # 3. 更新库存数量
            stock.qty += item.qty
            stock.available_qty = stock.qty - stock.locked_qty
            
            # 4. 创建批次明细
            batch_no = item.batch_no or generate_batch_no()
            detail = StockDetail(
                stock_id=stock.id,
                sku_id=item.sku_id,
                warehouse_id=request.warehouse_id,
                batch_no=batch_no,
                production_date=item.production_date,
                expiry_date=item.expiry_date,
                qty=item.qty,
                locked_qty=Decimal("0"),
                unit_cost=item.unit_cost,
                source_type=request.source_type.value,
                source_order_no=request.source_order_no
            )
            self.db.add(detail)
            
            # 5. 记录库存流水
            move_no = generate_move_no()
            move = StockMove(
                move_no=move_no,
                sku_id=item.sku_id,
                warehouse_id=request.warehouse_id,
                move_type=MoveType.IN.value,
                qty=item.qty,
                before_qty=before_qty,
                after_qty=stock.qty,
                unit_cost=item.unit_cost,
                source_type=request.source_type.value,
                source_order_no=request.source_order_no,
                batch_no=batch_no,
                remark=request.remark,
                operator=operator
            )
            self.db.add(move)
            move_nos.append(move_no)
            
            # 6. 发布库存变动事件
            await self._publish_stock_event(
                sku_id=item.sku_id,
                warehouse_id=request.warehouse_id,
                move_type=MoveType.IN.value,
                qty=item.qty,
                before_qty=before_qty,
                after_qty=stock.qty,
                source_type=request.source_type.value,
                source_order_no=request.source_order_no
            )
        
        await self.db.commit()
        return StockInResponse(success=True, move_nos=move_nos, message="入库成功")
    
    async def stock_out(self, request: StockOutRequest, operator: str = None) -> StockOutResponse:
        """
        库存出库
        - 校验可用库存
        - FIFO 扣减批次明细
        - 更新库存主表
        - 记录库存流水
        - 发布库存变动事件
        """
        move_nos = []
        total_cost = Decimal("0")
        
        for item in request.items:
            # 1. 获取库存记录
            stock = await self.get_stock(item.sku_id, request.warehouse_id)
            if not stock:
                raise BusinessException(
                    code="STOCK_NOT_FOUND",
                    message=f"库存记录不存在: SKU={item.sku_id}, 仓库={request.warehouse_id}"
                )
            
            # 2. 校验可用库存
            if stock.available_qty < item.qty:
                raise BusinessException(
                    code="INSUFFICIENT_STOCK",
                    message=f"可用库存不足: SKU={item.sku_id}, 可用={stock.available_qty}, 需要={item.qty}"
                )
            
            before_qty = stock.qty
            remaining_qty = item.qty
            out_cost = Decimal("0")
            
            # 3. FIFO 扣减批次明细
            details = await self._get_available_details(item.sku_id, request.warehouse_id, item.batch_no)
            for detail in details:
                if remaining_qty <= 0:
                    break
                
                available = detail.qty - detail.locked_qty
                deduct_qty = min(available, remaining_qty)
                
                detail.qty -= deduct_qty
                out_cost += deduct_qty * detail.unit_cost
                remaining_qty -= deduct_qty
            
            if remaining_qty > 0:
                raise BusinessException(
                    code="INSUFFICIENT_BATCH_STOCK",
                    message=f"批次库存不足以扣减: SKU={item.sku_id}"
                )
            
            # 4. 更新库存主表
            stock.qty -= item.qty
            stock.available_qty = stock.qty - stock.locked_qty
            total_cost += out_cost
            
            # 5. 记录库存流水
            move_no = generate_move_no()
            move = StockMove(
                move_no=move_no,
                sku_id=item.sku_id,
                warehouse_id=request.warehouse_id,
                move_type=MoveType.OUT.value,
                qty=item.qty,
                before_qty=before_qty,
                after_qty=stock.qty,
                unit_cost=out_cost / item.qty if item.qty > 0 else Decimal("0"),
                source_type=request.source_type.value,
                source_order_no=request.source_order_no,
                batch_no=item.batch_no,
                remark=request.remark,
                operator=operator
            )
            self.db.add(move)
            move_nos.append(move_no)
            
            # 6. 发布库存变动事件
            await self._publish_stock_event(
                sku_id=item.sku_id,
                warehouse_id=request.warehouse_id,
                move_type=MoveType.OUT.value,
                qty=item.qty,
                before_qty=before_qty,
                after_qty=stock.qty,
                source_type=request.source_type.value,
                source_order_no=request.source_order_no
            )
        
        await self.db.commit()
        return StockOutResponse(success=True, move_nos=move_nos, total_cost=total_cost, message="出库成功")
    
    async def lock_stock(self, request: StockLockRequest, operator: str = None) -> StockLockResponse:
        """
        锁定库存
        - 校验可用库存
        - 更新库存主表锁定数量
        - 创建锁定记录
        - 记录库存流水
        """
        lock_nos = []
        
        for item in request.items:
            # 1. 获取库存记录
            stock = await self.get_stock(item.sku_id, request.warehouse_id)
            if not stock:
                raise BusinessException(
                    code="STOCK_NOT_FOUND",
                    message=f"库存记录不存在: SKU={item.sku_id}"
                )
            
            # 2. 校验可用库存
            if stock.available_qty < item.qty:
                raise BusinessException(
                    code="INSUFFICIENT_AVAILABLE_STOCK",
                    message=f"可用库存不足: SKU={item.sku_id}, 可用={stock.available_qty}, 需要={item.qty}"
                )
            
            # 3. 更新库存锁定数量
            before_locked = stock.locked_qty
            stock.locked_qty += item.qty
            stock.available_qty = stock.qty - stock.locked_qty
            
            # 4. 创建锁定记录
            lock_no = generate_lock_no()
            lock_record = StockLock(
                lock_no=lock_no,
                sku_id=item.sku_id,
                warehouse_id=request.warehouse_id,
                locked_qty=item.qty,
                status="LOCKED",
                source_type=request.source_type,
                source_order_no=request.source_order_no,
                operator=operator
            )
            self.db.add(lock_record)
            lock_nos.append(lock_no)
            
            # 5. 记录库存流水
            move_no = generate_move_no()
            move = StockMove(
                move_no=move_no,
                sku_id=item.sku_id,
                warehouse_id=request.warehouse_id,
                move_type=MoveType.LOCK.value,
                qty=item.qty,
                before_qty=before_locked,
                after_qty=stock.locked_qty,
                unit_cost=Decimal("0"),
                source_type=request.source_type,
                source_order_no=request.source_order_no,
                operator=operator
            )
            self.db.add(move)
        
        await self.db.commit()
        return StockLockResponse(success=True, lock_nos=lock_nos, message="锁定成功")
    
    async def unlock_stock(self, request: StockUnlockRequest, operator: str = None) -> StockUnlockResponse:
        """
        解锁库存
        - 根据锁定单号或来源单号查找锁定记录
        - 更新库存主表锁定数量
        - 更新锁定记录状态
        - 记录库存流水
        """
        # 查找锁定记录
        query = select(StockLock).where(StockLock.status == "LOCKED")
        
        if request.lock_nos:
            query = query.where(StockLock.lock_no.in_(request.lock_nos))
        elif request.source_order_no:
            query = query.where(StockLock.source_order_no == request.source_order_no)
        else:
            raise BusinessException(code="INVALID_REQUEST", message="必须提供锁定单号或来源单号")
        
        result = await self.db.execute(query)
        lock_records = result.scalars().all()
        
        if not lock_records:
            raise BusinessException(code="LOCK_NOT_FOUND", message="未找到有效的锁定记录")
        
        unlocked_count = 0
        
        for lock_record in lock_records:
            # 获取库存记录
            stock = await self.get_stock(lock_record.sku_id, lock_record.warehouse_id)
            if stock:
                before_locked = stock.locked_qty
                stock.locked_qty -= lock_record.locked_qty
                stock.available_qty = stock.qty - stock.locked_qty
                
                # 记录库存流水
                move_no = generate_move_no()
                move = StockMove(
                    move_no=move_no,
                    sku_id=lock_record.sku_id,
                    warehouse_id=lock_record.warehouse_id,
                    move_type=MoveType.UNLOCK.value,
                    qty=lock_record.locked_qty,
                    before_qty=before_locked,
                    after_qty=stock.locked_qty,
                    unit_cost=Decimal("0"),
                    source_type=lock_record.source_type,
                    source_order_no=lock_record.source_order_no,
                    operator=operator
                )
                self.db.add(move)
            
            # 更新锁定记录状态
            lock_record.status = "UNLOCKED"
            lock_record.unlocked_at = datetime.utcnow()
            unlocked_count += 1
        
        await self.db.commit()
        return StockUnlockResponse(success=True, unlocked_count=unlocked_count, message="解锁成功")
    
    async def consume_locked_stock(self, source_order_no: str, operator: str = None) -> StockOutResponse:
        """
        消耗锁定库存（用于订单支付后出库）
        - 查找订单的锁定记录
        - 执行出库
        - 更新锁定记录状态为已消耗
        """
        # 查找锁定记录
        result = await self.db.execute(
            select(StockLock).where(
                and_(
                    StockLock.source_order_no == source_order_no,
                    StockLock.status == "LOCKED"
                )
            )
        )
        lock_records = result.scalars().all()
        
        if not lock_records:
            raise BusinessException(code="LOCK_NOT_FOUND", message=f"未找到订单 {source_order_no} 的锁定记录")
        
        move_nos = []
        total_cost = Decimal("0")
        
        for lock_record in lock_records:
            # 获取库存记录
            stock = await self.get_stock(lock_record.sku_id, lock_record.warehouse_id)
            if not stock:
                continue
            
            before_qty = stock.qty
            remaining_qty = lock_record.locked_qty
            out_cost = Decimal("0")
            
            # FIFO 扣减批次明细
            details = await self._get_available_details(lock_record.sku_id, lock_record.warehouse_id, None)
            for detail in details:
                if remaining_qty <= 0:
                    break
                
                deduct_qty = min(detail.qty, remaining_qty)
                detail.qty -= deduct_qty
                out_cost += deduct_qty * detail.unit_cost
                remaining_qty -= deduct_qty
            
            # 更新库存主表
            stock.qty -= lock_record.locked_qty
            stock.locked_qty -= lock_record.locked_qty
            stock.available_qty = stock.qty - stock.locked_qty
            total_cost += out_cost
            
            # 记录库存流水
            move_no = generate_move_no()
            move = StockMove(
                move_no=move_no,
                sku_id=lock_record.sku_id,
                warehouse_id=lock_record.warehouse_id,
                move_type=MoveType.OUT.value,
                qty=lock_record.locked_qty,
                before_qty=before_qty,
                after_qty=stock.qty,
                unit_cost=out_cost / lock_record.locked_qty if lock_record.locked_qty > 0 else Decimal("0"),
                source_type="SALE",
                source_order_no=source_order_no,
                operator=operator
            )
            self.db.add(move)
            move_nos.append(move_no)
            
            # 更新锁定记录状态
            lock_record.status = "CONSUMED"
            lock_record.unlocked_at = datetime.utcnow()
            
            # 发布库存变动事件
            await self._publish_stock_event(
                sku_id=lock_record.sku_id,
                warehouse_id=lock_record.warehouse_id,
                move_type=MoveType.OUT.value,
                qty=lock_record.locked_qty,
                before_qty=before_qty,
                after_qty=stock.qty,
                source_type="SALE",
                source_order_no=source_order_no
            )
        
        await self.db.commit()
        return StockOutResponse(success=True, move_nos=move_nos, total_cost=total_cost, message="出库成功")
    
    async def get_stock_info(self, sku_id: str, warehouse_id: int) -> Optional[StockWithDetails]:
        """获取库存详情（含批次明细）"""
        stock = await self.get_stock(sku_id, warehouse_id)
        if not stock:
            return None
        
        # 获取批次明细
        result = await self.db.execute(
            select(StockDetail).where(
                and_(
                    StockDetail.sku_id == sku_id,
                    StockDetail.warehouse_id == warehouse_id,
                    StockDetail.qty > 0
                )
            ).order_by(StockDetail.created_at)
        )
        details = result.scalars().all()
        
        return StockWithDetails(
            id=stock.id,
            sku_id=stock.sku_id,
            warehouse_id=stock.warehouse_id,
            qty=stock.qty,
            locked_qty=stock.locked_qty,
            available_qty=stock.available_qty,
            avg_cost=stock.avg_cost,
            created_at=stock.created_at,
            updated_at=stock.updated_at,
            details=[StockDetailResponse.model_validate(d) for d in details]
        )
    
    async def query_stock_moves(self, query: StockMoveQuery) -> Tuple[List[StockMoveResponse], int]:
        """查询库存流水"""
        stmt = select(StockMove)
        
        if query.sku_id:
            stmt = stmt.where(StockMove.sku_id == query.sku_id)
        if query.warehouse_id:
            stmt = stmt.where(StockMove.warehouse_id == query.warehouse_id)
        if query.move_type:
            stmt = stmt.where(StockMove.move_type == query.move_type.value)
        if query.source_type:
            stmt = stmt.where(StockMove.source_type == query.source_type.value)
        if query.source_order_no:
            stmt = stmt.where(StockMove.source_order_no == query.source_order_no)
        if query.start_time:
            stmt = stmt.where(StockMove.created_at >= query.start_time)
        if query.end_time:
            stmt = stmt.where(StockMove.created_at <= query.end_time)
        
        # 总数
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # 分页
        stmt = stmt.order_by(StockMove.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        
        result = await self.db.execute(stmt)
        moves = result.scalars().all()
        
        return [StockMoveResponse.model_validate(m) for m in moves], total or 0
    
    async def _get_available_details(
        self, sku_id: str, warehouse_id: int, batch_no: Optional[str]
    ) -> List[StockDetail]:
        """获取可用批次明细（FIFO 排序）"""
        stmt = select(StockDetail).where(
            and_(
                StockDetail.sku_id == sku_id,
                StockDetail.warehouse_id == warehouse_id,
                StockDetail.qty > 0
            )
        )
        
        if batch_no:
            stmt = stmt.where(StockDetail.batch_no == batch_no)
        
        stmt = stmt.order_by(StockDetail.created_at)  # FIFO
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _publish_stock_event(
        self,
        sku_id: str,
        warehouse_id: int,
        move_type: str,
        qty: Decimal,
        before_qty: Decimal,
        after_qty: Decimal,
        source_type: str,
        source_order_no: Optional[str]
    ):
        """发布库存变动事件"""
        if not self.kafka:
            return
        
        event = StockChangedEvent(
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            move_type=move_type,
            qty=qty,
            before_qty=before_qty,
            after_qty=after_qty,
            source_type=source_type,
            source_order_no=source_order_no
        )
        
        try:
            await self.kafka.send(
                topic="stock-events",
                key=sku_id,
                value=event.model_dump_json()
            )
        except Exception as e:
            # 记录日志但不影响主流程
            print(f"Failed to publish stock event: {e}")
