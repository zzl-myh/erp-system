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
    PasswordReset,
    RoleAssignRequest,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    TokenVerifyResponse,
    UserCreate,
    UserQuery,
    UserResponse,
    UserRoleResponse,
    UserUpdate,
    OrgCreate,
    OrgUpdate,
    OrgResponse,
    AuditLogResponse,
    AuditLogQuery,
    PermissionResponse,
    RolePermissionAssign,
)
from .service import AuthService, RoleService, UserService, OrgService, AuditLogService, PermissionService

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


def get_org_service(
    db: AsyncSession = Depends(get_db),
) -> OrgService:
    """获取组织服务实例"""
    return OrgService(db)


def get_audit_log_service(
    db: AsyncSession = Depends(get_db),
) -> AuditLogService:
    """获取操作日志服务实例"""
    return AuditLogService(db)


def get_permission_service(
    db: AsyncSession = Depends(get_db),
) -> PermissionService:
    """获取权限服务实例"""
    return PermissionService(db)


async def enrich_user_roles(user, db: AsyncSession) -> UserResponse:
    """丰富用户角色信息"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from .models import Role, UserRole
    
    # 直接查询用户的角色（避免懒加载问题）
    user_roles_result = await db.execute(
        select(UserRole).where(UserRole.user_id == user.id)
    )
    user_roles = user_roles_result.scalars().all()
    role_codes = [r.role_code for r in user_roles]
    
    # 查询角色详情
    roles_data = []
    if role_codes:
        result = await db.execute(
            select(Role).where(Role.code.in_(role_codes))
        )
        roles = result.scalars().all()
        roles_data = [
            UserRoleResponse(
                id=role.id,
                code=role.code,
                name=role.name,
                description=role.description
            )
            for role in roles
        ]
    
    return UserResponse(
        id=user.id,
        username=user.username,
        name=user.name,
        mobile=user.mobile,
        email=user.email,
        org_id=user.org_id,
        status=user.status,
        created_at=user.created_at,
        roles=roles_data
    )


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
    # 注意：HTTP 头只支持 ASCII，中文需要 URL 编码
    from urllib.parse import quote
    response.headers["X-User-Id"] = str(token_data.user_id)
    response.headers["X-Username"] = quote(token_data.username, safe='')
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
    db: AsyncSession = Depends(get_db),
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
    response = await enrich_user_roles(new_user, db)
    return Result.ok(data=response)


@router.get("/me", response_model=Result[UserResponse], summary="获取当前用户信息")
async def get_current_user_info(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """获取当前登录用户的详细信息"""
    user_info = await service.get_user(user.user_id)
    response = await enrich_user_roles(user_info, db)
    return Result.ok(data=response)


@router.get("/list", response_model=Result[PageResult[UserResponse]], summary="用户列表")
async def list_users(
    keyword: str = Query(None, description="关键词搜索"),
    org_id: int = Query(None, description="组织ID"),
    status: int = Query(None, ge=0, le=1, description="状态"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(get_current_user),
):
    """分页查询用户列表"""
    from sqlalchemy import select
    from .models import Role
    
    query = UserQuery(
        keyword=keyword,
        org_id=org_id,
        status=status,
        page=page,
        size=size,
    )
    result = await service.list_users(query)
    
    # 获取所有角色信息
    role_result = await db.execute(select(Role))
    all_roles = {r.code: r for r in role_result.scalars().all()}
    
    # 丰富角色信息
    enriched_items = []
    for item in result.items:
        roles_data = []
        for role_ref in item.roles:
            role = all_roles.get(role_ref.role_code if hasattr(role_ref, 'role_code') else role_ref.code)
            if role:
                roles_data.append(UserRoleResponse(
                    id=role.id,
                    code=role.code,
                    name=role.name,
                    description=role.description
                ))
        enriched_items.append(UserResponse(
            id=item.id,
            username=item.username,
            name=item.name,
            mobile=item.mobile,
            email=item.email,
            org_id=item.org_id,
            status=item.status,
            created_at=item.created_at,
            roles=roles_data
        ))
    
    result.items = enriched_items
    return Result.ok(data=result)


@router.post("/role/assign", response_model=Result[UserResponse], summary="分配角色")
async def assign_roles(
    request: RoleAssignRequest,
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """
    为用户分配角色（需要管理员权限）
    
    会替换用户现有的所有角色
    """
    updated_user = await service.assign_roles(request)
    response = await enrich_user_roles(updated_user, db)
    return Result.ok(data=response)


@router.post("/password/change", response_model=Result, summary="修改密码")
async def change_password(
    data: PasswordChange,
    user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """修改当前用户的密码"""
    await service.change_password(user.user_id, data.old_password, data.new_password)
    return Result.ok(message="Password changed successfully")


@router.post("/password/reset", response_model=Result, summary="重置密码")
async def reset_password(
    data: PasswordReset,
    service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """管理员重置用户密码"""
    await service.reset_password(data.user_id, data.new_password)
    return Result.ok(message="Password reset successfully")


# ==================== 角色接口 ====================

@router.get("/role/list", response_model=Result[list[RoleResponse]], summary="角色列表")
async def list_roles(
    service: RoleService = Depends(get_role_service),
    user: CurrentUser = Depends(get_current_user),
):
    """获取所有角色列表"""
    roles = await service.list_roles()
    return Result.ok(data=[RoleResponse.model_validate(r) for r in roles])


@router.post("/role/create", response_model=Result[RoleResponse], summary="创建角色")
async def create_role(
    data: RoleCreate,
    service: RoleService = Depends(get_role_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """创建角色（管理员权限）"""
    role = await service.create_role(data.code, data.name, data.description)
    return Result.ok(data=RoleResponse.model_validate(role))


@router.put("/role/{role_id}", response_model=Result[RoleResponse], summary="更新角色")
async def update_role(
    role_id: int,
    data: RoleUpdate,
    service: RoleService = Depends(get_role_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """更新角色（管理员权限）"""
    role = await service.update_role(role_id, data.name, data.description)
    return Result.ok(data=RoleResponse.model_validate(role))


@router.delete("/role/{role_id}", response_model=Result, summary="删除角色")
async def delete_role(
    role_id: int,
    service: RoleService = Depends(get_role_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """删除角色（管理员权限）"""
    await service.delete_role(role_id)
    return Result.ok(message="Role deleted successfully")


# ==================== 组织接口 ====================

@router.get("/org/list", response_model=Result[list[OrgResponse]], summary="组织列表")
async def list_orgs(
    type: str = Query(None, description="组织类型"),
    parent_id: int = Query(None, description="父级ID"),
    status: int = Query(None, ge=0, le=1, description="状态"),
    service: OrgService = Depends(get_org_service),
    user: CurrentUser = Depends(get_current_user),
):
    """获取组织列表"""
    orgs = await service.list_orgs(type=type, parent_id=parent_id, status=status)
    return Result.ok(data=[OrgResponse.model_validate(o) for o in orgs])


@router.get("/org/{org_id}", response_model=Result[OrgResponse], summary="组织详情")
async def get_org(
    org_id: int,
    service: OrgService = Depends(get_org_service),
    user: CurrentUser = Depends(get_current_user),
):
    """获取组织详情"""
    org = await service.get_org(org_id)
    return Result.ok(data=OrgResponse.model_validate(org))


@router.post("/org/create", response_model=Result[OrgResponse], summary="创建组织")
async def create_org(
    data: OrgCreate,
    service: OrgService = Depends(get_org_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """创建组织（管理员权限）"""
    org = await service.create_org(data.code, data.name, data.type, data.parent_id)
    return Result.ok(data=OrgResponse.model_validate(org))


@router.put("/org/{org_id}", response_model=Result[OrgResponse], summary="更新组织")
async def update_org(
    org_id: int,
    data: OrgUpdate,
    service: OrgService = Depends(get_org_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """更新组织（管理员权限）"""
    org = await service.update_org(org_id, data.name, data.type, data.parent_id, data.status)
    return Result.ok(data=OrgResponse.model_validate(org))


@router.delete("/org/{org_id}", response_model=Result, summary="删除组织")
async def delete_org(
    org_id: int,
    service: OrgService = Depends(get_org_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """删除组织（管理员权限）"""
    await service.delete_org(org_id)
    return Result.ok(message="Org deleted successfully")


# ==================== 操作日志接口 ====================

@router.get("/audit/list", response_model=Result[PageResult[AuditLogResponse]], summary="操作日志列表")
async def list_audit_logs(
    user_id: int = Query(None, description="用户ID"),
    action: str = Query(None, description="操作类型"),
    resource_type: str = Query(None, description="资源类型"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: AuditLogService = Depends(get_audit_log_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """查询操作日志（管理员权限）"""
    result = await service.list_logs(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        page=page,
        size=size
    )
    return Result.ok(data=result)


# ==================== 权限接口 ====================

@router.get("/permission/list", response_model=Result[list[PermissionResponse]], summary="权限列表")
async def list_permissions(
    service: PermissionService = Depends(get_permission_service),
    user: CurrentUser = Depends(get_current_user),
):
    """获取所有权限点"""
    permissions = await service.list_permissions()
    return Result.ok(data=[PermissionResponse.model_validate(p) for p in permissions])


@router.get("/permission/role/{role_id}", response_model=Result[list[str]], summary="角色权限")
async def get_role_permissions(
    role_id: int,
    service: PermissionService = Depends(get_permission_service),
    user: CurrentUser = Depends(get_current_user),
):
    """获取角色的权限点编码列表"""
    permissions = await service.get_role_permissions(role_id)
    return Result.ok(data=[p.code for p in permissions])


@router.post("/permission/assign", response_model=Result, summary="分配角色权限")
async def assign_role_permissions(
    data: RolePermissionAssign,
    service: PermissionService = Depends(get_permission_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """为角色分配权限（管理员权限）"""
    await service.assign_role_permissions(data.role_id, data.permission_codes)
    return Result.ok(message="Permissions assigned successfully")


@router.get("/permission/me", response_model=Result[list[str]], summary="我的权限")
async def get_my_permissions(
    service: PermissionService = Depends(get_permission_service),
    user: CurrentUser = Depends(get_current_user),
):
    """获取当前用户的权限点"""
    # ADMIN 拥有所有权限
    if "ADMIN" in user.roles:
        permissions = await service.list_permissions()
        return Result.ok(data=[p.code for p in permissions])
    
    permissions = await service.get_user_permissions(user.user_id)
    return Result.ok(data=list(permissions))


# ==================== 用户路径参数接口（必须放在最后） ====================

@router.get("/{user_id}", response_model=Result[UserResponse], summary="获取用户详情")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(get_current_user),
):
    """根据ID获取用户详情"""
    user_info = await service.get_user(user_id)
    response = await enrich_user_roles(user_info, db)
    return Result.ok(data=response)


@router.put("/{user_id}", response_model=Result[UserResponse], summary="更新用户")
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """更新用户信息（需要管理员权限）"""
    updated_user = await service.update_user(user_id, data, operator=user.username)
    response = await enrich_user_roles(updated_user, db)
    return Result.ok(data=response)


@router.delete("/{user_id}", response_model=Result, summary="删除用户")
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(require_roles("ADMIN")),
):
    """删除用户（管理员权限）"""
    await service.delete_user(user_id)
    return Result.ok(message="User deleted successfully")
