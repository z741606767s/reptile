import os
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # 项目配置
    PROJECT_NAME: str = "FastAPI Reptile 爬虫项目"
    PROJECT_DESCRIPTION: str = "集成MySQL, Redis, MongoDB, Kafka和ZooKeeper的示例"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    API_V2_STR: str = "/api/v2"

    # 调试配置
    DEBUG: bool = os.getenv("DEBUG", False)
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    # 日志文件配置
    LOG_FILE: str = os.getenv("LOG_FILE", "app.log")
    # 日志文件大小配置
    LOG_FILE_SIZE: int = os.getenv("LOG_FILE_SIZE", 1024 * 1024 * 100)
    # 日志文件最大字节配置
    LOG_FILE_MAX_BYTES: int = os.getenv("LOG_FILE_MAX_BYTES", 1024 * 1024 * 100)
    # 日志文件备份配置
    LOG_FILE_BACKUP: int = os.getenv("LOG_FILE_BACKUP", 5)
    # 日志格式配置
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # 日志日期格式配置
    LOG_DATE_FORMAT: str = os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
    # 日志文件编码配置
    LOG_FILE_ENCODING: str = os.getenv("LOG_FILE_ENCODING", "utf-8")
    # 日志文件模式配置
    LOG_FILE_MODE: str = os.getenv("LOG_FILE_MODE", "a")

    # 数据库配置
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "password")
    MYSQL_DB: str = os.getenv("MYSQL_DB", "fastapi_demo")

    # Redis配置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))

    # MongoDB配置
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB: str = os.getenv("MONGODB_DB", "fastapi_demo")

    # Kafka配置
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_PREFIX: str = os.getenv("KAFKA_TOPIC_PREFIX", "fastapi_")
    # Kafka主题配置
    KAFKA_NUM_PARTITIONS: int = int(os.getenv("KAFKA_NUM_PARTITIONS", "3"))
    KAFKA_REPLICATION_FACTOR: int = int(os.getenv("KAFKA_REPLICATION_FACTOR", "1"))
    # Kafka重试配置
    KAFKA_CONNECT_RETRIES: int = int(os.getenv("KAFKA_CONNECT_RETRIES", "3"))
    KAFKA_CONNECT_DELAY: int = int(os.getenv("KAFKA_CONNECT_DELAY", "5"))

    # ZooKeeper配置
    ZOOKEEPER_HOSTS: str = os.getenv("ZOOKEEPER_HOSTS", "localhost:2181")

    # CORS设置
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()