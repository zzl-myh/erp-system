"""订单中心 - 业务服务层"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Tuple

import httpx
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.config import settings
from erp_common.exceptions import BusinessException
from erp_common.utils.kafka_utils import KafkaProducer

from .models import SoOrder, SoDetail, Payment, Shipment
from .schemas import (
    SoOrderCreate, SoOrderUpdate, SoOrderResponse,
    SoDetailCreate, PaymentCreate, ShipmentCreate,
    ConfirmOrderRequest, CancelOrderRequest, PayOrderRequest, ShipOrderRequest,
    SoOrderQuery, SoOrderBrief,
    OrderStatus, PaymentStatus, ShippingStatus, Channel
)


def generate_order_no(channel: str = "POS", store_id: Optional[int] = None) -> str:
    """生成订单号"""
    # 订单号格式：渠道+门店+日期+序列号
    date_part = datetime.now().strftime('%Y%m%d')
    channel_code = channel[:2].upper()
    store_code = f"{store_id:03d}" if store_id else "000"
    sequence = uuid.uuid4().hex[:6].upper()
    return f"{channel_code}{store_code}{date_part}{sequence}"


def generate_payment_no() -> str:
    """生成支付单号"""
    return f"PY{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


def generate_shipment_no() -> str:
    """生成发货单号"""
    return f"SH{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


class OrderService:
    """订单服务"""
    
    def __init__(self, db: AsyncSession, kafka: Optional[KafkaProducer] = None):
        self.db = db
        self.kafka = kafka
    
    async def create(self, data: SoOrderCreate, created_by: str = None) -> SoOrder:
        """创建销售订单"""
        # 生成订单号
        order_no = generate_order_no(data.channel.value, data.store_id)
        
        # 计算订单金额
        total_qty = Decimal("0")
        subtotal_amount = Decimal("0")
        
        for detail in data.details:
            line_subtotal = detail.unit_price * detail.qty_ordered
            discount_amount = line_subtotal * detail.discount_rate / 100
            net_amount = line_subtotal - discount_amount
            tax_amount = net_amount * detail.tax_rate / 100
            
            total_qty += detail.qty_ordered
            subtotal_amount += net_amount + tax_amount
        
        # 创建订单主表
        order = SoOrder(
            order_no=order_no,
            customer_id=data.customer_id,
            customer_name=data.customer_name,
            channel=data.channel.value,
            store_id=data.store_id,
            store_name=data.store_name,
            total_qty=total_qty,
            subtotal_amount=subtotal_amount,
            shipping_amount=Decimal("0"),  # 运费暂时为0
            tax_amount=Decimal("0"),      # 税额将在明细中累加
            total_amount=subtotal_amount,
            balance_amount=subtotal_amount,  # 待付金额等于总金额
            status=OrderStatus.DRAFT.value,
            order_date=date.today(),
            shipping_address=data.shipping_address,
            payment_method=data.payment_method.value if data.payment_method else None,
            remark=data.remark,
            created_by=created_by
        )
        self.db.add(order)
        await self.db.flush()
        
        # 创建订单明细
        for idx, detail in enumerate(data.details, start=1):
            # 计算明细金额
            line_subtotal = detail.unit_price * detail.qty_ordered
            discount_amount = line_subtotal * detail.discount_rate / 100
            net_amount = line_subtotal - discount_amount
            tax_amount = net_amount * detail.tax_rate / 100
            
            order_detail = SoDetail(
                order_id=order.id,
                sku_id=detail.sku_id,
                sku_name=detail.sku_name,
                barcode=detail.barcode,
                unit_price=detail.unit_price,
                discount_rate=detail.discount_rate,
                discount_amount=discount_amount,
                tax_rate=detail.tax_rate,
                tax_amount=tax_amount,
                net_amount=net_amount,
                qty_ordered=detail.qty_ordered,
                warehouse_id=detail.warehouse_id,
                line_no=detail.line_no or idx,
                remark=detail.remark
            )
            self.db.add(order_detail)
        
        # 更新订单税额和总金额
        order.tax_amount = sum(d.tax_amount for d in data.details)
        order.total_amount = subtotal_amount + order.tax_amount
        order.balance_amount = order.total_amount
        
        await self.db.commit()
        await self.db.refresh(order)
        
        # 发布订单创建事件
        await self._publish_order_created_event(order)
        
        return order
    
    async def get_by_id(self, order_id: int) -> Optional[SoOrder]:
        """根据ID获取订单"""
        result = await self.db.execute(
            select(SoOrder)
            .where(SoOrder.id == order_id)
            .options(select.SoOrder.details, select.SoOrder.payments, select.SoOrder.shipments)
        )
        return result.scalar_one_or_none()
    
    async def get_by_order_no(self, order_no: str) -> Optional[SoOrder]:
        """根据订单号获取订单"""
        result = await self.db.execute(
            select(SoOrder)
            .where(SoOrder.order_no == order_no)
            .options(select.SoOrder.details, select.SoOrder.payments, select.SoOrder.shipments)
        )
        return result.scalar_one_or_none()
    
    async def confirm(self, order_id: int, confirmed_by: str) -> SoOrder:
        """确认订单"""
        order = await self.get_by_id(order_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="订单不存在")
        
        if order.status != OrderStatus.DRAFT.value:
            raise BusinessException(code="INVALID_STATUS", message="只有草稿状态的订单可以确认")
        
        # 检查库存是否足够
        await self._check_inventory(order)
        
        order.status = OrderStatus.CONFIRMED.value
        order.confirmed_by = confirmed_by
        order.confirmed_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def cancel(self, order_id: int, reason: str = None) -> SoOrder:
        """取消订单"""
        order = await self.get_by_id(order_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="订单不存在")
        
        if order.status in [OrderStatus.SHIPPED.value, OrderStatus.DELIVERED.value]:
            raise BusinessException(code="INVALID_STATUS", message="已发货或已送达的订单不能取消")
        
        order.status = OrderStatus.CANCELLED.value
        if reason:
            order.remark = f"取消原因: {reason}. {order.remark or ''}"
        
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def pay(self, order_id: int, request: PayOrderRequest, paid_by: str) -> SoOrder:
        """支付订单"""
        order = await self.get_by_id(order_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="订单不存在")
        
        if order.status in [OrderStatus.CANCELLED.value, OrderStatus.RETURNED.value]:
            raise BusinessException(code="INVALID_STATUS", message="订单已取消或已退货，无法支付")
        
        if order.balance_amount <= 0:
            raise BusinessException(code="ORDER_PAID", message="订单已支付完成")
        
        # 检查支付金额
        if request.payment_amount > order.balance_amount:
            raise BusinessException(
                code="OVER_PAYMENT", 
                message=f"支付金额超出待付金额: 支付={request.payment_amount}, 待付={order.balance_amount}"
            )
        
        # 创建支付记录
        payment = Payment(
            payment_no=generate_payment_no(),
            order_id=order.id,
            payment_method=request.payment_method.value,
            payment_amount=request.payment_amount,
            payment_date=date.today(),
            status=PaymentStatus.SUCCESS.value,
            remark=request.remark,
            paid_by=paid_by
        )
        self.db.add(payment)
        
        # 更新订单支付信息
        order.paid_amount += request.payment_amount
        order.balance_amount = order.total_amount - order.paid_amount
        
        # 更新支付状态
        if order.balance_amount <= 0:
            order.payment_status = PaymentStatus.SUCCESS.value
            order.status = OrderStatus.PAYMENT_COMPLETED.value
        else:
            order.payment_status = PaymentStatus.PARTIAL.value
            order.status = OrderStatus.PAYMENT_PARTIAL.value
        
        await self.db.commit()
        await self.db.refresh(order)
        
        # 如果订单完全支付，发布订单支付完成事件
        if order.balance_amount <= 0:
            await self._publish_order_paid_event(order, request.payment_amount, request.payment_method.value)
        
        return order
    
    async def ship(self, order_id: int, request: ShipOrderRequest, shipped_by: str) -> SoOrder:
        """发货"""
        order = await self.get_by_id(order_id)
        if not order:
            raise BusinessException(code="NOT_FOUND", message="订单不存在")
        
        if order.status != OrderStatus.PAYMENT_COMPLETED.value:
            raise BusinessException(code="INVALID_STATUS", message="订单未支付完成，无法发货")
        
        # 创建发货记录
        shipment = Shipment(
            shipment_no=generate_shipment_no(),
            order_id=order.id,
            warehouse_id=order.details[0].warehouse_id,  # 使用第一个明细的仓库
            shipping_company=request.shipping_company,
            tracking_number=request.tracking_number,
            shipping_address=request.shipping_address or order.shipping_address,
            status=ShippingStatus.SHIPPED.value,
            shipped_date=date.today(),
            remark=request.remark,
            shipped_by=shipped_by
        )
        self.db.add(shipment)
        
        # 更新订单状态
        order.status = OrderStatus.SHIPPED.value
        order.shipping_status = ShippingStatus.SHIPPED.value
        order.shipped_by = shipped_by
        order.shipped_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(order)
        
        # 发布订单发货事件
        await self._publish_order_shipped_event(order, shipment)
        
        return order
    
    async def query(self, query: SoOrderQuery) -> Tuple[List[SoOrder], int]:
        """查询订单"""
        stmt = select(SoOrder)
        
        if query.order_no:
            stmt = stmt.where(SoOrder.order_no.contains(query.order_no))
        if query.customer_id:
            stmt = stmt.where(SoOrder.customer_id == query.customer_id)
        if query.channel:
            stmt = stmt.where(SoOrder.channel == query.channel.value)
        if query.status:
            stmt = stmt.where(SoOrder.status == query.status.value)
        if query.start_date:
            stmt = stmt.where(SoOrder.order_date >= query.start_date)
        if query.end_date:
            stmt = stmt.where(SoOrder.order_date <= query.end_date)
        
        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # 分页
        stmt = stmt.order_by(SoOrder.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        
        result = await self.db.execute(stmt)
        orders = result.scalars().all()
        
        return list(orders), total or 0
    
    async def _check_inventory(self, order: SoOrder) -> bool:
        """检查库存是否足够"""
        # 调用库存服务检查可用库存
        # 这里应该调用库存服务的API
        # 暂时返回True，实际实现中应检查每个SKU的可用库存
        return True
    
    async def _publish_order_created_event(self, order: SoOrder):
        """发布订单创建事件"""
        if not self.kafka:
            return
        
        from .schemas import OrderCreatedEvent
        event = OrderCreatedEvent(
            order_no=order.order_no,
            customer_id=order.customer_id,
            total_amount=order.total_amount
        )
        
        try:
            await self.kafka.send(
                topic="order-events",
                key=order.order_no,
                value=event.model_dump_json()
            )
        except Exception as e:
            print(f"Failed to publish OrderCreated event: {e}")
    
    async def _publish_order_paid_event(self, order: SoOrder, payment_amount: Decimal, payment_method: str):
        """发布订单支付完成事件"""
        if not self.kafka:
            return
        
        from .schemas import OrderPaidEvent
        event = OrderPaidEvent(
            order_no=order.order_no,
            payment_amount=payment_amount,
            payment_method=payment_method
        )
        
        try:
            await self.kafka.send(
                topic="order-events",
                key=order.order_no,
                value=event.model_dump_json()
            )
        except Exception as e:
            print(f"Failed to publish OrderPaid event: {e}")
    
    async def _publish_order_shipped_event(self, order: SoOrder, shipment: Shipment):
        """发布订单发货事件"""
        if not self.kafka:
            return
        
        from .schemas import OrderShippedEvent
        event = OrderShippedEvent(
            order_no=order.order_no,
            shipping_company=shipment.shipping_company,
            tracking_number=shipment.tracking_number
        )
        
        try:
            await self.kafka.send(
                topic="order-events",
                key=order.order_no,
                value=event.model_dump_json()
            )
        except Exception as e:
            print(f"Failed to publish OrderShipped event: {e}")


class PaymentService:
    """支付服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_payment(self, data: PaymentCreate, paid_by: str = None) -> Payment:
        """创建支付记录"""
        payment = Payment(
            payment_no=generate_payment_no(),
            order_id=data.order_id,
            payment_method=data.payment_method.value,
            payment_amount=data.payment_amount,
            payment_date=date.today(),
            status=PaymentStatus.PENDING.value,
            remark=data.remark,
            paid_by=paid_by
        )
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment


class ShipmentService:
    """发货服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_shipment(self, data: ShipmentCreate, shipped_by: str = None) -> Shipment:
        """创建发货记录"""
        shipment = Shipment(
            shipment_no=generate_shipment_no(),
            order_id=data.order_id,
            warehouse_id=data.warehouse_id,
            shipping_company=data.shipping_company,
            tracking_number=data.tracking_number,
            shipping_address=data.shipping_address,
            status=ShippingStatus.PENDING.value,
            remark=data.remark,
            shipped_by=shipped_by
        )
        self.db.add(shipment)
        await self.db.commit()
        await self.db.refresh(shipment)
        return shipment
