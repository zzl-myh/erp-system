"""会员中心 - REST API 路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.database import get_db
from erp_common.schemas.base import Result, PageResult
from erp_common.auth import get_current_user, CurrentUser
from erp_common.utils.kafka_utils import get_kafka_producer, KafkaProducer

from .service import (
    MemberService, MemberLevelService, 
    MemberPointService, MemberCouponService
)
from .schemas import (
    MemberCreate, MemberUpdate, MemberResponse,
    MemberLevelCreate, MemberLevelUpdate, MemberLevelResponse,
    MemberPointCreate, MemberPointResponse,
    MemberCouponCreate, MemberCouponUpdate, MemberCouponResponse,
    EarnPointsRequest, ConsumePointsRequest, IssueCouponRequest, UseCouponRequest,
    MemberQuery, MemberPointQuery, MemberCouponQuery
)

router = APIRouter(prefix="/member", tags=["会员管理"])


def get_member_service(
    db: AsyncSession = Depends(get_db),
    kafka: Optional[KafkaProducer] = Depends(get_kafka_producer)
) -> MemberService:
    return MemberService(db, kafka)


def get_member_level_service(db: AsyncSession = Depends(get_db)) -> MemberLevelService:
    return MemberLevelService(db)


def get_member_point_service(
    db: AsyncSession = Depends(get_db),
    kafka: Optional[KafkaProducer] = Depends(get_kafka_producer)
) -> MemberPointService:
    return MemberPointService(db, kafka)


def get_member_coupon_service(db: AsyncSession = Depends(get_db)) -> MemberCouponService:
    return MemberCouponService(db)


# ============ 会员管理 ============

@router.post("/register", response_model=Result[MemberResponse], summary="注册会员")
async def register_member(
    request: MemberCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: MemberService = Depends(get_member_service)
):
    """注册会员"""
    member = await service.create(request, created_by=current_user.username)
    return Result.ok(data=MemberResponse.model_validate(member))


@router.get("/{member_id}", response_model=Result[MemberResponse], summary="获取会员信息")
async def get_member(
    member_id: int,
    service: MemberService = Depends(get_member_service)
):
    """获取会员信息"""
    member = await service.get_by_id(member_id)
    if not member:
        return Result.fail(code="NOT_FOUND", message="会员不存在")
    return Result.ok(data=MemberResponse.model_validate(member))


@router.put("/{member_id}", response_model=Result[MemberResponse], summary="更新会员信息")
async def update_member(
    member_id: int,
    request: MemberUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: MemberService = Depends(get_member_service)
):
    """更新会员信息"""
    member = await service.update(member_id, request)
    return Result.ok(data=MemberResponse.model_validate(member))


@router.get("/phone/{phone}", response_model=Result[MemberResponse], summary="根据手机号获取会员")
async def get_member_by_phone(
    phone: str,
    service: MemberService = Depends(get_member_service)
):
    """根据手机号获取会员"""
    member = await service.get_by_phone(phone)
    if not member:
        return Result.fail(code="NOT_FOUND", message="会员不存在")
    return Result.ok(data=MemberResponse.model_validate(member))


@router.get("/list", response_model=Result[PageResult[MemberResponse]], summary="会员列表")
async def list_members(
    phone: Optional[str] = Query(None, description="手机号"),
    member_no: Optional[str] = Query(None, description="会员号"),
    level_id: Optional[int] = Query(None, description="等级ID"),
    status: Optional[str] = Query(None, description="状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: MemberService = Depends(get_member_service)
):
    """会员列表"""
    query = MemberQuery(
        phone=phone,
        member_no=member_no,
        level_id=level_id,
        status=status,
        page=page,
        page_size=page_size
    )
    members, total = await service.query(query)
    return Result.ok(data=PageResult(
        items=[MemberResponse.model_validate(m) for m in members],
        total=total,
        page=page,
        page_size=page_size
    ))


# ============ 会员等级管理 ============

@router.post("/level", response_model=Result[MemberLevelResponse], summary="创建会员等级")
async def create_member_level(
    request: MemberLevelCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: MemberLevelService = Depends(get_member_level_service)
):
    """创建会员等级"""
    level = await service.create(request, created_by=current_user.username)
    return Result.ok(data=MemberLevelResponse.model_validate(level))


@router.get("/level/{level_id}", response_model=Result[MemberLevelResponse], summary="获取会员等级")
async def get_member_level(
    level_id: int,
    service: MemberLevelService = Depends(get_member_level_service)
):
    """获取会员等级"""
    level = await service.get_by_id(level_id)
    if not level:
        return Result.fail(code="NOT_FOUND", message="会员等级不存在")
    return Result.ok(data=MemberLevelResponse.model_validate(level))


# ============ 积分管理 ============

@router.post("/point/earn", response_model=Result[MemberPointResponse], summary="获得积分")
async def earn_points(
    request: EarnPointsRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: MemberPointService = Depends(get_member_point_service)
):
    """获得积分"""
    point_record = await service.earn_points(request, operator=current_user.username)
    return Result.ok(data=MemberPointResponse.model_validate(point_record))


@router.post("/point/consume", response_model=Result[MemberPointResponse], summary="消费积分")
async def consume_points(
    request: ConsumePointsRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: MemberPointService = Depends(get_member_point_service)
):
    """消费积分"""
    point_record = await service.consume_points(request, operator=current_user.username)
    return Result.ok(data=MemberPointResponse.model_validate(point_record))


@router.get("/point/history", response_model=Result[PageResult[MemberPointResponse]], summary="积分历史记录")
async def get_point_history(
    member_id: int = Query(..., description="会员ID"),
    change_type: Optional[str] = Query(None, description="变动类型"),
    source_type: Optional[str] = Query(None, description="来源类型"),
    source_no: Optional[str] = Query(None, description="来源单号"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: MemberPointService = Depends(get_member_point_service)
):
    """积分历史记录"""
    query = MemberPointQuery(
        member_id=member_id,
        change_type=change_type,
        source_type=source_type,
        source_no=source_no,
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
    
    records, total = await service.get_point_history(query)
    return Result.ok(data=PageResult(
        items=[MemberPointResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size
    ))


# ============ 优惠券管理 ============

@router.post("/coupon/issue", response_model=Result[MemberCouponResponse], summary="发放优惠券")
async def issue_coupon(
    request: IssueCouponRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: MemberCouponService = Depends(get_member_coupon_service)
):
    """发放优惠券"""
    coupon = await service.issue_coupon(request, issued_by=current_user.username)
    return Result.ok(data=MemberCouponResponse.model_validate(coupon))


@router.post("/coupon/use", response_model=Result[MemberCouponResponse], summary="使用优惠券")
async def use_coupon(
    request: UseCouponRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: MemberCouponService = Depends(get_member_coupon_service)
):
    """使用优惠券"""
    coupon = await service.use_coupon(request, used_by=current_user.username)
    return Result.ok(data=MemberCouponResponse.model_validate(coupon))


@router.get("/coupon/{member_id}", response_model=Result[list], summary="会员优惠券列表")
async def get_member_coupons(
    member_id: int,
    status: Optional[str] = Query(None, description="状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: MemberCouponService = Depends(get_member_coupon_service)
):
    """会员优惠券列表"""
    from .schemas import CouponStatus
    status_enum = CouponStatus(status) if status else None
    coupons = await service.get_coupons_by_member(member_id, status_enum)
    return Result.ok(data=[MemberCouponResponse.model_validate(c) for c in coupons])


@router.get("/coupon/list", response_model=Result[PageResult[MemberCouponResponse]], summary="优惠券列表")
async def list_coupons(
    member_id: Optional[int] = Query(None, description="会员ID"),
    coupon_type: Optional[str] = Query(None, description="优惠券类型"),
    status: Optional[str] = Query(None, description="状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: MemberCouponService = Depends(get_member_coupon_service)
):
    """优惠券列表"""
    query = MemberCouponQuery(
        member_id=member_id,
        coupon_type=coupon_type,
        status=status,
        page=page,
        page_size=page_size
    )
    coupons, total = await service.query_coupons(query)
    return Result.ok(data=PageResult(
        items=[MemberCouponResponse.model_validate(c) for c in coupons],
        total=total,
        page=page,
        page_size=page_size
    ))
