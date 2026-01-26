"""
Redis 缓存工具
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from erp_common.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis 异步客户端封装
    
    Usage:
        client = RedisClient()
        await client.connect()
        await client.set("key", "value", expire=3600)
        value = await client.get("key")
        await client.close()
    """
    
    def __init__(self, url: Optional[str] = None):
        self.url = url or settings.redis_url
        self._client: Optional[redis.Redis] = None
    
    async def connect(self):
        """连接 Redis"""
        self._client = redis.from_url(
            self.url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info(f"Redis connected: {self.url}")
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[str]:
        """获取字符串值"""
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return await self._client.get(key)
    
    async def set(
        self, 
        key: str, 
        value: str, 
        expire: Optional[int] = None
    ) -> bool:
        """设置字符串值"""
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return await self._client.set(key, value, ex=expire)
    
    async def delete(self, key: str) -> int:
        """删除键"""
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return await self._client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return await self._client.exists(key) > 0
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """自增"""
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return await self._client.incrby(key, amount)
    
    async def get_json(self, key: str) -> Optional[Any]:
        """获取 JSON 值"""
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set_json(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """设置 JSON 值"""
        return await self.set(key, json.dumps(value, default=str), expire)
    
    # ========== 分布式锁 ==========
    
    async def acquire_lock(
        self, 
        lock_name: str, 
        timeout: int = 10
    ) -> Optional[str]:
        """
        获取分布式锁
        
        Args:
            lock_name: 锁名称
            timeout: 锁超时时间（秒）
        
        Returns:
            锁标识符（用于释放锁），获取失败返回 None
        """
        import uuid
        lock_key = f"lock:{lock_name}"
        lock_value = str(uuid.uuid4())
        
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        
        acquired = await self._client.set(
            lock_key, 
            lock_value, 
            nx=True, 
            ex=timeout
        )
        
        if acquired:
            logger.debug(f"Lock acquired: {lock_name}")
            return lock_value
        return None
    
    async def release_lock(self, lock_name: str, lock_value: str) -> bool:
        """
        释放分布式锁
        
        Args:
            lock_name: 锁名称
            lock_value: 获取锁时返回的标识符
        
        Returns:
            是否成功释放
        """
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        
        lock_key = f"lock:{lock_name}"
        
        # 使用 Lua 脚本保证原子性
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        result = await self._client.eval(script, 1, lock_key, lock_value)
        
        if result:
            logger.debug(f"Lock released: {lock_name}")
            return True
        return False
    
    # ========== 号段生成器 ==========
    
    async def get_next_id(self, key: str, step: int = 1) -> int:
        """
        获取下一个ID（用于分布式ID生成）
        
        Args:
            key: 序列键名
            step: 步长
        
        Returns:
            下一个ID
        """
        return await self.incr(key, step)


# 全局 Redis 客户端实例
_redis_client: Optional[RedisClient] = None


async def init_redis() -> None:
    """
    初始化全局 Redis 连接
    应在应用启动时调用
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
        logger.info("Global Redis client initialized")


async def close_redis() -> None:
    """
    关闭全局 Redis 连接
    应在应用关闭时调用
    """
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Global Redis client closed")


async def get_redis() -> RedisClient:
    """
    获取全局 Redis 客户端实例
    如果未初始化会自动初始化
    """
    global _redis_client
    if _redis_client is None:
        await init_redis()
    return _redis_client


def get_redis_client() -> RedisClient:
    """
    获取全局 Redis 客户端实例（同步版本）
    
    Returns:
        RedisClient: 全局客户端实例
    
    Raises:
        RuntimeError: 如果客户端未初始化
    """
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return _redis_client
