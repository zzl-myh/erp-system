"""
JWT 认证工具
"""

from datetime import datetime, timedelta
from typing import List, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from erp_common.config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Token 数据"""
    user_id: int
    username: str
    roles: List[str] = []
    exp: Optional[datetime] = None


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(
    user_id: int,
    username: str,
    roles: List[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建访问令牌
    
    Args:
        user_id: 用户ID
        username: 用户名
        roles: 角色列表
        expires_delta: 过期时间增量
    
    Returns:
        JWT token 字符串
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    
    to_encode = {
        "user_id": user_id,
        "username": username,
        "roles": roles or [],
        "exp": expire,
    }
    
    return jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> Optional[TokenData]:
    """
    解码令牌
    
    Args:
        token: JWT token 字符串
    
    Returns:
        TokenData 或 None（如果无效）
    """
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        return TokenData(**payload)
    except JWTError:
        return None


def is_token_expired(token: str) -> bool:
    """检查令牌是否过期"""
    token_data = decode_token(token)
    if token_data is None:
        return True
    if token_data.exp is None:
        return True
    return datetime.utcnow() > token_data.exp
