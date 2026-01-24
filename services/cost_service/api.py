"""成本中心 - REST API 路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.database import get_db
from erp_common.schemas.base import Result, PageResult
from erp_common.auth import get_current_user, CurrentUser
from erp_common.utils.kafka_utils import get_kafka_producer, KafkaProducer

from .service import (
    CostCalculationService, CostSheetService, 
    ProductCostService, CostAllocationRuleService
)
from .schemas import (
    CostSheetCreate, CostSheetUpdate, CostSheetResponse,
    ProductCostCreate, ProductCostUpdate, ProductCostResponse,
    CostAllocationRuleCreate, CostAllocationRuleUpdate, CostAllocationRuleResponse,
    CalculateCostRequest, CalculateCostResponse,
    CostSheetQuery
)

router = APIRouter(prefix="/cost", tags=["成本管理"])


def get_calculation_service(
    db: AsyncSession = Depends(get_db),
    kafka: Optional[KafkaProducer] = Depends(get_kafka_producer)
) -> CostCalculationService:
    return CostCalculationService(db, kafka)


def get_cost_sheet_service(
    db: AsyncSession = Depends(get_db),
    calculation_service: CostCalculationService = Depends(get_calculation_service),
    kafka: Optional[KafkaProducer] = Depends(get_kafka_producer)
) -> CostSheetService:
    return CostSheetService(db, calculation_service, kafka)


def get_product_cost_service(db: AsyncSession = Depends(get_db)) -> ProductCostService:
    return ProductCostService(db)


def get_allocation_rule_service(db: AsyncSession = Depends(get_db)) -> CostAllocationRuleService:
    return CostAllocationRuleService(db)


# ============ 成本计算 ============

@router.post("/calculate", response_model=Result[CalculateCostResponse], summary="计算成本")
async def calculate_cost(
    request: CalculateCostRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: CostCalculationService = Depends(get_calculation_service)
):
    """计算成本"""
    if request.cost_type == "PURCHASE":
        result = await service.calculate_purchase_cost(
            request.sku_id, request.quantity, request.source_no
        )
    elif request.cost_type == "PRODUCTION":
        result = await service.calculate_production_cost(
            request.source_no, request.sku_id, request.quantity
        )
    else:
        raise ValueError(f"不支持的成本类型: {request.cost_type}")
    
    return Result.ok(data=result)


# ============ 成本核算单管理 ============

@router.post("/sheet", response_model=Result[CostSheetResponse], summary="创建成本核算单")
async def create_cost_sheet(
    request: CostSheetCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: CostSheetService = Depends(get_cost_sheet_service)
):
    """创建成本核算单"""
    sheet = await service.create(request, created_by=current_user.username)
    return Result.ok(data=CostSheetResponse.model_validate(sheet))


@router.get("/sheet/{sheet_id}", response_model=Result[CostSheetResponse], summary="获取成本核算单")
async def get_cost_sheet(
    sheet_id: int,
    service: CostSheetService = Depends(get_cost_sheet_service)
):
    """获取成本核算单详情"""
    sheet = await service.get_by_id(sheet_id)
    if not sheet:
        return Result.fail(code="NOT_FOUND", message="成本核算单不存在")
    return Result.ok(data=CostSheetResponse.model_validate(sheet))


@router.post("/sheet/{sheet_id}/post", response_model=Result[CostSheetResponse], summary="过账成本核算单")
async def post_cost_sheet(
    sheet_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: CostSheetService = Depends(get_cost_sheet_service)
):
    """过账成本核算单"""
    sheet = await service.post_sheet(sheet_id, posted_by=current_user.username)
    return Result.ok(data=CostSheetResponse.model_validate(sheet))


@router.get("/sheet/list", response_model=Result[PageResult[CostSheetResponse]], summary="成本核算单列表")
async def list_cost_sheets(
    sku_id: Optional[str] = Query(None, description="SKU ID"),
    cost_type: Optional[str] = Query(None, description="成本类型"),
    status: Optional[str] = Query(None, description="状态"),
    period_start: Optional[str] = Query(None, description="期间开始 YYYY-MM-DD"),
    period_end: Optional[str] = Query(None, description="期间结束 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: CostSheetService = Depends(get_cost_sheet_service)
):
    """成本核算单列表"""
    query = CostSheetQuery(
        sku_id=sku_id,
        cost_type=cost_type,
        status=status,
        page=page,
        page_size=page_size
    )
    
    # 转换日期字符串为 date 对象
    if period_start:
        from datetime import datetime
        query.period_start = datetime.strptime(period_start, "%Y-%m-%d").date()
    if period_end:
        from datetime import datetime
        query.period_end = datetime.strptime(period_end, "%Y-%m-%d").date()
    
    sheets, total = await service.query(query)
    return Result.ok(data=PageResult(
        items=[CostSheetResponse.model_validate(s) for s in sheets],
        total=total,
        page=page,
        page_size=page_size
    ))


# ============ 产品标准成本管理 ============

@router.post("/product-cost", response_model=Result[ProductCostResponse], summary="创建产品标准成本")
async def create_product_cost(
    request: ProductCostCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProductCostService = Depends(get_product_cost_service)
):
    """创建产品标准成本"""
    product_cost = await service.create(request, created_by=current_user.username)
    return Result.ok(data=ProductCostResponse.model_validate(product_cost))


@router.get("/product-cost/{sku_id}", response_model=Result[ProductCostResponse], summary="获取产品标准成本")
async def get_product_cost(
    sku_id: str,
    service: ProductCostService = Depends(get_product_cost_service)
):
    """获取产品标准成本详情"""
    product_cost = await service.get_by_sku(sku_id)
    if not product_cost:
        return Result.fail(code="NOT_FOUND", message="产品标准成本不存在")
    return Result.ok(data=ProductCostResponse.model_validate(product_cost))


@router.put("/product-cost/{sku_id}", response_model=Result[ProductCostResponse], summary="更新产品标准成本")
async def update_product_cost(
    sku_id: str,
    request: ProductCostUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProductCostService = Depends(get_product_cost_service)
):
    """更新产品标准成本"""
    product_cost = await service.update(sku_id, request)
    return Result.ok(data=ProductCostResponse.model_validate(product_cost))


# ============ 成本分摊规则管理 ============

@router.post("/allocation-rule", response_model=Result[CostAllocationRuleResponse], summary="创建成本分摊规则")
async def create_allocation_rule(
    request: CostAllocationRuleCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: CostAllocationRuleService = Depends(get_allocation_rule_service)
):
    """创建成本分摊规则"""
    rule = await service.create(request, created_by=current_user.username)
    return Result.ok(data=CostAllocationRuleResponse.model_validate(rule))


@router.get("/allocation-rule/{rule_code}", response_model=Result[CostAllocationRuleResponse], summary="获取成本分摊规则")
async def get_allocation_rule(
    rule_code: str,
    service: CostAllocationRuleService = Depends(get_allocation_rule_service)
):
    """获取成本分摊规则详情"""
    rule = await service.get_by_code(rule_code)
    if not rule:
        return Result.fail(code="NOT_FOUND", message="成本分摊规则不存在")
    return Result.ok(data=CostAllocationRuleResponse.model_validate(rule))
