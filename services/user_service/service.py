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
        
        # 返回原始用户对象，由 api 层处理角色信息转换
        return PageResult(
            items=users,
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
    
    async def reset_password(self, user_id: int, new_password: str) -> bool:
        """重置密码（管理员操作）"""
        user = await self.get_user(user_id)
        
        # 直接更新密码
        user.password = get_password_hash(new_password)
        await self.db.flush()
        
        logger.info(f"Password reset for user: {user.username}")
        return True
    
    async def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        user = await self.get_user(user_id)
        
        # 删除用户角色关联
        await self.db.execute(
            delete(UserRole).where(UserRole.user_id == user_id)
        )
        
        # 删除用户
        await self.db.delete(user)
        await self.db.flush()
        
        logger.info(f"User deleted: {user.username}")
        return True


class RoleService:
    """角色服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_roles(self) -> List[Role]:
        """获取所有角色"""
        result = await self.db.execute(select(Role).order_by(Role.id))
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
    
    async def get_role_by_id(self, role_id: int) -> Role:
        """根据ID获取角色"""
        result = await self.db.execute(
            select(Role).where(Role.id == role_id)
        )
        role = result.scalar_one_or_none()
        
        if not role:
            raise NotFoundError("Role", role_id)
        
        return role
    
    async def create_role(self, code: str, name: str, description: str = None) -> Role:
        """创建角色"""
        # 检查编码是否存在
        existing = await self.db.execute(
            select(Role).where(Role.code == code)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Role code '{code}' already exists")
        
        role = Role(code=code, name=name, description=description)
        self.db.add(role)
        await self.db.flush()
        
        logger.info(f"Role created: {code}")
        return role
    
    async def update_role(self, role_id: int, name: str = None, description: str = None) -> Role:
        """更新角色"""
        role = await self.get_role_by_id(role_id)
        
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        
        await self.db.flush()
        logger.info(f"Role updated: {role.code}")
        return role
    
    async def delete_role(self, role_id: int) -> bool:
        """删除角色"""
        role = await self.get_role_by_id(role_id)
        
        # 检查是否有用户使用该角色
        user_count_result = await self.db.execute(
            select(func.count(UserRole.id)).where(UserRole.role_code == role.code)
        )
        user_count = user_count_result.scalar()
        
        if user_count > 0:
            raise ValidationError(f"角色 '{role.name}' 正在被 {user_count} 个用户使用，无法删除")
        
        await self.db.delete(role)
        await self.db.flush()
        
        logger.info(f"Role deleted: {role.code}")
        return True


class OrgService:
    """组织服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_orgs(self, type: str = None, parent_id: int = None, status: int = None) -> List[Org]:
        """获取组织列表"""
        conditions = []
        if type:
            conditions.append(Org.type == type)
        if parent_id is not None:
            conditions.append(Org.parent_id == parent_id)
        if status is not None:
            conditions.append(Org.status == status)
        
        stmt = select(Org).order_by(Org.id)
        if conditions:
            stmt = stmt.where(*conditions)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_org(self, org_id: int) -> Org:
        """获取组织"""
        result = await self.db.execute(
            select(Org).where(Org.id == org_id)
        )
        org = result.scalar_one_or_none()
        
        if not org:
            raise NotFoundError("Org", org_id)
        
        return org
    
    async def create_org(self, code: str, name: str, type: str, parent_id: int = 0) -> Org:
        """创建组织"""
        # 检查编码是否存在
        existing = await self.db.execute(
            select(Org).where(Org.code == code)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Org code '{code}' already exists")
        
        org = Org(code=code, name=name, type=type, parent_id=parent_id)
        self.db.add(org)
        await self.db.flush()
        
        logger.info(f"Org created: {code}")
        return org
    
    async def update_org(self, org_id: int, name: str = None, type: str = None, 
                         parent_id: int = None, status: int = None) -> Org:
        """更新组织"""
        org = await self.get_org(org_id)
        
        if name is not None:
            org.name = name
        if type is not None:
            org.type = type
        if parent_id is not None:
            org.parent_id = parent_id
        if status is not None:
            org.status = status
        
        await self.db.flush()
        logger.info(f"Org updated: {org.code}")
        return org
    
    async def delete_org(self, org_id: int) -> bool:
        """删除组织"""
        org = await self.get_org(org_id)
        
        # 检查是否有子组织
        children_result = await self.db.execute(
            select(func.count(Org.id)).where(Org.parent_id == org_id)
        )
        children_count = children_result.scalar()
        
        if children_count > 0:
            raise ValidationError(f"组织 '{org.name}' 存在 {children_count} 个子组织，无法删除")
        
        # 检查是否有用户
        user_count_result = await self.db.execute(
            select(func.count(User.id)).where(User.org_id == org_id)
        )
        user_count = user_count_result.scalar()
        
        if user_count > 0:
            raise ValidationError(f"组织 '{org.name}' 存在 {user_count} 个用户，无法删除")
        
        await self.db.delete(org)
        await self.db.flush()
        
        logger.info(f"Org deleted: {org.code}")
        return True


class AuditLogService:
    """操作日志服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log(self, user_id: int, username: str, action: str, 
                  resource_type: str, resource_id: str = None, 
                  detail: str = None, ip_address: str = None):
        """记录操作日志"""
        from .models import AuditLog
        
        log = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            ip_address=ip_address
        )
        self.db.add(log)
        await self.db.flush()
    
    async def list_logs(self, user_id: int = None, action: str = None,
                        resource_type: str = None, start_time = None,
                        end_time = None, page: int = 1, size: int = 20):
        """查询操作日志"""
        from .models import AuditLog
        from erp_common.schemas.base import PageResult
        from .schemas import AuditLogResponse
        
        conditions = []
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if action:
            conditions.append(AuditLog.action == action)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if start_time:
            conditions.append(AuditLog.created_at >= start_time)
        if end_time:
            conditions.append(AuditLog.created_at <= end_time)
        
        # 查询总数
        count_stmt = select(func.count(AuditLog.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar()
        
        # 查询数据
        offset = (page - 1) * size
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.offset(offset).limit(size)
        
        result = await self.db.execute(stmt)
        logs = result.scalars().all()
        
        return PageResult(
            items=[AuditLogResponse.model_validate(log) for log in logs],
            total=total,
            page=page,
            size=size
        )
