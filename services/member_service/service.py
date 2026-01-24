"""会员中心 - 业务服务层"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.config import settings
from erp_common.exceptions import BusinessException
from erp_common.utils.kafka_utils import KafkaProducer

from .models import Member, MemberLevel, MemberPoint, MemberCoupon
from .schemas import (
    MemberCreate, MemberUpdate, MemberResponse,
    MemberLevelCreate, MemberLevelUpdate, MemberLevelResponse,
    MemberPointCreate, MemberPointResponse,
    MemberCouponCreate, MemberCouponUpdate, MemberCouponResponse,
    EarnPointsRequest, ConsumePointsRequest, IssueCouponRequest, UseCouponRequest,
    MemberQuery, MemberPointQuery, MemberCouponQuery,
    MemberStatus, LevelStatus, PointChangeType, CouponStatus, SourceType
)


def generate_member_no() -> str:
    """生成会员号"""
    return f"M{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"


def generate_coupon_no() -> str:
    """生成优惠券号"""
    return f"C{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


class MemberService:
    """会员服务"""
    
    def __init__(self, db: AsyncSession, kafka: Optional[KafkaProducer] = None):
        self.db = db
        self.kafka = kafka
    
    async def create(self, data: MemberCreate, created_by: str = None) -> Member:
        """创建会员"""
        # 检查手机号是否已存在
        existing = await self.db.execute(
            select(Member).where(Member.phone == data.phone)
        )
        if existing.scalar_one_or_none():
            raise BusinessException(code="PHONE_EXISTS", message=f"手机号已存在: {data.phone}")
        
        # 生成会员号
        member_no = generate_member_no()
        
        # 获取等级信息
        level_result = await self.db.execute(
            select(MemberLevel).where(MemberLevel.id == data.level_id)
        )
        level = level_result.scalar_one_or_none()
        if not level:
            raise BusinessException(code="LEVEL_NOT_FOUND", message=f"会员等级不存在: {data.level_id}")
        
        # 创建会员
        member = Member(
            member_no=member_no,
            phone=data.phone,
            name=data.name,
            gender=data.gender,
            birthday=data.birthday,
            email=data.email,
            level_id=level.id,
            level_name=level.name,
            points=Decimal("0"),  # 新会员积分从0开始
            total_consumed=Decimal("0"),  # 新会员消费金额为0
            status=MemberStatus.ACTIVE.value,
            referee_id=data.referee_id,
            referee_name=data.referee_name,
            register_channel=data.register_channel,
            register_store=data.register_store,
            remark=data.remark,
            created_by=created_by
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member
    
    async def get_by_id(self, member_id: int) -> Optional[Member]:
        """根据ID获取会员"""
        result = await self.db.execute(
            select(Member).where(Member.id == member_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_phone(self, phone: str) -> Optional[Member]:
        """根据手机号获取会员"""
        result = await self.db.execute(
            select(Member).where(Member.phone == phone)
        )
        return result.scalar_one_or_none()
    
    async def get_by_member_no(self, member_no: str) -> Optional[Member]:
        """根据会员号获取会员"""
        result = await self.db.execute(
            select(Member).where(Member.member_no == member_no)
        )
        return result.scalar_one_or_none()
    
    async def update(self, member_id: int, data: MemberUpdate) -> Member:
        """更新会员信息"""
        member = await self.get_by_id(member_id)
        if not member:
            raise BusinessException(code="NOT_FOUND", message="会员不存在")
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(member, key, value)
        
        await self.db.commit()
        await self.db.refresh(member)
        return member
    
    async def query(self, query: MemberQuery) -> Tuple[List[Member], int]:
        """查询会员"""
        stmt = select(Member)
        
        if query.phone:
            stmt = stmt.where(Member.phone.contains(query.phone))
        if query.member_no:
            stmt = stmt.where(Member.member_no.contains(query.member_no))
        if query.level_id:
            stmt = stmt.where(Member.level_id == query.level_id)
        if query.status:
            stmt = stmt.where(Member.status == query.status.value)
        
        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # 分页
        stmt = stmt.order_by(Member.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        
        result = await self.db.execute(stmt)
        members = result.scalars().all()
        
        return list(members), total or 0


class MemberLevelService:
    """会员等级服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, data: MemberLevelCreate, created_by: str = None) -> MemberLevel:
        """创建会员等级"""
        # 检查等级编码是否已存在
        existing = await self.db.execute(
            select(MemberLevel).where(MemberLevel.code == data.code)
        )
        if existing.scalar_one_or_none():
            raise BusinessException(code="CODE_EXISTS", message=f"等级编码已存在: {data.code}")
        
        level = MemberLevel(
            code=data.code,
            name=data.name,
            discount_rate=data.discount_rate,
            points_multiplier=data.points_multiplier,
            min_points=data.min_points,
            min_consumed=data.min_consumed,
            status=LevelStatus.ACTIVE.value,
            remark=data.remark,
            created_by=created_by
        )
        self.db.add(level)
        await self.db.commit()
        await self.db.refresh(level)
        return level
    
    async def get_by_id(self, level_id: int) -> Optional[MemberLevel]:
        """根据ID获取会员等级"""
        result = await self.db.execute(
            select(MemberLevel).where(MemberLevel.id == level_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_code(self, code: str) -> Optional[MemberLevel]:
        """根据编码获取会员等级"""
        result = await self.db.execute(
            select(MemberLevel).where(MemberLevel.code == code)
        )
        return result.scalar_one_or_none()
    
    async def update(self, level_id: int, data: MemberLevelUpdate) -> MemberLevel:
        """更新会员等级"""
        level = await self.get_by_id(level_id)
        if not level:
            raise BusinessException(code="NOT_FOUND", message="会员等级不存在")
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(level, key, value)
        
        await self.db.commit()
        await self.db.refresh(level)
        return level


class MemberPointService:
    """会员积分服务"""
    
    def __init__(self, db: AsyncSession, kafka: Optional[KafkaProducer] = None):
        self.db = db
        self.kafka = kafka
    
    async def earn_points(self, request: EarnPointsRequest, operator: str = None) -> MemberPoint:
        """获得积分"""
        # 获取会员信息
        member = await self.db.execute(
            select(Member).where(Member.id == request.member_id)
        )
        member = member.scalar_one_or_none()
        if not member:
            raise BusinessException(code="MEMBER_NOT_FOUND", message="会员不存在")
        
        # 计算新余额
        new_balance = member.points + request.change_points
        
        # 更新会员积分
        member.points = new_balance
        await self.db.flush()
        
        # 创建积分记录
        point_record = MemberPoint(
            member_id=request.member_id,
            member_no=member.member_no,
            change_type=request.change_type.value,
            change_points=request.change_points,
            balance_before=member.points - request.change_points,
            balance_after=new_balance,
            expired_points=Decimal("0"),
            source_type=request.source_type.value,
            source_no=request.source_no,
            expire_date=request.expire_date,
            remark=request.remark,
            operator=operator
        )
        self.db.add(point_record)
        
        await self.db.commit()
        await self.db.refresh(point_record)
        
        # 发布积分变动事件
        await self._publish_point_changed_event(
            member.id, member.member_no, request.change_points, new_balance,
            request.change_type.value, request.source_type.value, request.source_no
        )
        
        return point_record
    
    async def consume_points(self, request: ConsumePointsRequest, operator: str = None) -> MemberPoint:
        """消费积分"""
        # 获取会员信息
        member = await self.db.execute(
            select(Member).where(Member.id == request.member_id)
        )
        member = member.scalar_one_or_none()
        if not member:
            raise BusinessException(code="MEMBER_NOT_FOUND", message="会员不存在")
        
        # 检查积分是否足够
        if member.points < request.change_points:
            raise BusinessException(
                code="INSUFFICIENT_POINTS",
                message=f"积分不足: 当前={member.points}, 需要={request.change_points}"
            )
        
        # 计算新余额
        new_balance = member.points - request.change_points
        
        # 更新会员积分
        member.points = new_balance
        await self.db.flush()
        
        # 创建积分记录
        point_record = MemberPoint(
            member_id=request.member_id,
            member_no=member.member_no,
            change_type=PointChangeType.CONSUME.value,
            change_points=-request.change_points,  # 消费为负数
            balance_before=member.points + request.change_points,
            balance_after=new_balance,
            expired_points=Decimal("0"),
            source_type=request.source_type.value,
            source_no=request.source_no,
            expire_date=None,
            remark=request.remark,
            operator=operator
        )
        self.db.add(point_record)
        
        await self.db.commit()
        await self.db.refresh(point_record)
        
        # 发布积分变动事件
        await self._publish_point_changed_event(
            member.id, member.member_no, -request.change_points, new_balance,
            PointChangeType.CONSUME.value, request.source_type.value, request.source_no
        )
        
        return point_record
    
    async def get_point_history(self, query: MemberPointQuery) -> Tuple[List[MemberPoint], int]:
        """获取积分历史记录"""
        stmt = select(MemberPoint)
        
        if query.member_id:
            stmt = stmt.where(MemberPoint.member_id == query.member_id)
        if query.change_type:
            stmt = stmt.where(MemberPoint.change_type == query.change_type.value)
        if query.source_type:
            stmt = stmt.where(MemberPoint.source_type == query.source_type.value)
        if query.source_no:
            stmt = stmt.where(MemberPoint.source_no == query.source_no)
        if query.start_date:
            stmt = stmt.where(MemberPoint.created_at >= query.start_date)
        if query.end_date:
            stmt = stmt.where(MemberPoint.created_at <= query.end_date)
        
        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # 分页
        stmt = stmt.order_by(MemberPoint.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        
        result = await self.db.execute(stmt)
        records = result.scalars().all()
        
        return list(records), total or 0
    
    async def _publish_point_changed_event(
        self, member_id: int, member_no: str, change_points: Decimal, 
        balance_after: Decimal, change_type: str, source_type: str, source_no: str
    ):
        """发布积分变动事件"""
        if not self.kafka:
            return
        
        from .schemas import MemberPointChangedEvent
        event = MemberPointChangedEvent(
            member_id=member_id,
            member_no=member_no,
            change_points=change_points,
            balance_after=balance_after,
            change_type=change_type,
            source_type=source_type,
            source_no=source_no
        )
        
        try:
            await self.kafka.send(
                topic="member-events",
                key=str(member_id),
                value=event.model_dump_json()
            )
        except Exception as e:
            print(f"Failed to publish MemberPointChanged event: {e}")


class MemberCouponService:
    """会员优惠券服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def issue_coupon(self, request: IssueCouponRequest, issued_by: str = None) -> MemberCoupon:
        """发放优惠券"""
        # 获取会员信息
        member = await self.db.execute(
            select(Member).where(Member.id == request.member_id)
        )
        member = member.scalar_one_or_none()
        if not member:
            raise BusinessException(code="MEMBER_NOT_FOUND", message="会员不存在")
        
        # 生成优惠券号
        coupon_no = generate_coupon_no()
        
        # 创建优惠券
        coupon = MemberCoupon(
            coupon_no=coupon_no,
            member_id=request.member_id,
            member_no=member.member_no,
            name=request.name,
            coupon_type=request.coupon_type.value,
            value=request.value,
            min_amount=request.min_amount,
            valid_from=request.valid_from,
            valid_to=request.valid_to,
            usage_limit=request.usage_limit,
            source_type=request.source_type.value,
            source_no=request.source_no,
            remark=request.remark,
            issued_by=issued_by
        )
        self.db.add(coupon)
        
        await self.db.commit()
        await self.db.refresh(coupon)
        return coupon
    
    async def use_coupon(self, request: UseCouponRequest, used_by: str = None) -> MemberCoupon:
        """使用优惠券"""
        # 获取优惠券信息
        coupon = await self.db.execute(
            select(MemberCoupon).where(MemberCoupon.coupon_no == request.coupon_no)
        )
        coupon = coupon.scalar_one_or_none()
        if not coupon:
            raise BusinessException(code="COUPON_NOT_FOUND", message="优惠券不存在")
        
        # 检查优惠券状态
        if coupon.status != CouponStatus.UNUSED.value:
            raise BusinessException(code="COUPON_INVALID", message="优惠券不可用")
        
        # 检查是否过期
        if coupon.valid_to < date.today():
            coupon.status = CouponStatus.EXPIRED.value
            await self.db.commit()
            raise BusinessException(code="COUPON_EXPIRED", message="优惠券已过期")
        
        # 检查使用次数
        if coupon.used_count >= coupon.usage_limit:
            coupon.status = CouponStatus.USED.value
            await self.db.commit()
            raise BusinessException(code="COUPON_EXHAUSTED", message="优惠券使用次数已达上限")
        
        # 检查订单金额是否满足最低使用要求
        if request.amount < coupon.min_amount:
            raise BusinessException(
                code="INSUFFICIENT_AMOUNT",
                message=f"订单金额不足: 需要≥{coupon.min_amount}, 当前={request.amount}"
            )
        
        # 更新优惠券状态
        coupon.used_count += 1
        if coupon.used_count >= coupon.usage_limit:
            coupon.status = CouponStatus.USED.value
        else:
            coupon.status = CouponStatus.USED.value  # 一张优惠券通常只能用一次
        
        coupon.used_at = datetime.utcnow()
        coupon.used_order_no = request.order_no
        coupon.used_by = used_by
        
        await self.db.commit()
        await self.db.refresh(coupon)
        return coupon
    
    async def get_coupons_by_member(self, member_id: int, status: Optional[CouponStatus] = None) -> List[MemberCoupon]:
        """根据会员ID获取优惠券"""
        stmt = select(MemberCoupon).where(MemberCoupon.member_id == member_id)
        
        if status:
            stmt = stmt.where(MemberCoupon.status == status.value)
        else:
            # 只返回未使用且未过期的优惠券
            stmt = stmt.where(
                and_(
                    MemberCoupon.status == CouponStatus.UNUSED.value,
                    MemberCoupon.valid_to >= date.today()
                )
            )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def query_coupons(self, query: MemberCouponQuery) -> Tuple[List[MemberCoupon], int]:
        """查询优惠券"""
        stmt = select(MemberCoupon)
        
        if query.member_id:
            stmt = stmt.where(MemberCoupon.member_id == query.member_id)
        if query.coupon_type:
            stmt = stmt.where(MemberCoupon.coupon_type == query.coupon_type.value)
        if query.status:
            stmt = stmt.where(MemberCoupon.status == query.status.value)
        if query.valid_from:
            stmt = stmt.where(MemberCoupon.valid_to >= query.valid_from)
        if query.valid_to:
            stmt = stmt.where(MemberCoupon.valid_from <= query.valid_to)
        
        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt)
        
        # 分页
        stmt = stmt.order_by(MemberCoupon.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        
        result = await self.db.execute(stmt)
        coupons = result.scalars().all()
        
        return list(coupons), total or 0
