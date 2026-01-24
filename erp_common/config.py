"""
应用配置管理
使用 pydantic-settings 从环境变量加载配置
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # 应用配置
    app_name: str = "ERP System"
    debug: bool = False
    
    # 数据库配置
    database_url: str = "mysql+aiomysql://root:password@localhost:3306/erp"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis 配置
    redis_url: str = "redis://localhost:6379/0"
    
    # Kafka 配置
    kafka_bootstrap_servers: str = "localhost:9092"
    
    # JWT 配置
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    
    # 服务端口配置
    item_service_port: int = 8001
    user_service_port: int = 8002
    stock_service_port: int = 8003
    purchase_service_port: int = 8004
    production_service_port: int = 8005
    job_service_port: int = 8006
    cost_service_port: int = 8007
    order_service_port: int = 8008
    member_service_port: int = 8009
    promo_service_port: int = 8010


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
