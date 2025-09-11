import logging
from typing import Dict, Any
from database.redis import redis_client

# 配置日志
logger = logging.getLogger(__name__)


class NotificationService:
    async def create_user_notification(self, user_data: Dict[str, Any]):
        """创建用户通知"""
        logger.info(f"为用户 {user_data.get('name')} 创建系统通知")

        # 将通知存储到Redis
        redis = await redis_client.get_redis()
        notification_key = f"user:{user_data.get('user_id', 'unknown')}:notifications"

        notification = {
            "type": "welcome",
            "message": f"欢迎 {user_data.get('name')} 加入我们的平台!",
            "timestamp": "2023-01-01T00:00:00Z"  # 实际应用中应该使用当前时间
        }

        # 使用Redis列表存储通知
        await redis.lpush(notification_key, str(notification))
        await redis.ltrim(notification_key, 0, 99)  # 只保留最近100条通知

        logger.info(f"已为用户 {user_data.get('name')} 创建系统通知")

    async def broadcast_notification(self, notification_data: Dict[str, Any]):
        """广播通知"""
        logger.info(f"广播通知: {notification_data.get('message')}")

        # 在实际应用中，这里可能会使用WebSocket向所有连接的客户端广播通知
        # 这里我们简单地将通知存储到Redis
        redis = await redis_client.get_redis()
        await redis.publish("notifications", notification_data.get('message', ''))

        logger.info(f"通知已广播")


# 全局通知服务实例
notification_service = NotificationService()