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
    KAFKA_NUM_PARTITIONS = int(os.getenv("KAFKA_NUM_PARTITIONS", "3"))
    KAFKA_REPLICATION_FACTOR = int(os.getenv("KAFKA_REPLICATION_FACTOR", "1"))
    # Kafka重试配置
    KAFKA_CONNECT_RETRIES = int(os.getenv("KAFKA_CONNECT_RETRIES", "3"))
    KAFKA_CONNECT_DELAY = int(os.getenv("KAFKA_CONNECT_DELAY", "5"))

    # ZooKeeper配置
    ZOOKEEPER_HOSTS: str = os.getenv("ZOOKEEPER_HOSTS", "localhost:2181")

    # CORS设置
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()