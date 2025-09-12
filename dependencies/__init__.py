from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from config import settings
from database.redis import redis_client
from database.kafka_producer import kafka_producer
import logging

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


# 模拟用户验证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前用户"""
    # 从Redis获取用户信息
    redis = await redis_client.get_redis()
    user_data = await redis.get(f"user:{token}")

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 这里简化了，实际应该反序列化用户数据
    return {"id": 1, "name": "Alice", "email": "alice@example.com", "is_admin": False}


async def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    """获取当前管理员用户"""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


# 数据库依赖
async def get_mysql():
    from database.mysql import mysql_db
    async with mysql_db.get_cursor() as cursor:
        yield cursor


async def get_mongodb():
    from database.mongodb import mongodb
    db = mongodb.get_database()
    yield db


async def get_kafka():
    """获取Kafka生产者实例"""
    yield kafka_producer


async def get_redis():
    """获取Redis实例"""
    redis = await redis_client.get_redis()
    yield redis