"""报工中心 - REST API 路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.database import get_db
from erp_common.schemas.base import Result, PageResult
from erp_common.auth import get_current_user, CurrentUser
from erp_common.utils.kafka_utils import get_kafka_producer, KafkaProducer

from .service import JobService, LossService, WorkHourService
from .schemas import (
    ReportJobCreate, ReportJobUpdate, ReportJobResponse,
    ReportLossCreate, ReportLossResponse,
    MoWorkHourCreate, MoWorkHourResponse,
    ReportJobQuery, ReportLossQuery
)

router = APIRouter(prefix="/job", tags=["报工管理"])


def get_job_service(
    db: AsyncSession = Depends(get_db),
    kafka: Optional[KafkaProducer] = Depends(get_kafka_producer)
) -> JobService:
    return JobService(db, kafka)


def get_loss_service(
    db: AsyncSession = Depends(get_db),
    kafka: Optional[KafkaProducer] = Depends(get_kafka_producer)
) -> LossService:
    return LossService(db, kafka)


def get_workhour_service(db: AsyncSession = Depends(get_db)) -> WorkHourService:
    return WorkHourService(db)


# ============ 报工管理 ============

@router.post("/report", response_model=Result[ReportJobResponse], summary="创建报工记录")
async def create_job_report(
    request: ReportJobCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: JobService = Depends(get_job_service)
):
    """创建报工记录"""
    report = await service.create_job_report(request, reported_by=current_user.username)
    return Result.ok(data=ReportJobResponse.model_validate(report))


@router.get("/report/{report_id}", response_model=Result[ReportJobResponse], summary="获取报工记录")
async def get_job_report(
    report_id: int,
    service: JobService = Depends(get_job_service)
):
    """获取报工记录详情"""
    report = await service.get_job_report_by_id(report_id)
    if not report:
        return Result.fail(code="NOT_FOUND", message="报工记录不存在")
    return Result.ok(data=ReportJobResponse.model_validate(report))


@router.put("/report/{report_id}", response_model=Result[ReportJobResponse], summary="更新报工记录")
async def update_job_report(
    report_id: int,
    request: ReportJobUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: JobService = Depends(get_job_service)
):
    """更新报工记录"""
    report = await service.update_job_report(report_id, request)
    return Result.ok(data=ReportJobResponse.model_validate(report))


@router.post("/report/{report_id}/confirm", response_model=Result[ReportJobResponse], summary="确认报工记录")
async def confirm_job_report(
    report_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: JobService = Depends(get_job_service)
):
    """确认报工记录"""
    report = await service.confirm_job_report(report_id, confirmed_by=current_user.username)
    return Result.ok(data=ReportJobResponse.model_validate(report))


@router.post("/report/{report_id}/reject", response_model=Result[ReportJobResponse], summary="拒绝报工记录")
async def reject_job_report(
    report_id: int,
    reason: str = Query(..., description="拒绝原因"),
    current_user: CurrentUser = Depends(get_current_user),
    service: JobService = Depends(get_job_service)
):
    """拒绝报工记录"""
    report = await service.reject_job_report(report_id, reason, rejected_by=current_user.username)
    return Result.ok(data=ReportJobResponse.model_validate(report))


@router.get("/report/list", response_model=Result[PageResult[ReportJobResponse]], summary="报工记录列表")
async def list_job_reports(
    mo_id: Optional[int] = Query(None, description="生产订单ID"),
    mo_no: Optional[str] = Query(None, description="生产订单号"),
    product_sku_id: Optional[str] = Query(None, description="成品SKU ID"),
    worker_id: Optional[int] = Query(None, description="工人ID"),
    status: Optional[str] = Query(None, description="状态"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: JobService = Depends(get_job_service)
):
    """报工记录列表"""
    query = ReportJobQuery(
        mo_id=mo_id,
        mo_no=mo_no,
        product_sku_id=product_sku_id,
        worker_id=worker_id,
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
    
    reports, total = await service.query_job_reports(query)
    return Result.ok(data=PageResult(
        items=[ReportJobResponse.model_validate(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size
    ))


# ============ 报损管理 ============

@router.post("/loss", response_model=Result[ReportLossResponse], summary="创建报损记录")
async def create_loss_report(
    request: ReportLossCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: LossService = Depends(get_loss_service)
):
    """创建报损记录"""
    loss = await service.create_loss_report(request, reported_by=current_user.username)
    return Result.ok(data=ReportLossResponse.model_validate(loss))


@router.get("/loss/list", response_model=Result[PageResult[ReportLossResponse]], summary="报损记录列表")
async def list_loss_reports(
    mo_id: Optional[int] = Query(None, description="生产订单ID"),
    mo_no: Optional[str] = Query(None, description="生产订单号"),
    material_sku_id: Optional[str] = Query(None, description="物料SKU ID"),
    loss_type: Optional[str] = Query(None, description="损耗类型"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: LossService = Depends(get_loss_service)
):
    """报损记录列表"""
    query = ReportLossQuery(
        mo_id=mo_id,
        mo_no=mo_no,
        material_sku_id=material_sku_id,
        loss_type=loss_type,
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
    
    losses, total = await service.query_loss_reports(query)
    return Result.ok(data=PageResult(
        items=[ReportLossResponse.model_validate(l) for l in losses],
        total=total,
        page=page,
        page_size=page_size
    ))


# ============ 工时管理 ============

@router.post("/work-hour", response_model=Result[MoWorkHourResponse], summary="记录工时")
async def record_work_hour(
    request: MoWorkHourCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: WorkHourService = Depends(get_workhour_service)
):
    """记录工时"""
    work_hour = await service.record_work_hour(request, recorded_by=current_user.username)
    return Result.ok(data=MoWorkHourResponse.model_validate(work_hour))


@router.get("/work-hour/mo/{mo_id}", response_model=Result[list[MoWorkHourResponse]], summary="获取生产订单工时")
async def get_work_hours_by_mo(
    mo_id: int,
    service: WorkHourService = Depends(get_workhour_service)
):
    """获取生产订单工时记录"""
    work_hours = await service.get_work_hours_by_mo(mo_id)
    return Result.ok(data=[MoWorkHourResponse.model_validate(wh) for wh in work_hours])


@router.get("/work-hour/worker/{worker_id}", response_model=Result[list[MoWorkHourResponse]], summary="获取工人工时")
async def get_work_hours_by_worker(
    worker_id: int,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    service: WorkHourService = Depends(get_workhour_service)
):
    """获取工人工时记录"""
    from datetime import datetime
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    work_hours = await service.get_work_hours_by_worker(worker_id, start_dt, end_dt)
    return Result.ok(data=[MoWorkHourResponse.model_validate(wh) for wh in work_hours])
