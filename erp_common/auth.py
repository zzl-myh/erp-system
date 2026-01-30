"""
FastAPI 认证依赖
"""

from typing import Callable, List, Optional, Set

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from erp_common.exceptions import AuthenticationError, PermissionDeniedError
from erp_common.utils.jwt_utils import decode_token

# HTTP Bearer 认证
security = HTTPBearer(auto_error=False)

# 权限缓存（用户ID -> 权限编码集合）
_permission_cache: dict[int, Set[str]] = {}


class CurrentUser(BaseModel):
    """当前用户信息"""
    user_id: int
    username: str
    roles: List[str] = []
    permissions: List[str] = []  # 权限点列表


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> CurrentUser:
    """
    从请求中获取当前用户信息
    
    优先从 Nginx 注入的请求头获取，否则从 JWT Token 解析
    
    Usage:
        @app.get("/protected")
        async def protected(user: CurrentUser = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    # 1. 尝试从 Nginx 注入的请求头获取
    user_id = request.headers.get("X-User-Id")
    username = request.headers.get("X-Username")
    user_roles = request.headers.get("X-User-Roles", "")
    
    if user_id and username:
        return CurrentUser(
            user_id=int(user_id),
            username=username,
            roles=user_roles.split(",") if user_roles else []
        )
    
    # 2. 从 JWT Token 解析
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = decode_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return CurrentUser(
        user_id=token_data.user_id,
        username=token_data.username,
        roles=token_data.roles
    )


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[CurrentUser]:
    """
    可选的用户认证
    
    如果没有提供认证信息，返回 None 而不是抛出异常
    """
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None


def require_roles(*required_roles: str):
    """
    角色权限校验装饰器
    
    Usage:
        @app.get("/admin")
        async def admin_only(
            user: CurrentUser = Depends(require_roles("ADMIN"))
        ):
            return {"message": "Admin access granted"}
    """
    async def role_checker(
        user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        # ADMIN 拥有所有权限
        if "ADMIN" in user.roles:
            return user
        
        # 检查是否有所需角色
        if not any(role in user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required roles: {required_roles}"
            )
        return user
    
    return role_checker


def require_any_role(*roles: str):
    """要求拥有任意一个角色"""
    return require_roles(*roles)


def require_all_roles(*roles: str):
    """要求拥有所有角色"""
    async def role_checker(
        user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        if "ADMIN" in user.roles:
            return user
        
        if not all(role in user.roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required all roles: {roles}"
            )
        return user
    
    return role_checker


# ==================== 权限点控制 ====================

def set_permission_loader(loader: Callable[[int], Set[str]]):
    """
    设置权限加载器
    
    由 user_service 在启动时调用，注册权限加载函数
    
    Args:
        loader: 根据用户ID返回权限编码集合的函数
    """
    global _permission_loader
    _permission_loader = loader


_permission_loader: Optional[Callable[[int], Set[str]]] = None


def get_user_permissions(user_id: int) -> Set[str]:
    """
    获取用户权限点（带缓存）
    
    Args:
        user_id: 用户ID
    
    Returns:
        权限编码集合
    """
    if user_id in _permission_cache:
        return _permission_cache[user_id]
    
    if _permission_loader:
        permissions = _permission_loader(user_id)
        _permission_cache[user_id] = permissions
        return permissions
    
    return set()


def clear_permission_cache(user_id: Optional[int] = None):
    """
    清除权限缓存
    
    Args:
        user_id: 指定用户ID，不传则清除全部
    """
    if user_id:
        _permission_cache.pop(user_id, None)
    else:
        _permission_cache.clear()


def require_permissions(*required_permissions: str):
    """
    权限点校验装饰器
    
    要求用户拥有指定的权限点（任一即可）
    
    Usage:
        @app.delete("/user/{id}")
        async def delete_user(
            user: CurrentUser = Depends(require_permissions("user:delete"))
        ):
            pass
    """
    async def permission_checker(
        user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        # ADMIN 拥有所有权限
        if "ADMIN" in user.roles:
            return user
        
        # 获取用户权限
        user_permissions = get_user_permissions(user.user_id)
        
        # 检查是否拥有任一所需权限
        if not any(perm in user_permissions for perm in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permissions: {required_permissions}"
            )
        
        return user
    
    return permission_checker


def require_all_permissions(*required_permissions: str):
    """
    要求拥有所有指定权限点
    """
    async def permission_checker(
        user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        if "ADMIN" in user.roles:
            return user
        
        user_permissions = get_user_permissions(user.user_id)
        
        if not all(perm in user_permissions for perm in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required all permissions: {required_permissions}"
            )
        
        return user
    
    return permission_checker
