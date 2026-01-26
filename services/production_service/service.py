"""生产中心 - 业务服务层"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Tuple

import httpx
from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from erp_common.config import settings
from erp_common.exceptions import BusinessException
from erp_common.utils.kafka_utils import KafkaProducer

from .models import BomTemplate, BomTemplateItem, MoOrder, MoDetail, MoRouting
from .schemas import (
    BomTemplateCreate, BomTemplateUpdate, BomTemplateResponse,
    MoOrderCreate, MoOrderUpdate, MoOrderResponse,
    MoReleaseRequest, MoStartRequest, MoCompleteRequest,
    MoIssueMaterialRequest, MoConsumeMaterialRequest,
    MoOrderQuery, MoOrderBrief, MoStatus, BomStatus
)


def generate_mo_no() -> str:
    """生成生产单号"""
    return f"MO{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


class BomService:
    """BOM服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, data: BomTemplateCreate) -> BomTemplate:
        """创建BOM模板"""
        # 检查编码唯一性
        existing = await self.db.execute(
            select(BomTemplate).where(BomTemplate.code == data.code)
        )
        if existing.scalar_one_or_none():
            raise BusinessException(code="DUPLICATE_CODE", message=f"BOM编码已存在: {data.code}")
        
        # 检查BOM明细数量
        if not data.items or len(data.items) == 0:
            raise BusinessException(code="EMPTY_BOM", message="BOM明细不能为空")
        
        # 创建BOM模板主表
        bom = BomTemplate(
            code=data.code,
            name=data.name,
            product_sku_id=data.product_sku_id,
            product_sku_name=data.product_sku_name,
            version=data.version,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
            remark=data.remark
        )
        self.db.add(bom)
        await self.db.flush()
        
        # 创建BOM明细
        for idx, item in enumerate(data.items, start=1):
            detail = BomTemplateItem(
                bom_id=bom.id,
                material_sku_id=item.material_sku_id,
                material_sku_name=item.material_sku_name,
                qty=item.qty,
                unit=item.unit,
                line_no=item.line_no or idx,
                remark=item.remark
            )
            self.db.add(detail)
        
        await self.db.commit()
        await self.db.refresh(bom)
        return bom
    
    async def get_by_id(self, bom_id: int) -> Optional[BomTemplate]:
        """根据ID获取BOM模板"""
        result = await self.db.execute(
            select(BomTemplate)
            .where(BomTemplate.id == bom_id)
            .options(selectinload(BomTemplate.items))
        )
        return result.scalar_one_or_none()
    
    async def get_by_code(self, code: str) -> Optional[BomTemplate]:
        """根据编码获取BOM模板"""
        result = await self.db.execute(
            select(BomTemplate)
            .where(and_(BomTemplate.code == code, BomTemplate.status == BomStatus.ACTIVE.value))
            .options(selectinload(BomTemplate.items))
        )
        return result.scalar_one_or_none()
    
    async def update(self, bom_id: int, data: BomTemplateUpdate) -> BomTemplate:
        """更新BOM模板"""
        bom = await self.get_by_id(bom_id)
        if not bom:
            raise BusinessException(code="NOT_FOUND", message="BOM模板不存在")
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(bom, key, value)
        
        await self.db.commit()
        await self.db.refresh(bom)
        return bom
    
    async def copy_to_mo(self, bom_id: int, mo_id: int, planned_qty: Decimal) -> List[MoDetail]:
        """将BOM复制到生产订单明细"""
        bom = await self.get_by_id(bom_id)
        if not bom:
            raise BusinessException(code="NOT_FOUND", message="BOM模板不存在")
        
        details = []
        for item in bom.items:
            # 按计划数量计算实际需求数量
            required_qty = item.qty * planned_qty
            
            detail = MoDetail(
                mo_id=mo_id,
                material_sku_id=item.material_sku_id,
                material_sku_name=item.material_sku_name,
                required_qty=required_qty,
                unit=item.unit,
                line_no=item.line_no
            )
            self.db.add(detail)
            details.append(detail)
        
        return details


class ProductionOrderService:
    """生产订单服务"""
    
    def __init__(self, db: AsyncSession, kafka: Optional[KafkaProducer] = None):
        self.db = db
        self.kafka = kafka
        self.bom_service = BomService(db)
    
    async def create(self, data: MoOrderCreate, created_by: str = None) -> MoOrder:
        """创建生产订单"""
        # 生成生产单号
        mo_no = generate_mo_no()
        
        # 获取BOM模板
        bom = await self.bom_service.get_by_id(data.bom_id)
        if not bom:
            raise BusinessException(code="BOM_NOT_FOUND", message="BOM模板不存在")
        
        # 创建生产订单主表
        order = MoOrder(
            mo_no=mo_no,
            product_sku_id=data.product_sku_id,
            product_sku_name=data.product_sku_name,
            planned_qty=data.planned_qty,
            bom_id=data.bom_id,
            bom_version=bom.version,
            warehouse_id=data.warehouse_id,
            raw_material_warehouse_id=data.raw_material_warehouse_id,
            planned_start_date=data.planned_start_date,
            planned_end_date=data.planned_end_date,
            status=MoStatus.DRAFT.value,
            remark=data.remark,
            created_by=created_by
        )
        self.db.add(order)
        await self.db.flush()
        
        # 从BOM复制明细
        details = await self.bom_service.copy_to_mo(data.bom_id, order.id, data.planned_qty)
        for detail in details:
            self.db.add(detail)
        
        # 创建默认工序（可后续扩展）
        routing = MoRouting(
            mo_id=order.id,
            operation_no="OP001",
            operation_name="生产加工",
            description="默认生产工序",
            priority=1
        )
        self.db.add(routing)
        
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def get_by_id(self, mo_id: int) -> Optional[MoOrder]:
        """根据ID获取生产订单"""
        result = await self.db.execute(
            select(MoOrder)
            .where(MoOrder.id == mo_id)
            .options(selectinload(MoOrder.details), selectinload(MoOrder.routings))
        )
        return result.scalar_one_or_none()
    
    async def get_by_mo_no(self, mo_no: str) -> Optional[MoOrder]:
        """根据单号获取生产订单"""
        result = await self.db.execute(
            select(MoOrder)
            .where(MoOrder.mo_no == mo_no)
            .options(selectinload(MoOrder.details), selectinload(MoOrder.routings))
        )
        return result.scalar_one_or_none()
    
    async def release(self, mo_id: int) -> MoOrder:
        """下达生产订单"""
        order = await self.get_by_id(mo_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="生产订单不存在")
        
        if order.status != MoStatus.DRAFT.value:
            raise BusinessException(code="INVALID_STATUS", message="只有草稿状态的订单可以下达")
        
        order.status = MoStatus.RELEASED.value
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def start(self, mo_id: int) -> MoOrder:
        """开工生产订单"""
        order = await self.get_by_id(mo_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="生产订单不存在")
        
        if order.status != MoStatus.RELEASED.value:
            raise BusinessException(code="INVALID_STATUS", message="只有已下达状态的订单可以开工")
        
        order.status = MoStatus.STARTED.value
        order.actual_start_date = date.today()
        
        await self.db.commit()
        await self.db.refresh(order)
        
        # 发布开工事件
        await self._publish_started_event(order)
        
        return order
    
    async def complete(self, mo_id: int, request: MoCompleteRequest) -> MoOrder:
        """完工生产订单"""
        order = await self.get_by_id(mo_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="生产订单不存在")
        
        if order.status != MoStatus.STARTED.value:
            raise BusinessException(code="INVALID_STATUS", message="只有已开工状态的订单可以完工")
        
        order.status = MoStatus.COMPLETED.value
        order.actual_end_date = request.actual_end_date or date.today()
        
        await self.db.commit()
        await self.db.refresh(order)
        
        # 发布完工事件
        await self._publish_completed_event(order)
        
        return order
    
    async def issue_material(self, mo_id: int, request: MoIssueMaterialRequest, operator: str) -> MoOrder:
        """发料"""
        order = await self.get_by_id(mo_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="生产订单不存在")
        
        if order.status not in [MoStatus.RELEASED.value, MoStatus.STARTED.value]:
            raise BusinessException(code="INVALID_STATUS", message="订单状态不允许发料")
        
        # 更新明细中的已发料数量
        detail_map = {d.material_sku_id: d for d in order.details}
        
        for item in request.items:
            sku_id = item["sku_id"]
            qty = Decimal(str(item["qty"]))
            
            detail = detail_map.get(sku_id)
            if not detail:
                raise BusinessException(code="MATERIAL_NOT_FOUND", message=f"物料不在生产订单中: {sku_id}")
            
            if detail.issued_qty + qty > detail.required_qty:
                raise BusinessException(
                    code="EXCEED_REQUIRED_QTY",
                    message=f"发料数量超过需求数量: SKU={sku_id}, 需求={detail.required_qty}, 已发={detail.issued_qty}, 本次={qty}"
                )
            
            detail.issued_qty += qty
        
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def consume_material(self, mo_id: int, request: MoConsumeMaterialRequest, operator: str) -> MoOrder:
        """消耗物料"""
        order = await self.get_by_id(mo_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="生产订单不存在")
        
        if order.status != MoStatus.STARTED.value:
            raise BusinessException(code="INVALID_STATUS", message="只有已开工状态的订单可以消耗物料")
        
        # 更新明细中的已消耗数量
        detail_map = {d.material_sku_id: d for d in order.details}
        
        for item in request.items:
            sku_id = item["sku_id"]
            qty = Decimal(str(item["qty"]))
            
            detail = detail_map.get(sku_id)
            if not detail:
                raise BusinessException(code="MATERIAL_NOT_FOUND", message=f"物料不在生产订单中: {sku_id}")
            
            if detail.consumed_qty + qty > detail.issued_qty:
                raise BusinessException(
                    code="EXCEED_ISSUED_QTY",
                    message=f"消耗数量超过已发料数量: SKU={sku_id}, 已发={detail.issued_qty}, 已消耗={detail.consumed_qty}, 本次={qty}"
                )
            
            detail.consumed_qty += qty
        
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def query(self, query: MoOrderQuery) -> Tuple[List[MoOrderBrief], int]:
        """查询生产订单列表"""
        stmt = select(MoOrder)
        
        if query.mo_no:
            stmt = stmt.where(MoOrder.mo_no.contains(query.mo_no))
        if query.product_sku_id:
            stmt = stmt.where(MoOrder.product_sku_id == query.product_sku_id)
        if query.status:
            stmt = stmt.where(MoOrder.status == query.status.value)
        if query.start_date:
            stmt = stmt.where(MoOrder.planned_start_date >= query.start_date)
        if query.end_date:
            stmt = stmt.where(MoOrder.planned_start_date <= query.end_date)
        
        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # 分页
        stmt = stmt.order_by(MoOrder.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        
        result = await self.db.execute(stmt)
        orders = result.scalars().all()
        
        return [MoOrderBrief.model_validate(o) for o in orders], total or 0
    
    async def cancel(self, mo_id: int) -> MoOrder:
        """取消生产订单"""
        order = await self.get_by_id(mo_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="生产订单不存在")
        
        if order.status not in [MoStatus.DRAFT.value, MoStatus.RELEASED.value]:
            raise BusinessException(code="INVALID_STATUS", message="当前状态不允许取消")
        
        order.status = MoStatus.CANCELLED.value
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def _publish_started_event(self, order: MoOrder):
        """发布生产订单开工事件"""
        if not self.kafka:
            return
        
        from .schemas import MoStartedEvent
        event = MoStartedEvent(
            mo_no=order.mo_no,
            product_sku_id=order.product_sku_id,
            planned_qty=order.planned_qty,
            warehouse_id=order.warehouse_id,
            raw_material_warehouse_id=order.raw_material_warehouse_id
        )
        
        try:
            await self.kafka.send(
                topic="production-events",
                key=order.mo_no,
                value=event.model_dump_json()
            )
        except Exception as e:
            print(f"Failed to publish MoStarted event: {e}")
    
    async def _publish_completed_event(self, order: MoOrder):
        """发布生产订单完工事件"""
        if not self.kafka:
            return
        
        from .schemas import MoCompletedEvent
        event = MoCompletedEvent(
            mo_no=order.mo_no,
            product_sku_id=order.product_sku_id,
            planned_qty=order.planned_qty,
            actual_qty=order.planned_qty  # 简化处理，实际可能需要报工数量
        )
        
        try:
            await self.kafka.send(
                topic="production-events",
                key=order.mo_no,
                value=event.model_dump_json()
            )
        except Exception as e:
            print(f"Failed to publish MoCompleted event: {e}")
