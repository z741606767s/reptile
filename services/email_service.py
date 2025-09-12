import logging
from typing import Dict, Any
from config import settings

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


class EmailService:
    async def send_welcome_email(self, user_data: Dict[str, Any]):
        """发送欢迎邮件"""
        # 在实际应用中，这里会调用邮件服务API
        logger.info(f"发送欢迎邮件给 {user_data.get('email')}: 欢迎 {user_data.get('name')} 加入我们的平台!")

        # 模拟邮件发送延迟
        import asyncio
        await asyncio.sleep(0.1)

        logger.info(f"欢迎邮件已发送给 {user_data.get('email')}")

    async def send_notification_email(self, notification_data: Dict[str, Any]):
        """发送通知邮件"""
        logger.info(f"发送通知邮件: {notification_data.get('message')}")

        # 模拟邮件发送延迟
        import asyncio
        await asyncio.sleep(0.1)

        logger.info(f"通知邮件已发送")


# 全局邮件服务实例
email_service = EmailService()