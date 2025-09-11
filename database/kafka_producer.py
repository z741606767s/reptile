import asyncio
from aiokafka import AIOKafkaProducer
import json
from config.settings import settings
from typing import Optional
from .kafka_topics import KafkaTopic


class KafkaProducer:
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None

    async def connect(self):
        """连接Kafka"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()
        print("Kafka生产者已连接")

    async def connect_with_retry(self, retries=5, delay=5):
        """带重试机制的连接方法"""
        for attempt in range(retries):
            try:
                await self.connect()
                print(f"Kafka生产者连接成功(尝试 {attempt + 1}/{retries})")
                return True
            except Exception as e:
                if attempt < retries - 1:
                    print(f"Kafka连接尝试 {attempt + 1}/{retries} 失败: {e}")
                    await asyncio.sleep(delay)
                else:
                    print(f"所有Kafka连接尝试均失败: {e}")
                    raise

    async def disconnect(self):
        """断开Kafka连接"""
        if self.producer:
            await self.producer.stop()
            self.producer = None  # 设置为None，避免重复关闭
            print("Kafka生产者已断开")

    async def send_message(self, topic: KafkaTopic, value: dict):
        """发送消息到Kafka"""
        if not self.producer:
            await self.connect()

        topic_name = topic.with_prefix(settings.KAFKA_TOPIC_PREFIX)
        await self.producer.send_and_wait(topic_name, value)
        print(f"消息已发送到主题: {topic_name}")


# 全局Kafka生产者实例
kafka_producer = KafkaProducer()