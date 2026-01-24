"""会员中心 - FastAPI 应用入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from erp_common.config import settings
from erp_common.database import init_db, close_db
from erp_common.exceptions import BusinessException, business_exception_handler
from erp_common.utils.kafka_utils import init_kafka, close_kafka
from erp_common.utils.redis_utils import init_redis, close_redis

from .api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    await init_db()
    await init_redis()
    await init_kafka()
    print("Member service started successfully")
    
    yield
    
    # 关闭时清理
    await close_kafka()
    await close_redis()
    await close_db()
    print("Member service shutdown completed")


# 创建 FastAPI 应用
app = FastAPI(
    title="会员中心",
    description="ERP 系统 - 会员中心微服务（会员、积分、优惠券管理）",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/member/docs",
    openapi_url="/member/openapi.json",
)

# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "code": "INTERNAL_ERROR",
            "message": str(exc),
            "data": None
        }
    )


# 注册路由
app.include_router(router)


# 健康检查端点
@app.get("/member/health", tags=["健康检查"])
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "member_service"}


@app.get("/member/ready", tags=["健康检查"])
async def readiness_check():
    """就绪检查"""
    # TODO: 检查数据库、Redis、Kafka 连接
    return {"status": "ready", "service": "member_service"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "services.member_service.main:app",
        host="0.0.0.0",
        port=8008,
        reload=True
    )
