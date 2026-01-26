"""
用户中心 - API 路由
"""

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.auth import CurrentUser, get_current_user, require_roles
from erp_common.database import get_db
from erp_common.schemas.base import PageResult, Result
from erp_common.utils.jwt_utils import decode_token
from erp_common.utils.redis_utils import RedisClient, get_redis

from .schemas import (
    LoginRequest,
    LoginResponse,
    PasswordChange,
    RoleAssignRequest,
    RoleResponse,
    TokenVerifyResponse,
    UserCreate,
    UserQuery,
    UserResponse,
    UserUpdate,
)
from .service import AuthService, RoleService, UserService

router = APIRouter(prefix="/user", tags=["用户中心"])


# ==================== 健康检查（必须放在最前面） ====================

@router.get("/health", summary="健康检查")
async def health_check():
    """服务健康检查"""
    return {"status": "healthy", "service": "user-service"}


@router.get("/ready", summary="就绪检查")
async def readiness_check():
    """服务就绪检查"""
    return {"status": "ready", "service": "user-service"}


def get_auth_service(
    db: AsyncSession = Depends(get_db),
) -> AuthService:
    """获取认证服务实例"""
    return AuthService(db, redis=None)


def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    """获取用户服务实例"""
    return UserService(db, kafka=None)


def get_role_service(
    db: AsyncSession = Depends(get_db),
) -> RoleService:
    """获取角色服务实例"""
    return RoleService(db)


# ==================== 认证接口 ====================

@router.post("/login", response_model=Result[LoginResponse], summary="用户登录")
async def login(
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    """
    用户登录，返回 JWT Token
    
    - **username**: 用户名
    - **password**: 密码
    """
    result = await service.login(data)
    return Result.ok(data=result)


@router.post("/logout", response_model=Result, summary="用户注销")
async def logout(
    user: CurrentUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """用户注销，使 Token 失效"""
    await service.logout(user.user_id)
    return Result.ok(message="Logged out successfully")


@router.get("/verify", summary="验证 Token（供 Nginx auth_request 使用）")
async def verify_token(
    response: Response,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    验证 Token 有效性
    
    Nginx auth_request 调用此接口验证用户身份
    成功时返回 200 并在响应头中设置用户信息
    """
    if not authorization:
        response.status_code = 401
        return {"error": "No authorization header"}
    
    # 提取 Token
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        response.status_code = 401
        return {"error": "Invalid token format"}
    
    # 解析 Token
    token_data = decode_token(token)
    if not token_data:
        response.status_code = 401
        return {"error": "Invalid or expired token"}
    
    # 设置响应头（供 Nginx 转发给后端服务）
    response.headers["X-User-Id"] = str(token_data.user_id)
    response.headers["X-Username"] = token_data.username
    response.headers["X-User-Roles"] = ",".join(token_data.roles)
    
    return TokenVerifyResponse(
        user_id=token_data.user_id,
        username=token_data.username,
        roles=token_data.roles,
    )


# ==================== 用户接口 ====================

@router.post("/create", response_model=Result[UserResponse], summary="创建用户")
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """
    创建用户（需要管理员权限）
    
    - **username**: 用户名（3-50字符）
    - **password**: 密码（至少6位）
    - **roles**: 角色编码列表
    """
    new_user = await service.create_user(data, operator=user.username)
    return Result.ok(data=UserResponse.model_validate(new_user))


@router.get("/me", response_model=Result[UserResponse], summary="获取当前用户信息")
async def get_current_user_info(
    user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """获取当前登录用户的详细信息"""
    user_info = await service.get_user(user.user_id)
    return Result.ok(data=UserResponse.model_validate(user_info))


@router.get("/{user_id}", response_model=Result[UserResponse], summary="获取用户详情")
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(get_current_user),
):
    """根据ID获取用户详情"""
    user_info = await service.get_user(user_id)
    return Result.ok(data=UserResponse.model_validate(user_info))


@router.put("/{user_id}", response_model=Result[UserResponse], summary="更新用户")
async def update_user(
    user_id: int,
    data: UserUpdate,
    service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """更新用户信息（需要管理员权限）"""
    updated_user = await service.update_user(user_id, data, operator=user.username)
    return Result.ok(data=UserResponse.model_validate(updated_user))


@router.get("/list", response_model=Result[PageResult[UserResponse]], summary="用户列表")
async def list_users(
    keyword: str = Query(None, description="关键词搜索"),
    org_id: int = Query(None, description="组织ID"),
    status: int = Query(None, ge=0, le=1, description="状态"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(get_current_user),
):
    """分页查询用户列表"""
    query = UserQuery(
        keyword=keyword,
        org_id=org_id,
        status=status,
        page=page,
        size=size,
    )
    result = await service.list_users(query)
    return Result.ok(data=result)


@router.post("/role/assign", response_model=Result[UserResponse], summary="分配角色")
async def assign_roles(
    request: RoleAssignRequest,
    service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """
    为用户分配角色（需要管理员权限）
    
    会替换用户现有的所有角色
    """
    updated_user = await service.assign_roles(request)
    return Result.ok(data=UserResponse.model_validate(updated_user))


@router.post("/password/change", response_model=Result, summary="修改密码")
async def change_password(
    data: PasswordChange,
    user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """修改当前用户的密码"""
    await service.change_password(user.user_id, data.old_password, data.new_password)
    return Result.ok(message="Password changed successfully")


# ==================== 角色接口 ====================

@router.get("/role/list", response_model=Result[list[RoleResponse]], summary="角色列表")
async def list_roles(
    service: RoleService = Depends(get_role_service),
    user: CurrentUser = Depends(get_current_user),
):
    """获取所有角色列表"""
    roles = await service.list_roles()
    return Result.ok(data=[RoleResponse.model_validate(r) for r in roles])
