"""会员中心 - Pydantic Schema"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ============ 枚举类型 ============

class MemberStatus(str, Enum):
    """会员状态"""
    ACTIVE = "ACTIVE"       # 活跃
    INACTIVE = "INACTIVE"   # 非活跃
    BANNED = "BANNED"       # 禁用


class LevelStatus(str, Enum):
    """等级状态"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class PointChangeType(str, Enum):
    """积分变动类型"""
    EARN = "EARN"           # 获得
    CONSUME = "CONSUME"     # 消费
    EXPIRE = "EXPIRE"       # 过期
    ADJUST = "ADJUST"       # 调整


class CouponType(str, Enum):
    """优惠券类型"""
    DISCOUNT = "DISCOUNT"   # 折扣券
    CASH = "CASH"           # 代金券
    EXCHANGE = "EXCHANGE"   # 兑换券


class CouponStatus(str, Enum):
    """优惠券状态"""
    UNUSED = "UNUSED"       # 未使用
    USED = "USED"           # 已使用
    EXPIRED = "EXPIRED"     # 已过期
    CANCELLED = "CANCELLED" # 已取消


class SourceType(str, Enum):
    """来源类型"""
    ORDER = "ORDER"         # 订单
    RECHARGE = "RECHARGE"   # 充值
    PROMOTION = "PROMOTION" # 促销
    ADJUST = "ADJUST"       # 调整


# ============ 会员 Schema ============

class MemberBase(BaseModel):
    """会员基础"""
    phone: str = Field(..., max_length=20, description="手机号")
    name: str = Field(..., max_length=50, description="姓名")
    gender: Optional[str] = Field(None, max_length=10, description="性别: M/F")
    birthday: Optional[date] = Field(None, description="生日")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    level_id: int = Field(..., description="会员等级ID")
    level_name: str = Field(..., max_length=50, description="会员等级名称")
    register_channel: str = Field(default="ONLINE", max_length=20, description="注册渠道")
    register_store: Optional[str] = Field(None, max_length=50, description="注册门店")


class MemberCreate(MemberBase):
    """创建会员"""
    referee_id: Optional[int] = Field(None, description="推荐人ID")
    referee_name: Optional[str] = Field(None, max_length=50, description="推荐人姓名")
    remark: Optional[str] = Field(None, description="备注")


class MemberUpdate(BaseModel):
    """更新会员"""
    name: Optional[str] = Field(None, max_length=50, description="姓名")
    gender: Optional[str] = Field(None, max_length=10, description="性别: M/F")
    birthday: Optional[date] = Field(None, description="生日")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    referee_id: Optional[int] = Field(None, description="推荐人ID")
    referee_name: Optional[str] = Field(None, max_length=50, description="推荐人姓名")
    remark: Optional[str] = Field(None, description="备注")


class MemberResponse(MemberBase):
    """会员响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    member_no: str
    points: Decimal
    total_consumed: Decimal
    status: str
    referee_id: Optional[int] = None
    referee_name: Optional[str] = None
    register_channel: str
    register_store: Optional[str] = None
    remark: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============ 会员等级 Schema ============

class MemberLevelBase(BaseModel):
    """会员等级基础"""
    code: str = Field(..., max_length=20, description="等级编码")
    name: str = Field(..., max_length=50, description="等级名称")
    discount_rate: Decimal = Field(..., ge=0, le=100, description="折扣率 %")
    points_multiplier: Decimal = Field(..., ge=0, description="积分倍数")
    min_points: Decimal = Field(..., ge=0, description="最低积分")
    min_consumed: Decimal = Field(..., ge=0, description="最低消费金额")


class MemberLevelCreate(MemberLevelBase):
    """创建会员等级"""
    remark: Optional[str] = Field(None, description="备注")


class MemberLevelUpdate(BaseModel):
    """更新会员等级"""
    name: Optional[str] = Field(None, max_length=50, description="等级名称")
    discount_rate: Optional[Decimal] = Field(None, ge=0, le=100, description="折扣率 %")
    points_multiplier: Optional[Decimal] = Field(None, ge=0, description="积分倍数")
    min_points: Optional[Decimal] = Field(None, ge=0, description="最低积分")
    min_consumed: Optional[Decimal] = Field(None, ge=0, description="最低消费金额")
    remark: Optional[str] = Field(None, description="备注")


class MemberLevelResponse(MemberLevelBase):
    """会员等级响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: str
    remark: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============ 积分 Schema ============

class MemberPointBase(BaseModel):
    """会员积分基础"""
    member_id: int = Field(..., description="会员ID")
    member_no: str = Field(..., max_length=50, description="会员号")
    change_type: PointChangeType = Field(..., description="变动类型")
    change_points: Decimal = Field(..., description="变动积分数")
    source_type: SourceType = Field(..., description="来源类型")
    source_no: Optional[str] = Field(None, max_length=50, description="来源单号")
    expire_date: Optional[date] = Field(None, description="过期日期")
    remark: Optional[str] = Field(None, description="备注")


class MemberPointCreate(MemberPointBase):
    """创建积分记录"""
    pass


class MemberPointResponse(MemberPointBase):
    """积分记录响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    balance_before: Decimal
    balance_after: Decimal
    expired_points: Decimal
    operator: Optional[str] = None
    created_at: datetime


# ============ 优惠券 Schema ============

class MemberCouponBase(BaseModel):
    """会员优惠券基础"""
    member_id: int = Field(..., description="会员ID")
    member_no: str = Field(..., max_length=50, description="会员号")
    name: str = Field(..., max_length=100, description="优惠券名称")
    coupon_type: CouponType = Field(..., description="优惠券类型")
    value: Decimal = Field(..., gt=0, description="优惠券面值")
    min_amount: Decimal = Field(default=0, ge=0, description="最低使用金额")
    valid_from: date = Field(..., description="有效开始日期")
    valid_to: date = Field(..., description="有效结束日期")
    usage_limit: int = Field(default=1, ge=1, description="使用次数限制")
    source_type: SourceType = Field(..., description="来源类型")
    source_no: Optional[str] = Field(None, max_length=50, description="来源单号")


class MemberCouponCreate(MemberCouponBase):
    """创建会员优惠券"""
    remark: Optional[str] = Field(None, description="备注")


class MemberCouponUpdate(BaseModel):
    """更新会员优惠券"""
    remark: Optional[str] = Field(None, description="备注")


class MemberCouponResponse(MemberCouponBase):
    """会员优惠券响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    coupon_no: str
    used_count: int
    status: str
    used_at: Optional[datetime] = None
    used_order_no: Optional[str] = None
    remark: Optional[str] = None
    issued_by: Optional[str] = None
    used_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============ 会员操作 Schema ============

class EarnPointsRequest(BaseModel):
    """获得积分请求"""
    member_id: int = Field(..., description="会员ID")
    change_points: Decimal = Field(..., gt=0, description="获得积分数")
    source_type: SourceType = Field(..., description="来源类型")
    source_no: str = Field(..., max_length=50, description="来源单号")
    remark: Optional[str] = Field(None, description="备注")


class ConsumePointsRequest(BaseModel):
    """消费积分请求"""
    member_id: int = Field(..., description="会员ID")
    change_points: Decimal = Field(..., gt=0, description="消费积分数")
    source_type: SourceType = Field(..., description="来源类型")
    source_no: str = Field(..., max_length=50, description="来源单号")
    remark: Optional[str] = Field(None, description="备注")


class IssueCouponRequest(BaseModel):
    """发放优惠券请求"""
    member_id: int = Field(..., description="会员ID")
    name: str = Field(..., max_length=100, description="优惠券名称")
    coupon_type: CouponType = Field(..., description="优惠券类型")
    value: Decimal = Field(..., gt=0, description="优惠券面值")
    min_amount: Decimal = Field(default=0, ge=0, description="最低使用金额")
    valid_from: date = Field(..., description="有效开始日期")
    valid_to: date = Field(..., description="有效结束日期")
    usage_limit: int = Field(default=1, ge=1, description="使用次数限制")
    source_type: SourceType = Field(..., description="来源类型")
    source_no: str = Field(..., max_length=50, description="来源单号")
    remark: Optional[str] = Field(None, description="备注")


class UseCouponRequest(BaseModel):
    """使用优惠券请求"""
    coupon_no: str = Field(..., max_length=50, description="优惠券编号")
    order_no: str = Field(..., max_length=50, description="订单号")
    amount: Decimal = Field(..., ge=0, description="使用金额")


# ============ 查询 Schema ============

class MemberQuery(BaseModel):
    """会员查询参数"""
    phone: Optional[str] = Field(None, description="手机号")
    member_no: Optional[str] = Field(None, description="会员号")
    level_id: Optional[int] = Field(None, description="等级ID")
    status: Optional[MemberStatus] = Field(None, description="状态")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class MemberPointQuery(BaseModel):
    """积分记录查询参数"""
    member_id: Optional[int] = Field(None, description="会员ID")
    change_type: Optional[PointChangeType] = Field(None, description="变动类型")
    source_type: Optional[SourceType] = Field(None, description="来源类型")
    source_no: Optional[str] = Field(None, description="来源单号")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class MemberCouponQuery(BaseModel):
    """优惠券查询参数"""
    member_id: Optional[int] = Field(None, description="会员ID")
    coupon_type: Optional[CouponType] = Field(None, description="优惠券类型")
    status: Optional[CouponStatus] = Field(None, description="状态")
    valid_from: Optional[date] = Field(None, description="有效开始日期")
    valid_to: Optional[date] = Field(None, description="有效结束日期")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ============ 事件 Schema ============

class MemberPointChangedEvent(BaseModel):
    """会员积分变动事件"""
    event_type: str = "MemberPointChanged"
    member_id: int
    member_no: str
    change_points: Decimal
    balance_after: Decimal
    change_type: str
    source_type: str
    source_no: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
