"""采购中心 - 业务服务层"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Tuple

import httpx
from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.config import settings
from erp_common.exceptions import BusinessException
from erp_common.utils.kafka_utils import KafkaProducer

from .models import Supplier, PoOrder, PoDetail, PoReceive, PoReceiveDetail
from .schemas import (
    SupplierCreate, SupplierUpdate, SupplierResponse,
    PoOrderCreate, PoOrderUpdate, PoOrderResponse, PoOrderBrief, PoOrderQuery,
    PoApproveRequest, PoReceiveRequest, PoReceiveResponse,
    PoApprovedEvent, PoInStockEvent, PoStatus
)


def generate_po_no() -> str:
    """生成采购单号"""
    return f"PO{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


def generate_receive_no() -> str:
    """生成收货单号"""
    return f"RV{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


class SupplierService:
    """供应商服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, data: SupplierCreate) -> Supplier:
        """创建供应商"""
        # 检查编码唯一性
        existing = await self.db.execute(
            select(Supplier).where(Supplier.code == data.code)
        )
        if existing.scalar_one_or_none():
            raise BusinessException(code="DUPLICATE_CODE", message=f"供应商编码已存在: {data.code}")
        
        supplier = Supplier(**data.model_dump())
        self.db.add(supplier)
        await self.db.commit()
        await self.db.refresh(supplier)
        return supplier
    
    async def get_by_id(self, supplier_id: int) -> Optional[Supplier]:
        """根据ID获取供应商"""
        result = await self.db.execute(
            select(Supplier).where(Supplier.id == supplier_id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, supplier_id: int, data: SupplierUpdate) -> Supplier:
        """更新供应商"""
        supplier = await self.get_by_id(supplier_id)
        if not supplier:
            raise BusinessException(code="NOT_FOUND", message="供应商不存在")
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(supplier, key, value)
        
        await self.db.commit()
        await self.db.refresh(supplier)
        return supplier
    
    async def list_suppliers(self, status: Optional[str] = None, page: int = 1, page_size: int = 20) -> Tuple[List[Supplier], int]:
        """供应商列表"""
        stmt = select(Supplier)
        
        if status:
            stmt = stmt.where(Supplier.status == status)
        
        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # 分页
        stmt = stmt.order_by(Supplier.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total or 0


class PurchaseOrderService:
    """采购订单服务"""
    
    def __init__(self, db: AsyncSession, kafka: Optional[KafkaProducer] = None):
        self.db = db
        self.kafka = kafka
    
    async def create(self, data: PoOrderCreate, created_by: str = None) -> PoOrder:
        """创建采购订单"""
        # 生成采购单号
        po_no = generate_po_no()
        
        # 创建订单主表
        order = PoOrder(
            po_no=po_no,
            supplier_id=data.supplier_id,
            warehouse_id=data.warehouse_id,
            expected_date=data.expected_date,
            remark=data.remark,
            status=PoStatus.DRAFT.value,
            order_date=date.today(),
            created_by=created_by
        )
        self.db.add(order)
        await self.db.flush()
        
        # 创建订单明细
        total_qty = Decimal("0")
        total_amount = Decimal("0")
        total_tax = Decimal("0")
        
        for idx, item in enumerate(data.details, start=1):
            # 计算金额
            amount = item.qty * item.unit_price
            tax_amount = amount * item.tax_rate / 100
            line_total = amount + tax_amount
            
            detail = PoDetail(
                po_id=order.id,
                sku_id=item.sku_id,
                sku_name=item.sku_name,
                qty=item.qty,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate,
                amount=amount,
                tax_amount=tax_amount,
                total_amount=line_total,
                line_no=idx,
                remark=item.remark
            )
            self.db.add(detail)
            
            total_qty += item.qty
            total_amount += amount
            total_tax += tax_amount
        
        # 更新订单汇总
        order.total_qty = total_qty
        order.total_amount = total_amount
        order.tax_amount = total_tax
        order.payable_amount = total_amount + total_tax
        
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def get_by_id(self, po_id: int) -> Optional[PoOrder]:
        """根据ID获取采购订单"""
        result = await self.db.execute(
            select(PoOrder).where(PoOrder.id == po_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_po_no(self, po_no: str) -> Optional[PoOrder]:
        """根据单号获取采购订单"""
        result = await self.db.execute(
            select(PoOrder).where(PoOrder.po_no == po_no)
        )
        return result.scalar_one_or_none()
    
    async def submit(self, po_id: int) -> PoOrder:
        """提交审批"""
        order = await self.get_by_id(po_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="采购订单不存在")
        
        if order.status != PoStatus.DRAFT.value:
            raise BusinessException(code="INVALID_STATUS", message="只有草稿状态的订单可以提交审批")
        
        order.status = PoStatus.PENDING.value
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def approve(self, po_id: int, request: PoApproveRequest, approved_by: str) -> PoOrder:
        """审批采购订单"""
        order = await self.get_by_id(po_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="采购订单不存在")
        
        if order.status != PoStatus.PENDING.value:
            raise BusinessException(code="INVALID_STATUS", message="只有待审批状态的订单可以审批")
        
        if request.approved:
            order.status = PoStatus.APPROVED.value
            order.approved_by = approved_by
            order.approved_at = datetime.utcnow()
            
            # 发布审批通过事件
            await self._publish_approved_event(order, approved_by)
        else:
            if not request.reject_reason:
                raise BusinessException(code="REJECT_REASON_REQUIRED", message="拒绝时必须填写原因")
            order.status = PoStatus.REJECTED.value
            order.reject_reason = request.reject_reason
        
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def receive(self, request: PoReceiveRequest, receiver: str) -> PoReceiveResponse:
        """采购收货"""
        order = await self.get_by_id(request.po_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="采购订单不存在")
        
        if order.status not in [PoStatus.APPROVED.value, PoStatus.RECEIVING.value]:
            raise BusinessException(code="INVALID_STATUS", message="订单状态不允许收货")
        
        # 创建收货单
        receive_no = generate_receive_no()
        receive = PoReceive(
            receive_no=receive_no,
            po_id=order.id,
            receive_date=date.today(),
            receiver=receiver,
            status="RECEIVED",
            remark=request.remark
        )
        self.db.add(receive)
        await self.db.flush()
        
        # 获取采购明细映射
        detail_map = {d.id: d for d in order.details}
        
        # 创建收货明细并更新采购明细
        stock_items = []
        for item in request.details:
            po_detail = detail_map.get(item.po_detail_id)
            if not po_detail:
                raise BusinessException(code="DETAIL_NOT_FOUND", message=f"采购明细不存在: {item.po_detail_id}")
            
            # 检查收货数量
            remaining = po_detail.qty - po_detail.received_qty
            if item.qty > remaining:
                raise BusinessException(
                    code="EXCEED_QTY",
                    message=f"收货数量超过待收数量: SKU={item.sku_id}, 待收={remaining}, 实收={item.qty}"
                )
            
            # 计算入库成本（含税单价）
            unit_cost = po_detail.total_amount / po_detail.qty if po_detail.qty > 0 else Decimal("0")
            
            receive_detail = PoReceiveDetail(
                receive_id=receive.id,
                po_detail_id=item.po_detail_id,
                sku_id=item.sku_id,
                qty=item.qty,
                unit_cost=unit_cost,
                batch_no=item.batch_no,
                production_date=item.production_date,
                expiry_date=item.expiry_date
            )
            self.db.add(receive_detail)
            
            # 更新采购明细已收货数量
            po_detail.received_qty += item.qty
            
            # 准备入库数据
            stock_items.append({
                "sku_id": item.sku_id,
                "qty": float(item.qty),
                "unit_cost": float(unit_cost),
                "batch_no": item.batch_no,
                "production_date": item.production_date.isoformat() if item.production_date else None,
                "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None
            })
        
        # 检查是否全部收货完成
        all_received = all(d.received_qty >= d.qty for d in order.details)
        if all_received:
            order.status = PoStatus.COMPLETED.value
        else:
            order.status = PoStatus.RECEIVING.value
        
        await self.db.commit()
        
        # 调用库存服务入库
        await self._call_stock_in(order.warehouse_id, order.po_no, stock_items)
        
        # 更新收货单状态为已入库
        receive.status = "IN_STOCK"
        await self.db.commit()
        
        # 发布入库事件
        await self._publish_in_stock_event(order.po_no, receive_no, order.warehouse_id, stock_items)
        
        await self.db.refresh(receive)
        return PoReceiveResponse.model_validate(receive)
    
    async def query(self, query: PoOrderQuery) -> Tuple[List[PoOrderBrief], int]:
        """查询采购订单列表"""
        stmt = select(PoOrder)
        
        if query.po_no:
            stmt = stmt.where(PoOrder.po_no.contains(query.po_no))
        if query.supplier_id:
            stmt = stmt.where(PoOrder.supplier_id == query.supplier_id)
        if query.status:
            stmt = stmt.where(PoOrder.status == query.status.value)
        if query.start_date:
            stmt = stmt.where(PoOrder.order_date >= query.start_date)
        if query.end_date:
            stmt = stmt.where(PoOrder.order_date <= query.end_date)
        
        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # 分页
        stmt = stmt.order_by(PoOrder.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        
        result = await self.db.execute(stmt)
        orders = result.scalars().all()
        
        return [PoOrderBrief.model_validate(o) for o in orders], total or 0
    
    async def cancel(self, po_id: int) -> PoOrder:
        """取消采购订单"""
        order = await self.get_by_id(po_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="采购订单不存在")
        
        if order.status not in [PoStatus.DRAFT.value, PoStatus.PENDING.value, PoStatus.REJECTED.value]:
            raise BusinessException(code="INVALID_STATUS", message="当前状态不允许取消")
        
        order.status = PoStatus.CANCELLED.value
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def _call_stock_in(self, warehouse_id: int, source_order_no: str, items: List[dict]):
        """调用库存服务入库"""
        stock_service_url = getattr(settings, 'stock_service_url', 'http://localhost:8002')
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{stock_service_url}/stock/in",
                    json={
                        "warehouse_id": warehouse_id,
                        "source_type": "PURCHASE",
                        "source_order_no": source_order_no,
                        "items": items
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise BusinessException(
                        code="STOCK_IN_FAILED",
                        message=f"库存入库失败: {response.text}"
                    )
        except httpx.RequestError as e:
            raise BusinessException(
                code="STOCK_SERVICE_ERROR",
                message=f"调用库存服务失败: {str(e)}"
            )
    
    async def _publish_approved_event(self, order: PoOrder, approved_by: str):
        """发布采购订单审批通过事件"""
        if not self.kafka:
            return
        
        event = PoApprovedEvent(
            po_no=order.po_no,
            supplier_id=order.supplier_id,
            warehouse_id=order.warehouse_id,
            total_amount=order.payable_amount,
            approved_by=approved_by
        )
        
        try:
            await self.kafka.send(
                topic="purchase-events",
                key=order.po_no,
                value=event.model_dump_json()
            )
        except Exception as e:
            print(f"Failed to publish PoApproved event: {e}")
    
    async def _publish_in_stock_event(self, po_no: str, receive_no: str, warehouse_id: int, items: List[dict]):
        """发布采购入库事件"""
        if not self.kafka:
            return
        
        event = PoInStockEvent(
            po_no=po_no,
            receive_no=receive_no,
            warehouse_id=warehouse_id,
            items=items
        )
        
        try:
            await self.kafka.send(
                topic="purchase-events",
                key=po_no,
                value=event.model_dump_json()
            )
        except Exception as e:
            print(f"Failed to publish PoInStock event: {e}")
