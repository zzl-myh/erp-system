"""订单中心 - REST API 路由"""
from typing import Optional
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from erp_common.database import get_db
from erp_common.schemas.base import Result, PageResult
from erp_common.auth import get_current_user, CurrentUser
from erp_common.utils.kafka_utils import get_kafka_producer, KafkaProducer

from .service import OrderService, PaymentService, ShipmentService
from .schemas import (
    SoOrderCreate, SoOrderUpdate, SoOrderResponse,
    PaymentCreate, PaymentResponse,
    ShipmentCreate, ShipmentResponse,
    ConfirmOrderRequest, CancelOrderRequest, PayOrderRequest, ShipOrderRequest,
    SoOrderQuery, SoOrderBrief,
    DashboardStats, SalesTrend
)
from .models import SoOrder

router = APIRouter(prefix="/order", tags=["订单管理"])


# ============ 仪表盘统计 ============

@router.get("/dashboard/stats", response_model=Result[DashboardStats], summary="仪表盘统计")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """获取仪表盘统计数据"""
    from sqlalchemy import text
    import logging
    logger = logging.getLogger(__name__)
    
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # 本周一
    
    # 商品总数
    try:
        item_result = await db.execute(text("SELECT COUNT(*) FROM item WHERE status = 1"))
        item_count = item_result.scalar() or 0
    except Exception as e:
        logger.warning(f"查询商品数量失败: {e}")
        item_count = 0
    
    # 会员总数
    try:
        member_result = await db.execute(text("SELECT COUNT(*) FROM member WHERE status = 1"))
        member_count = member_result.scalar() or 0
    except Exception as e:
        logger.warning(f"查询会员数量失败: {e}")
        member_count = 0
    
    # 今日订单数和销售额 (使用 created_at)
    try:
        today_result = await db.execute(
            text("""
                SELECT COUNT(*) as cnt, COALESCE(SUM(total_amount), 0) as total 
                FROM so_order 
                WHERE DATE(created_at) = :today AND status != 'CANCELLED'
            """),
            {"today": today}
        )
        today_row = today_result.fetchone()
        today_order_count = today_row[0] if today_row else 0
        today_sales = float(today_row[1]) if today_row else 0
    except Exception as e:
        logger.warning(f"查询今日订单失败: {e}")
        today_order_count = 0
        today_sales = 0
    
    # 本周销售趋势
    week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    week_sales_trend = []
    
    for i in range(7):
        day = week_start + timedelta(days=i)
        try:
            day_result = await db.execute(
                text("""
                    SELECT COUNT(*) as cnt, COALESCE(SUM(total_amount), 0) as total
                    FROM so_order
                    WHERE DATE(created_at) = :day AND status != 'CANCELLED'
                """),
                {"day": day}
            )
            day_row = day_result.fetchone()
            week_sales_trend.append(SalesTrend(
                date=week_days[i],
                amount=float(day_row[1]) if day_row else 0,
                order_count=day_row[0] if day_row else 0
            ))
        except Exception:
            week_sales_trend.append(SalesTrend(
                date=week_days[i],
                amount=0,
                order_count=0
            ))
    
    stats = DashboardStats(
        item_count=item_count,
        today_order_count=today_order_count,
        member_count=member_count,
        today_sales=today_sales,
        week_sales_trend=week_sales_trend
    )
    
    return Result.ok(data=stats)


def get_order_service(
    db: AsyncSession = Depends(get_db),
    kafka: Optional[KafkaProducer] = Depends(get_kafka_producer)
) -> OrderService:
    return OrderService(db, kafka)


def get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    return PaymentService(db)


def get_shipment_service(db: AsyncSession = Depends(get_db)) -> ShipmentService:
    return ShipmentService(db)


# ============ 订单管理 ============

@router.post("/create", response_model=Result[SoOrderResponse], summary="创建销售订单")
async def create_order(
    request: SoOrderCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service)
):
    """创建销售订单"""
    order = await service.create(request, created_by=current_user.username)
    return Result.ok(data=SoOrderResponse.model_validate(order))


@router.get("/{order_id}", response_model=Result[SoOrderResponse], summary="获取销售订单")
async def get_order(
    order_id: int,
    service: OrderService = Depends(get_order_service)
):
    """获取销售订单详情"""
    order = await service.get_by_id(order_id)
    if not order:
        return Result.fail(code="NOT_FOUND", message="订单不存在")
    return Result.ok(data=SoOrderResponse.model_validate(order))


@router.put("/{order_id}", response_model=Result[SoOrderResponse], summary="更新销售订单")
async def update_order(
    order_id: int,
    request: SoOrderUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service)
):
    """更新销售订单"""
    order = await service.get_by_id(order_id)
    if not order:
        return Result.fail(code="NOT_FOUND", message="订单不存在")
    
    # 只允许在特定状态下更新
    if order.status not in ["DRAFT"]:
        return Result.fail(code="INVALID_STATUS", message="当前状态不允许修改")
    
    # 更新字段
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    
    await service.db.commit()
    await service.db.refresh(order)
    return Result.ok(data=SoOrderResponse.model_validate(order))


@router.post("/{order_id}/confirm", response_model=Result[SoOrderResponse], summary="确认订单")
async def confirm_order(
    order_id: int,
    request: ConfirmOrderRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service)
):
    """确认订单"""
    order = await service.confirm(order_id, confirmed_by=current_user.username)
    return Result.ok(data=SoOrderResponse.model_validate(order))


@router.post("/{order_id}/cancel", response_model=Result[SoOrderResponse], summary="取消订单")
async def cancel_order(
    order_id: int,
    request: CancelOrderRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service)
):
    """取消订单"""
    order = await service.cancel(order_id, reason=request.reason)
    return Result.ok(data=SoOrderResponse.model_validate(order))


@router.post("/{order_id}/pay", response_model=Result[SoOrderResponse], summary="支付订单")
async def pay_order(
    order_id: int,
    request: PayOrderRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service)
):
    """支付订单"""
    order = await service.pay(order_id, request, paid_by=current_user.username)
    return Result.ok(data=SoOrderResponse.model_validate(order))


@router.post("/{order_id}/ship", response_model=Result[SoOrderResponse], summary="发货")
async def ship_order(
    order_id: int,
    request: ShipOrderRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service)
):
    """发货"""
    order = await service.ship(order_id, request, shipped_by=current_user.username)
    return Result.ok(data=SoOrderResponse.model_validate(order))


@router.get("/list", response_model=Result[PageResult[SoOrderBrief]], summary="销售订单列表")
async def list_orders(
    order_no: Optional[str] = Query(None, description="订单号"),
    customer_id: Optional[int] = Query(None, description="客户ID"),
    channel: Optional[str] = Query(None, description="销售渠道"),
    status: Optional[str] = Query(None, description="状态"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: OrderService = Depends(get_order_service)
):
    """销售订单列表"""
    query = SoOrderQuery(
        order_no=order_no,
        customer_id=customer_id,
        channel=channel,
        status=status,
        page=page,
        page_size=page_size
    )
    
    # 转换日期字符串为 date 对象
    if start_date:
        from datetime import datetime
        query.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if end_date:
        from datetime import datetime
        query.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    orders, total = await service.query(query)
    return Result.ok(data=PageResult(
        items=[SoOrderBrief.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size
    ))


# ============ 支付管理 ============

@router.post("/payment", response_model=Result[PaymentResponse], summary="创建支付记录")
async def create_payment(
    request: PaymentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service)
):
    """创建支付记录"""
    payment = await service.create_payment(request, paid_by=current_user.username)
    return Result.ok(data=PaymentResponse.model_validate(payment))


# ============ 发货管理 ============

@router.post("/shipment", response_model=Result[ShipmentResponse], summary="创建发货记录")
async def create_shipment(
    request: ShipmentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ShipmentService = Depends(get_shipment_service)
):
    """创建发货记录"""
    shipment = await service.create_shipment(request, shipped_by=current_user.username)
    return Result.ok(data=ShipmentResponse.model_validate(shipment))
