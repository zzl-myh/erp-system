"""
统一响应和分页模型
"""

from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    """
    统一响应结果类
    
    Usage:
        return Result.success(data=user)
        return Result.fail(message="User not found", code="NOT_FOUND")
    """
    
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: Optional[T] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "OK") -> "Result[T]":
        """成功响应"""
        return cls(success=True, code="SUCCESS", message=message, data=data)
    
    @classmethod
    def fail(
        cls, 
        message: str, 
        code: str = "ERROR", 
        data: Optional[T] = None
    ) -> "Result[T]":
        """失败响应"""
        return cls(success=False, code=code, message=message, data=data)


class PageQuery(BaseModel):
    """分页查询基类"""
    
    page: int = Field(default=1, ge=1, description="页码，从1开始")
    size: int = Field(default=20, ge=1, le=100, description="每页数量")
    
    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.size


class PageResult(BaseModel, Generic[T]):
    """分页结果"""
    
    items: List[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, ge=0, description="总记录数")
    page: int = Field(default=1, ge=1, description="当前页码")
    size: int = Field(default=20, ge=1, description="每页数量")
    
    @property
    def pages(self) -> int:
        """总页数"""
        if self.size <= 0:
            return 0
        return (self.total + self.size - 1) // self.size
    
    @property
    def has_next(self) -> bool:
        """是否有下一页"""
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        """是否有上一页"""
        return self.page > 1


class TimestampMixin(BaseModel):
    """时间戳混入类"""
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IdMixin(BaseModel):
    """ID 混入类"""
    
    id: Optional[int] = None
