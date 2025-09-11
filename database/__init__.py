from .kafka_consumer import kafka_consumer
from .kafka_topics import KafkaTopic
from services.email_service import email_service
from services.notification_service import notification_service
from database.redis import redis_client
import logging

logger = logging.getLogger(__name__)


async def register_kafka_handlers():
    """注册Kafka消息处理器"""

    # 用户创建消息处理器
    async def handle_user_created(message):
        logger.info(f"处理用户创建消息: {message}")

        # 发送欢迎邮件
        await email_service.send_welcome_email(message)

        # 创建系统通知
        await notification_service.create_user_notification(message)

        # 更新用户统计
        redis = await redis_client.get_redis()
        await redis.incr("stats:user_count")

    # 通知消息处理器
    async def handle_notification(message):
        logger.info(f"处理通知消息: {message}")

        # 发送通知邮件
        await email_service.send_notification_email(message)

        # 广播通知
        await notification_service.broadcast_notification(message)

    # 审计日志处理器
    async def handle_audit_log(message):
        logger.info(f"处理审计日志: {message}")
        # 在实际应用中，这里可能会将审计日志存储到专门的日志系统或数据库

    # 注册处理器
    kafka_consumer.register_handler(KafkaTopic.USER_CREATED, handle_user_created)
    kafka_consumer.register_handler(KafkaTopic.NOTIFICATION, handle_notification)
    kafka_consumer.register_handler(KafkaTopic.AUDIT_LOG, handle_audit_log)

    logger.info("Kafka消息处理器注册完成")