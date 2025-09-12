import uvicorn
import asyncio
import sys
import signal
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config.settings import settings
from api.v1 import router as v1_router
from api.v2 import router as v2_router
from database.mysql import mysql_db
from database.redis import redis_client
from database.mongodb import mongodb
from database.kafka_producer import kafka_producer
from database.kafka_consumer import kafka_consumer
from database import register_kafka_handlers
from utils.response.exception_handlers import (
    validation_exception_handler,
    http_exception_handler,
    global_exception_handler
)
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量，用于存储关闭函数
_shutdown_handlers = []

# ====== 关闭处理函数 ======
def register_shutdown_handler(handler):
    """注册关闭处理函数"""
    _shutdown_handlers.append(handler)

# ====== 优雅关闭处理 ======
async def graceful_shutdown():
    """优雅关闭所有资源"""
    logger.info("开始优雅关闭...")
    for handler in reversed(_shutdown_handlers):
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
        except Exception as e:
            logger.error(f"关闭处理函数执行出错: {e}")
    logger.info("所有资源已关闭")

# ====== 初始化Kafka主题 ======
async def initialize_kafka_topics():
    """初始化Kafka主题"""
    if not hasattr(app.state, 'kafka_available') or not app.state.kafka_available:
        return

    try:
        # 获取所有主题
        from database.kafka_topics import KafkaTopic
        topics = [topic.with_prefix(settings.KAFKA_TOPIC_PREFIX) for topic in KafkaTopic]

        # 确保所有主题都存在
        for topic in topics:
            await kafka_producer.ensure_topic_exists(topic)

        logger.info(f"已初始化Kafka主题: {topics}")
    except Exception as e:
        logger.error(f"初始化Kafka主题时出错: {e}")

# ====== 应用生命周期 ======
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 注册关闭处理函数
    register_shutdown_handler(mysql_db.disconnect)
    register_shutdown_handler(redis_client.disconnect)
    register_shutdown_handler(mongodb.disconnect)
    register_shutdown_handler(kafka_producer.disconnect)
    register_shutdown_handler(kafka_consumer.disconnect)

    # 启动时连接所有数据库
    await mysql_db.connect()
    await redis_client.connect()
    await mongodb.connect()

    # Kafka 连接（带重试机制）
    kafka_available = True
    try:
        await kafka_producer.connect_with_retry(retries=5, delay=5)
    except Exception as e:
        logger.error(f"Kafka生产者连接失败: {e}")
        kafka_available = False

    try:
        await kafka_consumer.connect_with_retry(retries=5, delay=5)
    except Exception as e:
        logger.error(f"Kafka消费者连接失败: {e}")
        kafka_available = False

    # 设置应用状态
    app.state.kafka_available = kafka_available

    # 如果Kafka可用，注册处理器并启动消费者
    if hasattr(app.state, 'kafka_available') and app.state.kafka_available:
        try:
            await initialize_kafka_topics()
            await register_kafka_handlers()
            await kafka_consumer.start_consuming()
        except Exception as e:
            logger.error(f"Kafka消费者启动失败: {e}")
            app.state.kafka_available = False

    yield

    # 关闭所有资源
    await graceful_shutdown()

# ====== 应用实例 ======
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# ====== 注册异常处理器 ======
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(status.HTTP_400_BAD_REQUEST, http_exception_handler)
app.add_exception_handler(status.HTTP_401_UNAUTHORIZED, http_exception_handler)
app.add_exception_handler(status.HTTP_403_FORBIDDEN, http_exception_handler)
app.add_exception_handler(status.HTTP_404_NOT_FOUND, http_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# ====== 设置CORS ======
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== 引入v1和v2路由 ======
app.include_router(v1_router, prefix=settings.API_V1_STR)
app.include_router(v2_router, prefix=settings.API_V2_STR)

# ====== 根路由 ======
@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI FullStack Demo with v1 and v2 APIs"}

# ====== 健康检查路由 ======
@app.get("/health")
async def health_check():
    # 检查所有数据库连接状态
    mysql_status = "connected" if mysql_db.pool else "disconnected"
    redis_status = "connected" if redis_client.redis else "disconnected"
    mongo_status = "connected" if mongodb.client else "disconnected"

    # 检查Kafka状态
    kafka_producer_status = "connected" if hasattr(app.state,
                                                   'kafka_available') and app.state.kafka_available else "disconnected"
    kafka_consumer_status = "running" if hasattr(app.state,
                                                 'kafka_available') and app.state.kafka_available else "stopped"

    return {
        "status": "healthy",
        "mysql": mysql_status,
        "redis": redis_status,
        "mongodb": mongo_status,
        "kafka_producer": kafka_producer_status,
        "kafka_consumer": kafka_consumer_status
    }


# ====== 优雅关闭处理 ======
async def handle_shutdown():
    """处理优雅关闭"""
    await graceful_shutdown()
    sys.exit(0)

# ====== 信号处理 ======
def handle_signal(signum, frame):
    """信号处理函数"""
    logger.info(f"收到信号 {signum}，开始优雅关闭...")
    # 创建异步任务来处理关闭
    asyncio.create_task(handle_shutdown())


if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    uvicorn.run(app, host="0.0.0.0", port=8000)
