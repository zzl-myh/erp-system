"""
Kafka 消息工具
异步生产者和消费者封装
"""

import json
import logging
from typing import Any, Awaitable, Callable, Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from erp_common.config import settings
from erp_common.schemas.events import DomainEvent

logger = logging.getLogger(__name__)


class KafkaProducer:
    """
    Kafka 异步生产者
    
    Usage:
        producer = KafkaProducer()
        await producer.start()
        await producer.send("topic", event)
        await producer.stop()
    """
    
    def __init__(self, bootstrap_servers: Optional[str] = None):
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self._producer: Optional[AIOKafkaProducer] = None
    
    async def start(self):
        """启动生产者"""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await self._producer.start()
        logger.info(f"Kafka producer started: {self.bootstrap_servers}")
    
    async def stop(self):
        """停止生产者"""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")
    
    async def send(self, topic: str, event: DomainEvent) -> None:
        """
        发送事件消息
        
        Args:
            topic: Kafka topic
            event: 领域事件对象
        """
        if not self._producer:
            raise RuntimeError("Producer not started. Call start() first.")
        
        await self._producer.send_and_wait(topic, value=event.model_dump())
        logger.debug(f"Event sent to {topic}: {event.event_type}")
    
    async def send_raw(self, topic: str, key: Optional[str], value: dict) -> None:
        """
        发送原始消息
        
        Args:
            topic: Kafka topic
            key: 消息键
            value: 消息值
        """
        if not self._producer:
            raise RuntimeError("Producer not started. Call start() first.")
        
        key_bytes = key.encode("utf-8") if key else None
        await self._producer.send_and_wait(topic, key=key_bytes, value=value)


class KafkaConsumer:
    """
    Kafka 异步消费者
    
    Usage:
        async def handler(msg: dict):
            print(msg)
        
        consumer = KafkaConsumer("topic", "group-id", handler)
        await consumer.start()
        # ... 运行一段时间
        await consumer.stop()
    """
    
    def __init__(
        self,
        topic: str,
        group_id: str,
        handler: Callable[[dict], Awaitable[None]],
        bootstrap_servers: Optional[str] = None,
    ):
        self.topic = topic
        self.group_id = group_id
        self.handler = handler
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
    
    async def start(self):
        """启动消费者"""
        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
        )
        await self._consumer.start()
        self._running = True
        logger.info(f"Kafka consumer started: topic={self.topic}, group={self.group_id}")
        
        # 开始消费消息
        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                try:
                    await self.handler(msg.value)
                    logger.debug(f"Message processed from {self.topic}")
                except Exception as e:
                    logger.error(f"Error processing message from {self.topic}: {e}")
                    # TODO: 发送到死信队列
        finally:
            await self._consumer.stop()
    
    async def stop(self):
        """停止消费者"""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            logger.info(f"Kafka consumer stopped: topic={self.topic}")


# Kafka Topics 定义
class KafkaTopics:
    """Kafka Topic 常量"""
    
    # 商品中心
    ITEM_EVENTS = "item-events"
    
    # 用户中心
    USER_EVENTS = "user-events"
    
    # 采购中心
    PURCHASE_EVENTS = "purchase-events"
    
    # 生产中心
    PRODUCTION_EVENTS = "production-events"
    
    # 报工中心
    JOB_EVENTS = "job-events"
    
    # 库存中心
    STOCK_EVENTS = "stock-events"
    
    # 成本中心
    COST_EVENTS = "cost-events"
    
    # 订单中心
    ORDER_EVENTS = "order-events"
    
    # 会员中心
    MEMBER_EVENTS = "member-events"
    
    # 促销中心
    PROMO_EVENTS = "promo-events"
