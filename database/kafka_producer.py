import asyncio
from aiokafka import AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError
import json
from config.settings import settings
from typing import Optional, List
from .kafka_topics import KafkaTopic
import logging

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.admin_client: Optional[AIOKafkaAdminClient] = None
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
                metadata_max_age_ms=30000,
            )
            await self.producer.start()
            logger.info("Kafka生产者已连接")
        except Exception as e:
            logger.error(f"Kafka生产者连接失败: {e}")
            self.producer = None
            raise
        finally:
            self._connecting = False

    async def connect_admin_client(self):
        """连接Kafka Admin客户端"""
        try:
            self.admin_client = AIOKafkaAdminClient(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
            )
            await self.admin_client.start()
            logger.info("Kafka Admin客户端已连接")
        except Exception as e:
            logger.error(f"Kafka Admin客户端连接失败: {e}")
            self.admin_client = None
            raise

    async def connect_with_retry(self, retries=5, delay=5):
        """带重试机制的连接方法"""
        for attempt in range(retries):
            try:
                await self.connect()
                print(f"Kafka生产者连接成功(尝试 {attempt + 1}/{retries})")

                # 同时连接Admin客户端
                await self.connect_admin_client()
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
            self.producer = None
            print("Kafka生产者已断开")

        if self.admin_client:
            await self.admin_client.close()
            self.admin_client = None
            print("Kafka Admin客户端已断开")

    async def send_message(self, topic: KafkaTopic, value: dict):
        """发送消息到Kafka"""
        if not self.producer:
            await self.connect()

        topic_name = topic.with_prefix(settings.KAFKA_TOPIC_PREFIX)

        try:
            # 直接发送消息，Kafka会自动创建主题（如果配置允许）
            await self.producer.send_and_wait(topic_name, value)
            logger.info(f"消息已发送到主题: {topic_name}")
        except Exception as e:
            logger.error(f"发送消息到主题 {topic_name} 时出错: {e}")
            # 尝试重新连接
            await self.disconnect()
            await self.connect_with_retry()
            # 重新发送
            await self.producer.send_and_wait(topic_name, value)

    async def ensure_topics_exist(self, topics: List[KafkaTopic]):
        """确保所有主题存在"""
        if not self.admin_client:
            await self.connect_admin_client()

        topic_names = [topic.with_prefix(settings.KAFKA_TOPIC_PREFIX) for topic in topics]

        try:
            # 获取现有主题
            cluster_metadata = await self.admin_client.describe_topics()
            existing_topics = set(cluster_metadata.keys())

            # 找出不存在的主题
            missing_topics = set(topic_names) - existing_topics

            if missing_topics:
                logger.info(f"以下主题不存在，尝试创建: {missing_topics}")

                # 创建新主题
                new_topics = [
                    NewTopic(
                        name=topic,
                        num_partitions=1,  # 默认分区数
                        replication_factor=1  # 默认副本因子
                    )
                    for topic in missing_topics
                ]

                try:
                    await self.admin_client.create_topics(new_topics)
                    logger.info(f"成功创建主题: {missing_topics}")
                except TopicAlreadyExistsError:
                    logger.info(f"主题已存在: {missing_topics}")
                except Exception as e:
                    logger.error(f"创建主题失败: {e}")
        except Exception as e:
            logger.error(f"检查主题存在性时出错: {e}")

    async def create_topic_if_not_exists(self, topic_name: str, partitions=1, replication_factor=1):
        """如果主题不存在则创建"""
        if not self.admin_client:
            await self.connect_admin_client()

        try:
            # 检查主题是否存在
            cluster_metadata = await self.admin_client.describe_topics([topic_name])

            if topic_name not in cluster_metadata:
                logger.info(f"主题 '{topic_name}' 不存在，尝试创建...")

                # 创建新主题
                new_topic = NewTopic(
                    name=topic_name,
                    num_partitions=partitions,
                    replication_factor=replication_factor
                )

                await self.admin_client.create_topics([new_topic])
                logger.info(f"成功创建主题: {topic_name}")
            else:
                logger.debug(f"主题 '{topic_name}' 已存在")
        except TopicAlreadyExistsError:
            logger.info(f"主题 '{topic_name}' 已存在")
        except Exception as e:
            logger.error(f"创建主题 '{topic_name}' 时出错: {e}")


# 全局Kafka生产者实例
kafka_producer = KafkaProducer()