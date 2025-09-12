from aiokafka import AIOKafkaConsumer
import asyncio
import json
import logging
from typing import Callable, Dict, Any, Optional
from config.settings import settings
from .kafka_topics import KafkaTopic
from datetime import datetime
import time

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)



class KafkaConsumer:
    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.message_handlers: Dict[str, Callable] = {}
        self.is_running = False
        self._consuming_task: Optional[asyncio.Task] = None
        self._metrics = {
            'messages_processed': 0,
            'messages_failed': 0,
            'last_processed_at': None,
            'processing_times': []
        }
        self._max_retries = 3
        self._dead_letter_topics = {}

    async def connect(self):
        """连接Kafka"""
        self.consumer = AIOKafkaConsumer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id="fastapi_consumer_group",
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            enable_auto_commit=False,  # 禁用自动提交，手动控制
            auto_offset_reset='earliest',
            metadata_max_age_ms=30000, # 允许自动创建主题
            session_timeout_ms=30000,  # 增加会话超时时间（默认10秒）
            heartbeat_interval_ms=3000,  # 设置心跳间隔（默认3秒）
            max_poll_interval_ms=300000,  # 增加最大轮询间隔（默认5分钟）
            max_poll_records=100,  # 每次拉取的最大记录数
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

    def register_dead_letter_topic(self, original_topic: KafkaTopic, dead_letter_topic: KafkaTopic):
        """注册死信主题"""
        original_name = original_topic.with_prefix(settings.KAFKA_TOPIC_PREFIX)
        dead_letter_name = dead_letter_topic.with_prefix(settings.KAFKA_TOPIC_PREFIX)
        self._dead_letter_topics[original_name] = dead_letter_name
        logger.info(f"已为主题 {original_name} 注册死信主题 {dead_letter_name}")

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
                            # 处理消息
                            success = await self.process_message(handler, msg)

                            if success:
                                # 手动提交偏移量
                                await self.consumer.commit()
                                self._update_metrics(success=True)
                            else:
                                # 处理失败，不提交偏移量，让消息重新被消费
                                self._update_metrics(success=False)
                                logger.error(f"消息处理失败: 主题={msg.topic}, 偏移量={msg.offset}")

                        except Exception as e:
                            logger.error(f"处理消息时发生错误: {e}")
                            self._update_metrics(success=False)
                    else:
                        logger.warning(f"未找到主题 {msg.topic} 的处理器")
                        self._update_metrics(success=False)

            except asyncio.CancelledError:
                logger.info("消息消费任务被取消")
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"消费消息时发生错误 (尝试 {retry_count}/{max_retries}): {e}")

                if retry_count < max_retries:
                    # 等待一段时间后重试
                    await asyncio.sleep(min(2 ** retry_count, 30))

                    # 尝试重新连接
                    try:
                        await self.disconnect()
                        await self.connect()
                    except Exception as reconnect_error:
                        logger.error(f"重新连接失败: {reconnect_error}")
                else:
                    logger.error("达到最大重试次数，停止消费")
                    break

        self.is_running = False

    async def process_message(self, handler, msg, retry_count=0):
        """处理单条消息，支持重试"""
        try:
            start_time = time.time()

            # 执行处理器
            await self.safe_handler_execution(handler, msg.value)

            processing_time = time.time() - start_time
            logger.info(f"消息处理成功: 主题={msg.topic}, 偏移量={msg.offset}, 处理时间={processing_time:.2f}s")

            return True
        except Exception as e:
            if retry_count < self._max_retries:
                # 重试
                logger.warning(f"消息处理失败，准备重试 (尝试 {retry_count + 1}/{self._max_retries}): {e}")
                await asyncio.sleep(2 ** retry_count)  # 指数退避
                return await self.process_message(handler, msg, retry_count + 1)
            else:
                # 重试次数用完，发送到死信队列
                logger.error(f"消息处理失败，重试次数用完: {e}")
                await self.send_to_dead_letter_queue(msg)
                return False

    async def send_to_dead_letter_queue(self, msg):
        """发送消息到死信队列"""
        dead_letter_topic = self._dead_letter_topics.get(msg.topic)
        if dead_letter_topic and hasattr(self, '_producer'):
            try:
                dead_letter_message = {
                    'original_topic': msg.topic,
                    'original_partition': msg.partition,
                    'original_offset': msg.offset,
                    'original_timestamp': msg.timestamp,
                    'failure_timestamp': datetime.utcnow().isoformat(),
                    'message': msg.value
                }

                await self._producer.send(dead_letter_topic, dead_letter_message)
                logger.info(f"消息已发送到死信队列: {msg.topic} -> {dead_letter_topic}")
            except Exception as e:
                logger.error(f"发送到死信队列失败: {e}")
        else:
            logger.warning(f"未找到主题 {msg.topic} 的死信队列配置")

    def _update_metrics(self, success=True):
        """更新监控指标"""
        if success:
            self._metrics['messages_processed'] += 1
        else:
            self._metrics['messages_failed'] += 1

        self._metrics['last_processed_at'] = datetime.now()
        self._metrics['processing_times'].append(time.time())

        # 只保留最近1000个处理时间
        if len(self._metrics['processing_times']) > 1000:
            self._metrics['processing_times'] = self._metrics['processing_times'][-1000:]

    def get_metrics(self):
        """获取消费者指标"""
        processing_times = self._metrics['processing_times']
        if processing_times:
            avg_processing_time = sum(processing_times) / len(processing_times)
        else:
            avg_processing_time = 0

        return {
            'messages_processed': self._metrics['messages_processed'],
            'messages_failed': self._metrics['messages_failed'],
            'last_processed_at': self._metrics['last_processed_at'],
            'avg_processing_time': avg_processing_time,
            'is_running': self.is_running
        }

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
                    logger.info(f"已发送测试消息到主题 '{topic_name}' 已触发自动创建")
                    # 等待主题创建完成
                    await asyncio.sleep(5)  # 等待5秒
                finally:
                    await producer.stop()
        except Exception as e:
            logger.error(f"检查主题存在性时出错: {e}")


# 全局Kafka消费者实例
kafka_consumer = KafkaConsumer()
