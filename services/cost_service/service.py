"""成本中心 - 业务服务层"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any

import httpx
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.config import settings
from erp_common.exceptions import BusinessException
from erp_common.utils.kafka_utils import KafkaProducer

from .models import CostSheet, CostItem, ProductCost, CostAllocationRule
from .schemas import (
    CostSheetCreate, CostSheetUpdate, CostSheetResponse,
    ProductCostCreate, ProductCostUpdate, ProductCostResponse,
    CostAllocationRuleCreate, CostAllocationRuleUpdate, CostAllocationRuleResponse,
    CalculateCostRequest, CalculateCostResponse,
    CostSheetQuery, CostCalculatedEvent,
    CostType, CostSheetStatus, AllocationMethod
)


def generate_sheet_no() -> str:
    """生成成本单号"""
    return f"CS{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


class CostCalculationService:
    """成本计算服务"""
    
    def __init__(self, db: AsyncSession, kafka: Optional[KafkaProducer] = None):
        self.db = db
        self.kafka = kafka
    
    async def calculate_purchase_cost(self, sku_id: str, quantity: Decimal, source_no: str) -> CalculateCostResponse:
        """
        计算采购成本（移动加权平均法）
        从库存服务获取最新的入库成本
        """
        # 这里模拟从库存服务获取成本
        # 实际实现中应调用库存服务的API
        unit_cost = await self._get_latest_unit_cost_from_stock(sku_id, source_no)
        
        if unit_cost is None:
            # 如果没有历史成本，返回0
            unit_cost = Decimal("0")
        
        total_cost = unit_cost * quantity
        
        return CalculateCostResponse(
            sku_id=sku_id,
            cost_type=CostType.PURCHASE.value,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            details={"method": "moving_average", "source": "stock_service"}
        )
    
    async def calculate_production_cost(self, mo_no: str, sku_id: str, quantity: Decimal) -> CalculateCostResponse:
        """
        计算生产成本（标准成本法）
        从生产订单获取实际成本
        """
        # 获取BOM和工时成本
        material_cost = await self._calculate_material_cost(sku_id, quantity)
        labor_cost = await self._calculate_labor_cost(mo_no, quantity)
        overhead_cost = await self._calculate_overhead_cost(mo_no, quantity)
        
        total_cost = material_cost + labor_cost + overhead_cost
        unit_cost = total_cost / quantity if quantity > 0 else Decimal("0")
        
        return CalculateCostResponse(
            sku_id=sku_id,
            cost_type=CostType.PRODUCTION.value,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            details={
                "material_cost": float(material_cost),
                "labor_cost": float(labor_cost),
                "overhead_cost": float(overhead_cost)
            }
        )
    
    async def _get_latest_unit_cost_from_stock(self, sku_id: str, source_no: str) -> Optional[Decimal]:
        """从库存服务获取最新单位成本"""
        # 这里应该调用库存服务API获取成本
        # 暂时返回模拟值
        return Decimal("10.00")
    
    async def _calculate_material_cost(self, sku_id: str, quantity: Decimal) -> Decimal:
        """计算原料成本"""
        # 从产品标准成本表获取标准原料成本
        result = await self.db.execute(
            select(ProductCost).where(ProductCost.sku_id == sku_id)
        )
        product_cost = result.scalar_one_or_none()
        
        if product_cost:
            return product_cost.std_material_cost * quantity
        else:
            # 如果没有标准成本，返回0
            return Decimal("0")
    
    async def _calculate_labor_cost(self, mo_no: str, quantity: Decimal) -> Decimal:
        """计算人工成本"""
        # 这里应该从生产服务获取实际工时和工资率
        # 暂时返回模拟值
        return Decimal("5.00") * quantity
    
    async def _calculate_overhead_cost(self, mo_no: str, quantity: Decimal) -> Decimal:
        """计算制造费用"""
        # 这里应该根据实际制造费用分摊规则计算
        # 暂时返回模拟值
        return Decimal("3.00") * quantity


class CostSheetService:
    """成本核算单服务"""
    
    def __init__(self, db: AsyncSession, calculation_service: CostCalculationService, kafka: Optional[KafkaProducer] = None):
        self.db = db
        self.calculation_service = calculation_service
        self.kafka = kafka
    
    async def create(self, data: CostSheetCreate, created_by: str = None) -> CostSheet:
        """创建成本核算单"""
        # 生成成本单号
        sheet_no = generate_sheet_no()
        
        # 计算各项成本
        material_cost = sum(item.amount for item in data.items if "材料" in item.item_name or "原料" in item.item_name)
        labor_cost = sum(item.amount for item in data.items if "人工" in item.item_name or "工资" in item.item_name)
        overhead_cost = sum(item.amount for item in data.items if "制造费用" in item.item_name or "间接费用" in item.item_name)
        total_cost = material_cost + labor_cost + overhead_cost
        unit_cost = total_cost / data.quantity if data.quantity > 0 else Decimal("0")
        
        # 创建成本核算单
        sheet = CostSheet(
            sheet_no=sheet_no,
            sku_id=data.sku_id,
            sku_name=data.sku_name,
            cost_type=data.cost_type.value,
            material_cost=material_cost,
            labor_cost=labor_cost,
            overhead_cost=overhead_cost,
            total_cost=total_cost,
            quantity=data.quantity,
            unit_cost=unit_cost,
            period_start=data.period_start,
            period_end=data.period_end,
            source_type=data.source_type,
            source_no=data.source_no,
            status=CostSheetStatus.DRAFT.value,
            remark=data.remark,
            created_by=created_by
        )
        self.db.add(sheet)
        await self.db.flush()
        
        # 创建成本明细
        for item in data.items:
            cost_item = CostItem(
                sheet_id=sheet.id,
                item_code=item.item_code,
                item_name=item.item_name,
                amount=item.amount,
                quantity=item.quantity,
                allocation_base=item.allocation_base.value if item.allocation_base else None,
                allocation_value=item.allocation_value,
                source_detail=item.source_detail
            )
            self.db.add(cost_item)
        
        await self.db.commit()
        await self.db.refresh(sheet)
        
        # 发布成本计算完成事件
        await self._publish_cost_calculated_event(sheet)
        
        return sheet
    
    async def get_by_id(self, sheet_id: int) -> Optional[CostSheet]:
        """根据ID获取成本核算单"""
        result = await self.db.execute(
            select(CostSheet)
            .where(CostSheet.id == sheet_id)
            .options(select.CostSheet.items)
        )
        return result.scalar_one_or_none()
    
    async def get_by_sheet_no(self, sheet_no: str) -> Optional[CostSheet]:
        """根据单号获取成本核算单"""
        result = await self.db.execute(
            select(CostSheet)
            .where(CostSheet.sheet_no == sheet_no)
            .options(select.CostSheet.items)
        )
        return result.scalar_one_or_none()
    
    async def post_sheet(self, sheet_id: int, posted_by: str) -> CostSheet:
        """过账成本核算单"""
        sheet = await self.get_by_id(sheet_id)
        if not sheet:
            raise BusinessException(code="NOT_FOUND", message="成本核算单不存在")
        
        if sheet.status != CostSheetStatus.DRAFT.value:
            raise BusinessException(code="INVALID_STATUS", message="只有草稿状态的成本单可以过账")
        
        sheet.status = CostSheetStatus.POSTED.value
        sheet.posted_by = posted_by
        sheet.posted_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(sheet)
        return sheet
    
    async def query(self, query: CostSheetQuery) -> Tuple[List[CostSheet], int]:
        """查询成本核算单"""
        stmt = select(CostSheet)
        
        if query.sku_id:
            stmt = stmt.where(CostSheet.sku_id == query.sku_id)
        if query.cost_type:
            stmt = stmt.where(CostSheet.cost_type == query.cost_type.value)
        if query.status:
            stmt = stmt.where(CostSheet.status == query.status.value)
        if query.period_start:
            stmt = stmt.where(CostSheet.period_start >= query.period_start)
        if query.period_end:
            stmt = stmt.where(CostSheet.period_end <= query.period_end)
        
        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # 分页
        stmt = stmt.order_by(CostSheet.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        
        result = await self.db.execute(stmt)
        sheets = result.scalars().all()
        
        return list(sheets), total or 0
    
    async def _publish_cost_calculated_event(self, sheet: CostSheet):
        """发布成本计算完成事件"""
        if not self.kafka:
            return
        
        event = CostCalculatedEvent(
            sheet_no=sheet.sheet_no,
            sku_id=sheet.sku_id,
            cost_type=sheet.cost_type,
            unit_cost=sheet.unit_cost,
            total_cost=sheet.total_cost
        )
        
        try:
            await self.kafka.send(
                topic="cost-events",
                key=sheet.sku_id,
                value=event.model_dump_json()
            )
        except Exception as e:
            print(f"Failed to publish CostCalculated event: {e}")


class ProductCostService:
    """产品标准成本服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, data: ProductCostCreate, created_by: str = None) -> ProductCost:
        """创建产品标准成本"""
        # 检查SKU是否已存在
        existing = await self.db.execute(
            select(ProductCost).where(ProductCost.sku_id == data.sku_id)
        )
        if existing.scalar_one_or_none():
            raise BusinessException(code="DUPLICATE_SKU", message=f"产品标准成本已存在: {data.sku_id}")
        
        # 计算总成本
        total_cost = data.std_material_cost + data.std_labor_cost + data.std_overhead_cost
        
        product_cost = ProductCost(
            sku_id=data.sku_id,
            sku_name=data.sku_name,
            std_material_cost=data.std_material_cost,
            std_labor_cost=data.std_labor_cost,
            std_overhead_cost=data.std_overhead_cost,
            std_total_cost=total_cost,
            version=data.version,
            effective_date=data.effective_date,
            remark=data.remark,
            created_by=created_by
        )
        self.db.add(product_cost)
        await self.db.commit()
        await self.db.refresh(product_cost)
        return product_cost
    
    async def get_by_sku(self, sku_id: str) -> Optional[ProductCost]:
        """根据SKU获取产品标准成本"""
        result = await self.db.execute(
            select(ProductCost).where(ProductCost.sku_id == sku_id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, sku_id: str, data: ProductCostUpdate) -> ProductCost:
        """更新产品标准成本"""
        product_cost = await self.get_by_sku(sku_id)
        if not product_cost:
            raise BusinessException(code="NOT_FOUND", message="产品标准成本不存在")
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(product_cost, key, value)
        
        # 如果更新了单项成本，重新计算总成本
        if any(field in update_data for field in ['std_material_cost', 'std_labor_cost', 'std_overhead_cost']):
            product_cost.std_total_cost = (
                product_cost.std_material_cost + 
                product_cost.std_labor_cost + 
                product_cost.std_overhead_cost
            )
        
        await self.db.commit()
        await self.db.refresh(product_cost)
        return product_cost


class CostAllocationRuleService:
    """成本分摊规则服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, data: CostAllocationRuleCreate, created_by: str = None) -> CostAllocationRule:
        """创建成本分摊规则"""
        # 检查规则编码是否已存在
        existing = await self.db.execute(
            select(CostAllocationRule).where(CostAllocationRule.rule_code == data.rule_code)
        )
        if existing.scalar_one_or_none():
            raise BusinessException(code="DUPLICATE_RULE", message=f"成本分摊规则已存在: {data.rule_code}")
        
        rule = CostAllocationRule(
            rule_code=data.rule_code,
            rule_name=data.rule_name,
            target_type=data.target_type,
            target_condition=data.target_condition,
            base_type=data.base_type,
            base_condition=data.base_condition,
            allocation_method=data.allocation_method.value,
            ratio_formula=data.ratio_formula,
            remark=data.remark,
            created_by=created_by
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule
    
    async def get_by_code(self, rule_code: str) -> Optional[CostAllocationRule]:
        """根据编码获取成本分摊规则"""
        result = await self.db.execute(
            select(CostAllocationRule).where(CostAllocationRule.rule_code == rule_code)
        )
        return result.scalar_one_or_none()
