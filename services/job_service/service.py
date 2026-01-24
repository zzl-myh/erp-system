"""报工中心 - 业务服务层"""
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

from .models import ReportJob, ReportLoss, MoWorkHour
from .schemas import (
    ReportJobCreate, ReportJobUpdate, ReportJobResponse,
    ReportLossCreate, ReportLossResponse,
    MoWorkHourCreate, MoWorkHourResponse,
    ReportJobQuery, ReportLossQuery,
    ReportJobStatus, LossType
)


def generate_report_no() -> str:
    """生成报工单号"""
    return f"RJ{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


def generate_loss_no() -> str:
    """生成报损单号"""
    return f"RL{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


class JobService:
    """报工服务"""
    
    def __init__(self, db: AsyncSession, kafka: Optional[KafkaProducer] = None):
        self.db = db
        self.kafka = kafka
    
    async def create_job_report(self, data: ReportJobCreate, reported_by: str = None) -> ReportJob:
        """创建报工记录"""
        # 生成报工单号
        report_no = generate_report_no()
        
        # 验证数量
        if data.qualified_qty + data.unqualified_qty != data.reported_qty:
            raise BusinessException(
                code="QTY_MISMATCH",
                message=f"合格数量({data.qualified_qty}) + 不合格数量({data.unqualified_qty}) != 报工数量({data.reported_qty})"
            )
        
        # 创建报工记录
        report = ReportJob(
            report_no=report_no,
            mo_id=data.mo_id,
            mo_no=data.mo_no,
            product_sku_id=data.product_sku_id,
            product_sku_name=data.product_sku_name,
            reported_qty=data.reported_qty,
            qualified_qty=data.qualified_qty,
            unqualified_qty=data.unqualified_qty,
            work_hours=data.work_hours,
            worker_id=data.worker_id,
            worker_name=data.worker_name,
            equipment_id=data.equipment_id,
            equipment_name=data.equipment_name,
            team_id=data.team_id,
            team_name=data.team_name,
            status=ReportJobStatus.REPORTED.value,
            remark=data.remark,
            reported_by=reported_by
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        
        # 发布报工事件
        await self._publish_job_reported_event(report)
        
        return report
    
    async def update_job_report(self, report_id: int, data: ReportJobUpdate) -> ReportJob:
        """更新报工记录"""
        report = await self.get_job_report_by_id(report_id)
        if not report:
            raise BusinessException(code="NOT_FOUND", message="报工记录不存在")
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(report, key, value)
        
        await self.db.commit()
        await self.db.refresh(report)
        return report
    
    async def get_job_report_by_id(self, report_id: int) -> Optional[ReportJob]:
        """根据ID获取报工记录"""
        result = await self.db.execute(
            select(ReportJob).where(ReportJob.id == report_id)
        )
        return result.scalar_one_or_none()
    
    async def get_job_report_by_no(self, report_no: str) -> Optional[ReportJob]:
        """根据单号获取报工记录"""
        result = await self.db.execute(
            select(ReportJob).where(ReportJob.report_no == report_no)
        )
        return result.scalar_one_or_none()
    
    async def query_job_reports(self, query: ReportJobQuery) -> Tuple[List[ReportJob], int]:
        """查询报工记录"""
        stmt = select(ReportJob)
        
        if query.mo_id:
            stmt = stmt.where(ReportJob.mo_id == query.mo_id)
        if query.mo_no:
            stmt = stmt.where(ReportJob.mo_no == query.mo_no)
        if query.product_sku_id:
            stmt = stmt.where(ReportJob.product_sku_id == query.product_sku_id)
        if query.worker_id:
            stmt = stmt.where(ReportJob.worker_id == query.worker_id)
        if query.status:
            stmt = stmt.where(ReportJob.status == query.status.value)
        if query.start_date:
            stmt = stmt.where(ReportJob.report_date >= query.start_date)
        if query.end_date:
            stmt = stmt.where(ReportJob.report_date <= query.end_date)
        
        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # 分页
        stmt = stmt.order_by(ReportJob.report_time.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        
        result = await self.db.execute(stmt)
        reports = result.scalars().all()
        
        return list(reports), total or 0
    
    async def confirm_job_report(self, report_id: int, confirmed_by: str) -> ReportJob:
        """确认报工记录"""
        report = await self.get_job_report_by_id(report_id)
        if not report:
            raise BusinessException(code="NOT_FOUND", message="报工记录不存在")
        
        if report.status != ReportJobStatus.REPORTED.value:
            raise BusinessException(code="INVALID_STATUS", message="只有已报工状态的记录可以确认")
        
        report.status = ReportJobStatus.CONFIRMED.value
        await self.db.commit()
        await self.db.refresh(report)
        
        # 如果是完工报工，尝试完成生产订单
        await self._try_complete_mo_if_needed(report.mo_id)
        
        return report
    
    async def reject_job_report(self, report_id: int, reason: str, rejected_by: str) -> ReportJob:
        """拒绝报工记录"""
        report = await self.get_job_report_by_id(report_id)
        if not report:
            raise BusinessException(code="NOT_FOUND", message="报工记录不存在")
        
        if report.status != ReportJobStatus.REPORTED.value:
            raise BusinessException(code="INVALID_STATUS", message="只有已报工状态的记录可以拒绝")
        
        report.status = ReportJobStatus.REJECTED.value
        await self.db.commit()
        await self.db.refresh(report)
        return report
    
    async def _try_complete_mo_if_needed(self, mo_id: int):
        """尝试完成生产订单（如果报工数量达到计划数量）"""
        # 这里可以调用生产服务来完成生产订单
        # 暂时留空，具体实现依赖于生产服务的API
        pass


class LossService:
    """报损服务"""
    
    def __init__(self, db: AsyncSession, kafka: Optional[KafkaProducer] = None):
        self.db = db
        self.kafka = kafka
    
    async def create_loss_report(self, data: ReportLossCreate, reported_by: str = None) -> ReportLoss:
        """创建报损记录"""
        # 生成报损单号
        loss_no = generate_loss_no()
        
        # 创建报损记录
        loss = ReportLoss(
            loss_no=loss_no,
            mo_id=data.mo_id,
            mo_no=data.mo_no,
            material_sku_id=data.material_sku_id,
            material_sku_name=data.material_sku_name,
            loss_qty=data.loss_qty,
            loss_type=data.loss_type.value,
            loss_reason=data.loss_reason,
            remark=data.remark,
            reported_by=reported_by
        )
        self.db.add(loss)
        await self.db.commit()
        await self.db.refresh(loss)
        return loss
    
    async def get_loss_report_by_id(self, loss_id: int) -> Optional[ReportLoss]:
        """根据ID获取报损记录"""
        result = await self.db.execute(
            select(ReportLoss).where(ReportLoss.id == loss_id)
        )
        return result.scalar_one_or_none()
    
    async def query_loss_reports(self, query: ReportLossQuery) -> Tuple[List[ReportLoss], int]:
        """查询报损记录"""
        stmt = select(ReportLoss)
        
        if query.mo_id:
            stmt = stmt.where(ReportLoss.mo_id == query.mo_id)
        if query.mo_no:
            stmt = stmt.where(ReportLoss.mo_no == query.mo_no)
        if query.material_sku_id:
            stmt = stmt.where(ReportLoss.material_sku_id == query.material_sku_id)
        if query.loss_type:
            stmt = stmt.where(ReportLoss.loss_type == query.loss_type.value)
        if query.start_date:
            stmt = stmt.where(ReportLoss.loss_date >= query.start_date)
        if query.end_date:
            stmt = stmt.where(ReportLoss.loss_date <= query.end_date)
        
        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # 分页
        stmt = stmt.order_by(ReportLoss.loss_time.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        
        result = await self.db.execute(stmt)
        losses = result.scalars().all()
        
        return list(losses), total or 0


class WorkHourService:
    """工时服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def record_work_hour(self, data: MoWorkHourCreate, recorded_by: str = None) -> MoWorkHour:
        """记录工时"""
        work_hour = MoWorkHour(
            mo_id=data.mo_id,
            mo_no=data.mo_no,
            worker_id=data.worker_id,
            worker_name=data.worker_name,
            work_date=data.work_date,
            work_hours=data.work_hours,
            work_content=data.work_content,
            remark=data.remark,
            recorded_by=recorded_by
        )
        self.db.add(work_hour)
        await self.db.commit()
        await self.db.refresh(work_hour)
        return work_hour
    
    async def get_work_hours_by_mo(self, mo_id: int) -> List[MoWorkHour]:
        """根据生产订单获取工时记录"""
        result = await self.db.execute(
            select(MoWorkHour).where(MoWorkHour.mo_id == mo_id)
        )
        return list(result.scalars().all())
    
    async def get_work_hours_by_worker(self, worker_id: int, start_date: date, end_date: date) -> List[MoWorkHour]:
        """根据工人获取工时记录"""
        result = await self.db.execute(
            select(MoWorkHour).where(
                and_(
                    MoWorkHour.worker_id == worker_id,
                    MoWorkHour.work_date >= start_date,
                    MoWorkHour.work_date <= end_date
                )
            )
        )
        return list(result.scalars().all())


    async def _publish_job_reported_event(self, report: ReportJob):
        """发布报工事件"""
        if not self.kafka:
            return
        
        from .schemas import JobReportedEvent
        event = JobReportedEvent(
            report_no=report.report_no,
            mo_no=report.mo_no,
            product_sku_id=report.product_sku_id,
            reported_qty=report.reported_qty,
            qualified_qty=report.qualified_qty,
            unqualified_qty=report.unqualified_qty,
            work_hours=report.work_hours,
            worker_name=report.worker_name
        )
        
        try:
            await self.kafka.send(
                topic="job-events",
                key=report.report_no,
                value=event.model_dump_json()
            )
        except Exception as e:
            print(f"Failed to publish JobReported event: {e}")
