from redis.asyncio import Redis
from config.settings import settings
from typing import Optional
import logging

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self.redis: Optional[Redis] = None

    async def connect(self):
        """连接Redis"""
        self.redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            db=settings.REDIS_DB,
            encoding="utf-8",
            decode_responses=True
        )
        # 测试连接
        await self.redis.ping()
        print("Redis连接已建立")

    async def disconnect(self):
        """断开Redis连接"""
        if self.redis:
            await self.redis.close()
            print("Redis连接已关闭")

    async def get_redis(self) -> Redis:
        """获取Redis实例"""
        if not self.redis:
            await self.connect()
        return self.redis


# 全局Redis实例
redis_client = RedisClient()