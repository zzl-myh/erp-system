"""
统一异常定义
"""

from typing import Any, Dict, Optional


class BusinessError(Exception):
    """业务异常基类"""
    
    def __init__(
        self, 
        message: str, 
        code: str = "BUSINESS_ERROR",
        status_code: int = 400,
        data: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.data = data or {}
        super().__init__(self.message)


class NotFoundError(BusinessError):
    """资源不存在异常"""
    
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            code="NOT_FOUND",
            status_code=404,
            data={"resource": resource, "identifier": str(identifier)}
        )


class ValidationError(BusinessError):
    """数据校验异常"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            data={"field": field} if field else {}
        )


class AuthenticationError(BusinessError):
    """认证异常"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401
        )


class PermissionDeniedError(BusinessError):
    """权限不足异常"""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            status_code=403
        )


class ConflictError(BusinessError):
    """业务冲突异常"""
    
    def __init__(self, message: str, resource: Optional[str] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            data={"resource": resource} if resource else {}
        )


# ============ 业务特定异常 ============

class StockInsufficientError(BusinessError):
    """库存不足异常"""
    
    def __init__(self, sku_id: str, available: float, required: float):
        super().__init__(
            message=f"Insufficient stock for SKU {sku_id}: available={available}, required={required}",
            code="STOCK_INSUFFICIENT",
            status_code=400,
            data={
                "sku_id": sku_id,
                "available": available,
                "required": required
            }
        )


class OrderAlreadyPaidError(BusinessError):
    """订单已支付异常"""
    
    def __init__(self, order_id: str):
        super().__init__(
            message=f"Order {order_id} has already been paid",
            code="ORDER_ALREADY_PAID",
            status_code=409,
            data={"order_id": order_id}
        )


class PromoExpiredError(BusinessError):
    """促销已过期异常"""
    
    def __init__(self, promo_id: int):
        super().__init__(
            message=f"Promotion {promo_id} has expired",
            code="PROMO_EXPIRED",
            status_code=400,
            data={"promo_id": promo_id}
        )


class MemberNotFoundError(NotFoundError):
    """会员不存在异常"""
    
    def __init__(self, member_id: int):
        super().__init__(resource="Member", identifier=member_id)


class PointInsufficientError(BusinessError):
    """积分不足异常"""
    
    def __init__(self, available: int, required: int):
        super().__init__(
            message=f"Insufficient points: available={available}, required={required}",
            code="POINT_INSUFFICIENT",
            status_code=400,
            data={"available": available, "required": required}
        )


class PoAlreadyStockedInError(BusinessError):
    """采购订单已入库异常"""
    
    def __init__(self, po_id: int):
        super().__init__(
            message=f"Purchase order {po_id} has already been stocked in",
            code="PO_ALREADY_STOCKED_IN",
            status_code=409,
            data={"po_id": po_id}
        )

# 别名，兼容旧代码
BusinessException = BusinessError


# ============ 异常处理器 ============

async def business_exception_handler(request, exc: BusinessError):
    """
    FastAPI 业务异常处理器
    用于统一返回业务异常响应
    """
    from fastapi.responses import JSONResponse
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "code": exc.code,
            "message": exc.message,
            "data": exc.data
        }
    )
