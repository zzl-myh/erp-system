"""
用户中心 - Pydantic Schema
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, EmailStr

from erp_common.schemas.base import PageQuery


# ========== 登录相关 ==========

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserBrief"


class TokenVerifyResponse(BaseModel):
    """Token 验证响应（用于 Nginx auth_request）"""
    user_id: int
    username: str
    roles: List[str]


# ========== 用户相关 ==========

class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    name: Optional[str] = Field(None, max_length=50, description="姓名")
    mobile: Optional[str] = Field(None, max_length=20, description="手机号")
    email: Optional[str] = Field(None, description="邮箱")
    org_id: Optional[int] = Field(None, description="所属组织ID")
    roles: List[str] = Field(default_factory=list, description="角色编码列表")


class UserUpdate(BaseModel):
    """更新用户请求"""
    name: Optional[str] = Field(None, max_length=50)
    mobile: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = None
    org_id: Optional[int] = None
    status: Optional[int] = Field(None, ge=0, le=1)


class PasswordChange(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=100)


class UserRoleResponse(BaseModel):
    """用户角色响应"""
    id: int
    role_code: str
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    org_id: Optional[int] = None
    status: int
    created_at: datetime
    roles: List[UserRoleResponse] = []
    
    class Config:
        from_attributes = True


class UserBrief(BaseModel):
    """用户简要信息"""
    id: int
    username: str
    name: Optional[str] = None
    roles: List[str] = []
    
    class Config:
        from_attributes = True


class UserQuery(PageQuery):
    """用户查询条件"""
    keyword: Optional[str] = Field(None, description="关键词搜索")
    org_id: Optional[int] = Field(None, description="组织ID")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")
    role: Optional[str] = Field(None, description="角色编码")


# ========== 角色相关 ==========

class RoleAssignRequest(BaseModel):
    """角色分配请求"""
    user_id: int
    roles: List[str] = Field(..., description="角色编码列表")


class RoleCreate(BaseModel):
    """创建角色请求"""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class RoleResponse(BaseModel):
    """角色响应"""
    id: int
    code: str
    name: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


# ========== 组织相关 ==========

class OrgCreate(BaseModel):
    """创建组织请求"""
    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., description="类型: STORE/WAREHOUSE/SUPPLIER/DEPT")
    parent_id: int = 0


class OrgResponse(BaseModel):
    """组织响应"""
    id: int
    code: str
    name: str
    type: str
    parent_id: int
    status: int
    
    class Config:
        from_attributes = True


# 解决循环引用
LoginResponse.model_rebuild()
