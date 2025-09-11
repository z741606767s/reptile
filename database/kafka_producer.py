import asyncio
from aiokafka import AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError
import json
from config.settings import settings
from typing import Optional
from .kafka_topics import KafkaTopic
import logging

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self._connecting = False

    async def connect(self):
        """连接Kafka"""
        if self._connecting:
            return

        self._connecting = True
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                request_timeout_ms=30000,
                retry_backoff_ms=1000,
                # 允许自动创建主题
                metadata_max_age_ms=30000,  # 更频繁地更新元数据
            )
            await self.producer.start()
            logger.info("Kafka生产者已连接")
        except Exception as e:
            logger.error(f"Kafka生产者连接失败: {e}")
            self.producer = None
            raise
        finally:
            self._connecting = False

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

        # 确保主题存在
        await self.ensure_topic_exists(topic_name)

        try:
            await self.producer.send_and_wait(topic_name, value)
            logger.info(f"消息已发送到主题: {topic_name}")
        except Exception as e:
            logger.error(f"发送消息到主题 {topic_name} 时出错: {e}")
            # 尝试重新连接
            await self.disconnect()
            await self.connect()
            # 重新发送
            await self.producer.send_and_wait(topic_name, value)

    async def ensure_topic_exists(self, topic_name: str):
        """确保主题存在"""
        if not self.producer:
            await self.connect()

        # 获取集群元数据，这会触发主题的自动创建
        try:
            cluster_metadata = await self.producer.client.cluster()
            # 检查主题是否存在
            if topic_name not in cluster_metadata.topics():
                logger.info(f"主题 '{topic_name}' 不存在，等待自动创建...")
                # 发送一个测试消息来触发主题创建
                try:
                    await self.producer.send(topic_name, {"test": "message"})
                    logger.info(f"已发送测试消息到主题 '{topic_name}' 以触发创建")
                except Exception as e:
                    logger.warning(f"发送测试消息失败: {e}. 主题将在第一次真实消息发送时创建")
        except Exception as e:
            logger.error(f"检查主题存在性时出错: {e}")


# 全局Kafka生产者实例
kafka_producer = KafkaProducer()
