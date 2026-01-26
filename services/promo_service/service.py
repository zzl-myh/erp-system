"""促销中心 - 业务服务层"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
import json

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from erp_common.config import settings
from erp_common.exceptions import BusinessException
from erp_common.utils.kafka_utils import KafkaProducer

from .models import Promo, PromoRule, PromoRecord, PromoCombination
from .schemas import (
    PromoCreate, PromoUpdate, PromoResponse,
    PromoRuleCreate, PromoRuleResponse,
    PromoRecordCreate, PromoRecordResponse,
    PromoCombinationCreate, PromoCombinationUpdate, PromoCombinationResponse,
    CalcPromoRequest, CalcPromoResponse,
    ApplyPromoRequest,
    PromoQuery,
    PromoType, PromoStatus, ScopeType, ConditionType, BenefitType
)


def generate_promo_no() -> str:
    """生成促销单号"""
    return f"PR{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


class PromoService:
    """促销服务"""
    
    def __init__(self, db: AsyncSession, kafka: Optional[KafkaProducer] = None):
        self.db = db
        self.kafka = kafka
    
    async def create(self, data: PromoCreate, created_by: str = None) -> Promo:
        """创建促销活动"""
        # 检查编码是否已存在
        existing = await self.db.execute(
            select(Promo).where(Promo.code == data.code)
        )
        if existing.scalar_one_or_none():
            raise BusinessException(code="CODE_EXISTS", message=f"促销编码已存在: {data.code}")
        
        # 创建促销主记录
        promo = Promo(
            code=data.code,
            name=data.name,
            promo_type=data.promo_type.value,
            scope_type=data.scope_type.value,
            scope_value=data.scope_value,
            condition_type=data.condition_type.value,
            condition_value=data.condition_value,
            benefit_type=data.benefit_type.value,
            benefit_value=data.benefit_value,
            max_discount=data.max_discount,
            min_qty=data.min_qty,
            max_qty=data.max_qty,
            usage_limit=data.usage_limit,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
            status=PromoStatus.DRAFT.value,
            priority=data.priority,
            remark=data.remark,
            created_by=created_by
        )
        self.db.add(promo)
        await self.db.flush()
        
        # 创建促销规则
        for rule_data in data.rules:
            rule = PromoRule(
                promo_id=promo.id,
                name=rule_data.name,
                condition_field=rule_data.condition_field,
                condition_operator=rule_data.condition_operator.value,
                condition_value=rule_data.condition_value,
                benefit_field=rule_data.benefit_field,
                benefit_operator=rule_data.benefit_operator.value,
                benefit_value=rule_data.benefit_value,
                priority=rule_data.priority,
                status=rule_data.status
            )
            self.db.add(rule)
        
        await self.db.commit()
        await self.db.refresh(promo)
        return promo
    
    async def get_by_id(self, promo_id: int) -> Optional[Promo]:
        """根据ID获取促销活动"""
        result = await self.db.execute(
            select(Promo)
            .where(Promo.id == promo_id)
            .options(selectinload(Promo.rules))
        )
        return result.scalar_one_or_none()
    
    async def get_by_code(self, code: str) -> Optional[Promo]:
        """根据编码获取促销活动"""
        result = await self.db.execute(
            select(Promo)
            .where(and_(Promo.code == code, Promo.status == PromoStatus.ACTIVE.value))
            .options(selectinload(Promo.rules))
        )
        return result.scalar_one_or_none()
    
    async def update(self, promo_id: int, data: PromoUpdate) -> Promo:
        """更新促销活动"""
        promo = await self.get_by_id(promo_id)
        if not promo:
            raise BusinessException(code="NOT_FOUND", message="促销活动不存在")
        
        # 更新字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(promo, key):
                setattr(promo, key, value)
        
        await self.db.commit()
        await self.db.refresh(promo)
        return promo
    
    async def activate(self, promo_id: int) -> Promo:
        """激活促销活动"""
        promo = await self.get_by_id(promo_id)
        if not promo:
            raise BusinessException(code="NOT_FOUND", message="促销活动不存在")
        
        # 检查是否在有效期内
        if promo.valid_from > date.today() or promo.valid_to < date.today():
            raise BusinessException(code="INVALID_PERIOD", message="促销活动不在有效期内")
        
        promo.status = PromoStatus.ACTIVE.value
        await self.db.commit()
        await self.db.refresh(promo)
        return promo
    
    async def deactivate(self, promo_id: int) -> Promo:
        """停用促销活动"""
        promo = await self.get_by_id(promo_id)
        if not promo:
            raise BusinessException(code="NOT_FOUND", message="促销活动不存在")
        
        promo.status = PromoStatus.INACTIVE.value
        await self.db.commit()
        await self.db.refresh(promo)
        return promo
    
    async def query(self, query: PromoQuery) -> Tuple[List[Promo], int]:
        """查询促销活动"""
        stmt = select(Promo)
        
        if query.code:
            stmt = stmt.where(Promo.code.contains(query.code))
        if query.promo_type:
            stmt = stmt.where(Promo.promo_type == query.promo_type.value)
        if query.status:
            stmt = stmt.where(Promo.status == query.status.value)
        if query.valid_from:
            stmt = stmt.where(Promo.valid_to >= query.valid_from)
        if query.valid_to:
            stmt = stmt.where(Promo.valid_from <= query.valid_to)
        
        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # 分页
        stmt = stmt.order_by(Promo.priority.desc(), Promo.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        
        result = await self.db.execute(stmt)
        promos = result.scalars().all()
        
        return list(promos), total or 0


class PromoCalculationService:
    """促销计算服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate_promo(self, request: CalcPromoRequest) -> CalcPromoResponse:
        """计算促销优惠"""
        # 获取所有激活的促销活动
        active_promos = await self._get_active_promos()
        
        # 计算原始总价
        original_total = sum(
            Decimal(str(item.get('price', 0))) * Decimal(str(item.get('qty', 1)))
            for item in request.items
        )
        
        # 应用促销
        final_total = original_total
        applied_promos = []
        item_details = []
        
        # 按优先级排序促销活动
        sorted_promos = sorted(active_promos, key=lambda p: p.priority, reverse=True)
        
        for promo in sorted_promos:
            # 检查促销是否适用于当前订单
            if await self._check_promo_eligible(promo, request.items):
                # 计算该促销对订单的优惠
                promo_discount, promo_items = await self._apply_promo_to_order(
                    promo, request.items, final_total
                )
                
                if promo_discount > 0:
                    final_total -= promo_discount
                    applied_promos.append({
                        'promo_id': promo.id,
                        'promo_code': promo.code,
                        'promo_name': promo.name,
                        'discount_amount': float(promo_discount),
                        'promo_type': promo.promo_type
                    })
                    
                    # 更新商品明细
                    for item_detail in promo_items:
                        item_details.append(item_detail)
        
        # 如果没有应用任何促销，则返回原始商品明细
        if not item_details:
            item_details = request.items
        
        total_discount = original_total - final_total
        
        return CalcPromoResponse(
            order_no=request.order_no,
            original_total=original_total,
            final_total=final_total,
            total_discount=total_discount,
            applied_promos=applied_promos,
            item_details=item_details
        )
    
    async def _get_active_promos(self) -> List[Promo]:
        """获取所有激活的促销活动"""
        result = await self.db.execute(
            select(Promo)
            .where(
                and_(
                    Promo.status == PromoStatus.ACTIVE.value,
                    Promo.valid_from <= date.today(),
                    Promo.valid_to >= date.today()
                )
            )
            .options(selectinload(Promo.rules))
        )
        return list(result.scalars().all())
    
    async def _check_promo_eligible(self, promo: Promo, items: List[Dict]) -> bool:
        """检查促销是否适用于订单"""
        # 检查适用范围
        if promo.scope_type != ScopeType.ALL.value:
            eligible = False
            for item in items:
                if promo.scope_type == ScopeType.SKU.value:
                    # 检查SKU是否在范围内
                    scope_values = json.loads(promo.scope_value) if promo.scope_value else []
                    if item.get('sku_id') in scope_values:
                        eligible = True
                        break
                elif promo.scope_type == ScopeType.CATEGORY.value:
                    # 检查分类是否在范围内
                    scope_values = json.loads(promo.scope_value) if promo.scope_value else []
                    if item.get('category_id') in scope_values:
                        eligible = True
                        break
                elif promo.scope_type == ScopeType.BRAND.value:
                    # 检查品牌是否在范围内
                    scope_values = json.loads(promo.scope_value) if promo.scope_value else []
                    if item.get('brand_id') in scope_values:
                        eligible = True
                        break
            if not eligible:
                return False
        
        # 检查条件
        if promo.condition_type == ConditionType.AMOUNT.value:
            order_total = sum(
                Decimal(str(item.get('price', 0))) * Decimal(str(item.get('qty', 1)))
                for item in items
            )
            if order_total < promo.condition_value:
                return False
        elif promo.condition_type == ConditionType.QTY.value:
            order_qty = sum(Decimal(str(item.get('qty', 1))) for item in items)
            if order_qty < promo.condition_value:
                return False
        
        return True
    
    async def _apply_promo_to_order(
        self, promo: Promo, items: List[Dict], original_total: Decimal
    ) -> Tuple[Decimal, List[Dict]]:
        """将促销应用于订单"""
        discount_amount = Decimal("0")
        item_details = []
        
        if promo.promo_type == PromoType.FULL_REDUCTION.value:
            # 满减促销
            if original_total >= promo.condition_value:
                discount_amount = min(promo.benefit_value, promo.max_discount) if promo.max_discount > 0 else promo.benefit_value
        
        elif promo.promo_type == PromoType.DISCOUNT.value:
            # 折扣促销
            if promo.benefit_value < 100:  # 百分比折扣
                discount_amount = original_total * (Decimal("100") - promo.benefit_value) / Decimal("100")
            else:  # 固定金额折扣
                discount_amount = promo.benefit_value
        
        elif promo.promo_type == PromoType.BUY_GIFT.value:
            # 买赠促销，这里简化处理，只计算价值
            # 实际业务中需要处理赠品逻辑
            discount_amount = Decimal("0")  # 暂时不计算赠品价值
        
        # 返回当前促销的优惠金额和商品明细
        return discount_amount, items


class PromoRecordService:
    """促销记录服务"""
    
    def __init__(self, db: AsyncSession, kafka: Optional[KafkaProducer] = None):
        self.db = db
        self.kafka = kafka
    
    async def create_record(self, data: PromoRecordCreate, applied_by: str = None) -> PromoRecord:
        """创建促销应用记录"""
        promo_no = generate_promo_no()
        
        record = PromoRecord(
            promo_no=promo_no,
            promo_id=data.promo_id,
            promo_code=data.promo_code,
            promo_name=data.promo_name,
            order_no=data.order_no,
            sku_id=data.sku_id,
            sku_name=data.sku_name,
            benefit_type=data.benefit_type.value,
            benefit_value=data.benefit_value,
            original_price=data.original_price,
            final_price=data.final_price,
            qty=data.qty,
            total_discount=(data.original_price - data.final_price) * data.qty,
            applied_by=applied_by,
            remark=data.remark
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        
        # 发布促销应用事件
        await self._publish_promo_applied_event(record, applied_by or "")
        
        return record
    
    async def get_records_by_order(self, order_no: str) -> List[PromoRecord]:
        """根据订单号获取促销记录"""
        result = await self.db.execute(
            select(PromoRecord).where(PromoRecord.order_no == order_no)
        )
        return list(result.scalars().all())
    
    async def _publish_promo_applied_event(self, record: PromoRecord, applied_by: str):
        """发布促销应用事件"""
        if not self.kafka:
            return
        
        from .schemas import PromoAppliedEvent
        event = PromoAppliedEvent(
            promo_id=record.promo_id,
            promo_code=record.promo_code,
            order_no=record.order_no,
            total_discount=record.total_discount,
            applied_by=applied_by
        )
        
        try:
            await self.kafka.send(
                topic="promo-events",
                key=record.order_no,
                value=event.model_dump_json()
            )
        except Exception as e:
            print(f"Failed to publish PromoApplied event: {e}")


class PromoCombinationService:
    """促销组合服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_combination(self, data: PromoCombinationCreate, created_by: str = None) -> PromoCombination:
        """创建促销组合"""
        combination = PromoCombination(
            name=data.name,
            combination_type=data.combination_type.value,
            promo_ids=json.dumps(data.promo_ids),
            priority=data.priority,
            status="ACTIVE",
            remark=data.remark,
            created_by=created_by
        )
        self.db.add(combination)
        await self.db.commit()
        await self.db.refresh(combination)
        return combination
    
    async def get_combination_by_id(self, combo_id: int) -> Optional[PromoCombination]:
        """根据ID获取促销组合"""
        result = await self.db.execute(
            select(PromoCombination).where(PromoCombination.id == combo_id)
        )
        return result.scalar_one_or_none()
