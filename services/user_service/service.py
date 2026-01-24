"""
用户中心 - 业务服务层
"""

import logging
from typing import List, Optional

from sqlalchemy import func, or_, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.config import settings
from erp_common.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from erp_common.schemas.base import PageResult
from erp_common.schemas.events import UserCreatedEvent, UserUpdatedEvent
from erp_common.utils.jwt_utils import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from erp_common.utils.kafka_utils import KafkaProducer, KafkaTopics
from erp_common.utils.redis_utils import RedisClient

from .models import Org, Role, User, UserRole
from .schemas import (
    LoginRequest,
    LoginResponse,
    RoleAssignRequest,
    UserBrief,
    UserCreate,
    UserQuery,
    UserResponse,
    UserUpdate,
)

logger = logging.getLogger(__name__)


class AuthService:
    """认证服务"""
    
    def __init__(
        self, 
        db: AsyncSession, 
        redis: Optional[RedisClient] = None
    ):
        self.db = db
        self.redis = redis
    
    async def login(self, data: LoginRequest) -> LoginResponse:
        """
        用户登录
        
        Args:
            data: 登录请求数据
        
        Returns:
            登录响应（包含 Token）
        """
        # 1. 查询用户
        result = await self.db.execute(
            select(User).where(User.username == data.username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthenticationError("Invalid username or password")
        
        # 2. 验证密码
        if not verify_password(data.password, user.password):
            raise AuthenticationError("Invalid username or password")
        
        # 3. 检查用户状态
        if user.status != 1:
            raise AuthenticationError("User account is disabled")
        
        # 4. 获取用户角色
        roles = [role.role_code for role in user.roles]
        
        # 5. 生成 Token
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            roles=roles,
        )
        
        # 6. 存储 Token 到 Redis（可选，用于注销）
        if self.redis:
            token_key = f"token:{user.id}"
            await self.redis.set(
                token_key, 
                access_token, 
                expire=settings.jwt_expire_minutes * 60
            )
        
        logger.info(f"User logged in: {user.username}")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expire_minutes * 60,
            user=UserBrief(
                id=user.id,
                username=user.username,
                name=user.name,
                roles=roles,
            )
        )
    
    async def logout(self, user_id: int) -> bool:
        """
        用户注销
        
        Args:
            user_id: 用户ID
        
        Returns:
            是否成功
        """
        if self.redis:
            token_key = f"token:{user_id}"
            await self.redis.delete(token_key)
        
        logger.info(f"User logged out: {user_id}")
        return True


class UserService:
    """用户服务"""
    
    def __init__(
        self, 
        db: AsyncSession,
        kafka: Optional[KafkaProducer] = None
    ):
        self.db = db
        self.kafka = kafka
    
    async def create_user(self, data: UserCreate, operator: str = None) -> User:
        """
        创建用户
        
        Args:
            data: 创建用户请求数据
            operator: 操作人
        
        Returns:
            创建的用户对象
        """
        # 1. 检查用户名是否存在
        existing = await self.db.execute(
            select(User).where(User.username == data.username)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Username '{data.username}' already exists")
        
        # 2. 创建用户
        user = User(
            username=data.username,
            password=get_password_hash(data.password),
            name=data.name,
            mobile=data.mobile,
            email=data.email,
            org_id=data.org_id,
            status=1,
        )
        self.db.add(user)
        await self.db.flush()
        
        # 3. 分配角色
        for role_code in data.roles:
            user_role = UserRole(user_id=user.id, role_code=role_code)
            self.db.add(user_role)
        
        await self.db.flush()
        
        # 4. 发布事件
        if self.kafka:
            event = UserCreatedEvent(
                aggregate_id=str(user.id),
                operator=operator,
                payload={
                    "id": user.id,
                    "username": user.username,
                    "name": user.name,
                }
            )
            await self.kafka.send(KafkaTopics.USER_EVENTS, event)
        
        logger.info(f"User created: {user.username}")
        return user
    
    async def get_user(self, user_id: int) -> User:
        """获取用户详情"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError("User", user_id)
        
        return user
    
    async def get_user_by_username(self, username: str) -> User:
        """通过用户名获取用户"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError("User", username)
        
        return user
    
    async def update_user(
        self, 
        user_id: int, 
        data: UserUpdate,
        operator: str = None
    ) -> User:
        """更新用户"""
        user = await self.get_user(user_id)
        
        # 更新字段
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await self.db.flush()
        
        # 发布事件
        if self.kafka:
            event = UserUpdatedEvent(
                aggregate_id=str(user.id),
                operator=operator,
                payload={
                    "id": user.id,
                    "username": user.username,
                    "updated_fields": list(update_data.keys()),
                }
            )
            await self.kafka.send(KafkaTopics.USER_EVENTS, event)
        
        logger.info(f"User updated: {user.username}")
        return user
    
    async def list_users(self, query: UserQuery) -> PageResult[UserResponse]:
        """分页查询用户列表"""
        # 构建查询条件
        conditions = []
        
        if query.keyword:
            conditions.append(
                or_(
                    User.username.contains(query.keyword),
                    User.name.contains(query.keyword),
                    User.mobile.contains(query.keyword),
                )
            )
        
        if query.org_id is not None:
            conditions.append(User.org_id == query.org_id)
        
        if query.status is not None:
            conditions.append(User.status == query.status)
        
        # 查询总数
        count_stmt = select(func.count(User.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar()
        
        # 查询数据
        stmt = select(User).order_by(User.id.desc())
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.offset(query.offset).limit(query.size)
        
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        
        return PageResult(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=query.page,
            size=query.size,
        )
    
    async def assign_roles(self, request: RoleAssignRequest) -> User:
        """
        分配用户角色
        
        Args:
            request: 角色分配请求
        
        Returns:
            更新后的用户对象
        """
        user = await self.get_user(request.user_id)
        
        # 删除现有角色
        await self.db.execute(
            delete(UserRole).where(UserRole.user_id == user.id)
        )
        
        # 添加新角色
        for role_code in request.roles:
            user_role = UserRole(user_id=user.id, role_code=role_code)
            self.db.add(user_role)
        
        await self.db.flush()
        
        # 重新加载用户
        await self.db.refresh(user)
        
        logger.info(f"Roles assigned to user {user.username}: {request.roles}")
        return user
    
    async def change_password(
        self, 
        user_id: int, 
        old_password: str, 
        new_password: str
    ) -> bool:
        """修改密码"""
        user = await self.get_user(user_id)
        
        # 验证旧密码
        if not verify_password(old_password, user.password):
            raise ValidationError("Old password is incorrect")
        
        # 更新密码
        user.password = get_password_hash(new_password)
        await self.db.flush()
        
        logger.info(f"Password changed for user: {user.username}")
        return True


class RoleService:
    """角色服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_roles(self) -> List[Role]:
        """获取所有角色"""
        result = await self.db.execute(select(Role))
        return list(result.scalars().all())
    
    async def get_role(self, role_code: str) -> Role:
        """获取角色"""
        result = await self.db.execute(
            select(Role).where(Role.code == role_code)
        )
        role = result.scalar_one_or_none()
        
        if not role:
            raise NotFoundError("Role", role_code)
        
        return role
