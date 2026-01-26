"""
商品中心 - FastAPI 应用入口
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from erp_common.config import settings
from erp_common.database import close_db, init_db
from erp_common.exceptions import BusinessError
from erp_common.schemas.base import Result
from erp_common.utils.kafka_utils import KafkaProducer
from erp_common.utils.redis_utils import close_redis, get_redis

from .api import kafka_producer, router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting Item Service...")
    
    # 初始化数据库
    await init_db()
    logger.info("Database initialized")
    
    # 初始化 Redis
    redis = await get_redis()
    logger.info("Redis connected")
    
    # 初始化 Kafka 生产者
    global kafka_producer
    from . import api
    api.kafka_producer = KafkaProducer()
    try:
        await api.kafka_producer.start()
        logger.info("Kafka producer started")
    except Exception as e:
        logger.warning(f"Kafka producer failed to start: {e}")
    
    yield
    
    # 关闭时
    logger.info("Shutting down Item Service...")
    
    if api.kafka_producer:
        await api.kafka_producer.stop()
    
    await close_redis()
    await close_db()
    
    logger.info("Item Service stopped")


# 创建 FastAPI 应用
app = FastAPI(
    title="商品中心",
    description="ERP 系统 - 商品中心微服务",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/item/docs",
    openapi_url="/item/openapi.json",
)


# 注册路由
app.include_router(router)


# ==================== 异常处理 ====================

@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    """业务异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content=Result.fail(
            message=exc.message,
            code=exc.code,
            data=exc.data,
        ).model_dump(mode='json'),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
        })
    
    return JSONResponse(
        status_code=400,
        content=Result.fail(
            message="Validation error",
            code="VALIDATION_ERROR",
            data={"errors": errors},
        ).model_dump(mode='json'),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.exception(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content=Result.fail(
            message="Internal server error",
            code="INTERNAL_ERROR",
        ).model_dump(mode='json'),
    )


# 用于直接运行
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "services.item_service.main:app",
        host="0.0.0.0",
        port=settings.item_service_port,
        reload=True,
    )
