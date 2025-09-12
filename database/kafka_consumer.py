from aiokafka import AIOKafkaConsumer
import asyncio
import json
import logging
from typing import Callable, Dict, Any, Optional
from config.settings import settings
from .kafka_topics import KafkaTopic

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KafkaConsumer:
    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.message_handlers: Dict[str, Callable] = {}
        self.is_running = False
        self._consuming_task: Optional[asyncio.Task] = None

    async def connect(self):
        """连接Kafka"""
        self.consumer = AIOKafkaConsumer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id="fastapi_consumer_group",
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,  # 增加自动提交间隔
            auto_offset_reset='earliest',
            metadata_max_age_ms=30000, # 允许自动创建主题
            session_timeout_ms=30000,  # 增加会话超时时间（默认10秒）
            heartbeat_interval_ms=3000,  # 设置心跳间隔（默认3秒）
            max_poll_interval_ms=300000,  # 增加最大轮询间隔（默认5分钟）
        )

        # 订阅所有主题
        topics = [topic.with_prefix(settings.KAFKA_TOPIC_PREFIX) for topic in KafkaTopic]

        # 启动消费者
        await self.consumer.start()

        # 确保所有主题都存在
        for topic in topics:
            await self.ensure_topic_exists(topic)

        # 订阅主题
        self.consumer.subscribe(topics)

        logger.info(f"Kafka消费者已连接，订阅主题: {topics}")

    async def connect_with_retry(self, retries=5, delay=5):
        """带重试机制的连接方法"""
        for attempt in range(retries):
            try:
                await self.connect()
                print(f"Kafka消费者连接成功(尝试 {attempt + 1}/{retries})")
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
        self.is_running = False

        # 取消消费任务
        if self._consuming_task and not self._consuming_task.done():
            self._consuming_task.cancel()
            try:
                await self._consuming_task
            except asyncio.CancelledError:
                pass

        # 关闭消费者
        if self.consumer:
            await self.consumer.stop()
            self.consumer = None

        logger.info("Kafka消费者已断开")

    def register_handler(self, topic: KafkaTopic, handler: Callable[[Any], None]):
        """注册消息处理器"""
        topic_name = topic.with_prefix(settings.KAFKA_TOPIC_PREFIX)
        self.message_handlers[topic_name] = handler
        logger.info(f"已为主题 {topic_name} 注册处理器")

    async def consume_messages(self):
        """消费消息"""
        self.is_running = True
        retry_count = 0
        max_retries = 10

        while self.is_running and retry_count < max_retries:
            try:
                async for msg in self.consumer:
                    if not self.is_running:
                        break

                    # 重置重试计数
                    retry_count = 0

                    logger.info(f"收到消息: 主题={msg.topic}, 分区={msg.partition}, 偏移量={msg.offset}")

                    # 查找对应的处理器
                    handler = self.message_handlers.get(msg.topic)
                    if handler:
                        try:
                            # 使用异步执行处理器，避免阻塞消费循环
                            asyncio.create_task(self.safe_handler_execution(handler, msg.value))
                        except Exception as e:
                            logger.error(f"处理消息时出错: {e}")
                    else:
                        logger.warning(f"未找到主题 {msg.topic} 的处理器")
            except asyncio.CancelledError:
                logger.info("消息消费任务被取消")
            except Exception as e:
                retry_count += 1
                logger.error(f"消费消息时发生错误 (尝试 {retry_count}/{max_retries}): {e}")

                if retry_count < max_retries:
                    # 等待一段时间后重试
                    await asyncio.sleep(min(2 ** retry_count, 30))  # 指数退避，最大30秒

                    # 尝试重新连接
                    try:
                        await self.disconnect()
                        await self.connect()
                    except Exception as reconnect_error:
                        logger.error(f"重新连接失败: {reconnect_error}")
                else:
                    logger.error("达到最大重试次数，停止消费")
                    break
            finally:
                self.is_running = False

    async def safe_handler_execution(self, handler, value):
        """安全执行处理器，带有超时机制"""
        try:
            # 设置处理超时（例如30秒）
            await asyncio.wait_for(handler(value), timeout=30.0)
        except asyncio.TimeoutError:
            logger.error(f"消息处理超时: {value}")
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")

    async def start_consuming(self):
        """开始消费消息"""
        if not self.consumer:
            await self.connect()

        # 启动消费任务
        self._consuming_task = asyncio.create_task(self.consume_messages())
        logger.info("Kafka消费者已开始消费消息")

    async def ensure_topic_exists(self, topic_name: str):
        """确保主题存在"""
        try:
            # 获取集群元数据
            cluster_metadata = await self.consumer.topics()
            # 检查主题是否存在
            if topic_name not in cluster_metadata:
                logger.info(f"主题 '{topic_name}' 不存在，等待自动创建...")
                # 创建一个临时生产者来发送测试消息
                from aiokafka import AIOKafkaProducer
                producer = AIOKafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
                await producer.start()
                try:
                    await producer.send(topic_name, {"test": "message"})
                    logger.info(f"已发送测试消息到主题 '{topic_name}' 以触发创建")
                finally:
                    await producer.stop()
        except Exception as e:
            logger.error(f"检查主题存在性时出错: {e}")


# 全局Kafka消费者实例
kafka_consumer = KafkaConsumer()
