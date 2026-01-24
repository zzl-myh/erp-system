"""促销中心 - REST API 路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.database import get_db
from erp_common.schemas.base import Result, PageResult
from erp_common.auth import get_current_user, CurrentUser
from erp_common.utils.kafka_utils import get_kafka_producer, KafkaProducer

from .service import (
    PromoService, PromoCalculationService, 
    PromoRecordService, PromoCombinationService
)
from .schemas import (
    PromoCreate, PromoUpdate, PromoResponse,
    PromoRuleCreate, PromoRuleResponse,
    PromoRecordCreate, PromoRecordResponse,
    PromoCombinationCreate, PromoCombinationUpdate, PromoCombinationResponse,
    CalcPromoRequest, CalcPromoResponse,
    PromoQuery
)

router = APIRouter(prefix="/promo", tags=["促销管理"])


def get_promo_service(
    db: AsyncSession = Depends(get_db),
    kafka: Optional[KafkaProducer] = Depends(get_kafka_producer)
) -> PromoService:
    return PromoService(db, kafka)


def get_promo_calculation_service(db: AsyncSession = Depends(get_db)) -> PromoCalculationService:
    return PromoCalculationService(db)


def get_promo_record_service(
    db: AsyncSession = Depends(get_db),
    kafka: Optional[KafkaProducer] = Depends(get_kafka_producer)
) -> PromoRecordService:
    return PromoRecordService(db, kafka)


def get_promo_combination_service(db: AsyncSession = Depends(get_db)) -> PromoCombinationService:
    return PromoCombinationService(db)


# ============ 促销活动管理 ============

@router.post("/create", response_model=Result[PromoResponse], summary="创建促销活动")
async def create_promo(
    request: PromoCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: PromoService = Depends(get_promo_service)
):
    """创建促销活动"""
    promo = await service.create(request, created_by=current_user.username)
    return Result.ok(data=PromoResponse.model_validate(promo))


@router.get("/{promo_id}", response_model=Result[PromoResponse], summary="获取促销活动")
async def get_promo(
    promo_id: int,
    service: PromoService = Depends(get_promo_service)
):
    """获取促销活动详情"""
    promo = await service.get_by_id(promo_id)
    if not promo:
        return Result.fail(code="NOT_FOUND", message="促销活动不存在")
    return Result.ok(data=PromoResponse.model_validate(promo))


@router.put("/{promo_id}", response_model=Result[PromoResponse], summary="更新促销活动")
async def update_promo(
    promo_id: int,
    request: PromoUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: PromoService = Depends(get_promo_service)
):
    """更新促销活动"""
    promo = await service.update(promo_id, request)
    return Result.ok(data=PromoResponse.model_validate(promo))


@router.post("/{promo_id}/activate", response_model=Result[PromoResponse], summary="激活促销活动")
async def activate_promo(
    promo_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: PromoService = Depends(get_promo_service)
):
    """激活促销活动"""
    promo = await service.activate(promo_id)
    return Result.ok(data=PromoResponse.model_validate(promo))


@router.post("/{promo_id}/deactivate", response_model=Result[PromoResponse], summary="停用促销活动")
async def deactivate_promo(
    promo_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: PromoService = Depends(get_promo_service)
):
    """停用促销活动"""
    promo = await service.deactivate(promo_id)
    return Result.ok(data=PromoResponse.model_validate(promo))


@router.get("/list", response_model=Result[PageResult[PromoResponse]], summary="促销活动列表")
async def list_promos(
    code: Optional[str] = Query(None, description="促销编码"),
    promo_type: Optional[str] = Query(None, description="促销类型"),
    status: Optional[str] = Query(None, description="状态"),
    valid_from: Optional[str] = Query(None, description="有效开始日期 YYYY-MM-DD"),
    valid_to: Optional[str] = Query(None, description="有效结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: PromoService = Depends(get_promo_service)
):
    """促销活动列表"""
    query = PromoQuery(
        code=code,
        promo_type=promo_type,
        status=status,
        page=page,
        page_size=page_size
    )
    
    # 转换日期字符串为 date 对象
    if valid_from:
        from datetime import datetime
        query.valid_from = datetime.strptime(valid_from, "%Y-%m-%d").date()
    if valid_to:
        from datetime import datetime
        query.valid_to = datetime.strptime(valid_to, "%Y-%m-%d").date()
    
    promos, total = await service.query(query)
    return Result.ok(data=PageResult(
        items=[PromoResponse.model_validate(p) for p in promos],
        total=total,
        page=page,
        page_size=page_size
    ))


# ============ 促销计算 ============

@router.post("/calc", response_model=Result[CalcPromoResponse], summary="计算促销优惠")
async def calc_promo(
    request: CalcPromoRequest,
    service: PromoCalculationService = Depends(get_promo_calculation_service)
):
    """计算促销优惠"""
    result = await service.calculate_promo(request)
    return Result.ok(data=result)


# ============ 促销记录管理 ============

@router.post("/record", response_model=Result[PromoRecordResponse], summary="创建促销记录")
async def create_promo_record(
    request: PromoRecordCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: PromoRecordService = Depends(get_promo_record_service)
):
    """创建促销应用记录"""
    record = await service.create_record(request, applied_by=current_user.username)
    return Result.ok(data=PromoRecordResponse.model_validate(record))


@router.get("/record/{order_no}", response_model=Result[list], summary="获取订单促销记录")
async def get_promo_records_by_order(
    order_no: str,
    service: PromoRecordService = Depends(get_promo_record_service)
):
    """根据订单号获取促销记录"""
    records = await service.get_records_by_order(order_no)
    return Result.ok(data=[PromoRecordResponse.model_validate(r) for r in records])


# ============ 促销组合管理 ============

@router.post("/combination", response_model=Result[PromoCombinationResponse], summary="创建促销组合")
async def create_promo_combination(
    request: PromoCombinationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: PromoCombinationService = Depends(get_promo_combination_service)
):
    """创建促销组合"""
    combination = await service.create_combination(request, created_by=current_user.username)
    return Result.ok(data=PromoCombinationResponse.model_validate(combination))


@router.get("/combination/{combo_id}", response_model=Result[PromoCombinationResponse], summary="获取促销组合")
async def get_promo_combination(
    combo_id: int,
    service: PromoCombinationService = Depends(get_promo_combination_service)
):
    """获取促销组合详情"""
    combination = await service.get_combination_by_id(combo_id)
    if not combination:
        return Result.fail(code="NOT_FOUND", message="促销组合不存在")
    return Result.ok(data=PromoCombinationResponse.model_validate(combination))
