from fastapi import APIRouter, Request
from aiokafka.admin import AIOKafkaAdminClient
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
from aiokafka.admin import NewTopic
from config.settings import settings
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/topics")
async def list_kafka_topics(request: Request):
    if not hasattr(request.app.state, "kafka_available") or not request.app.state.kafka_available:
        return {"message": "Kafka 不可用."}

    try:
        # 使用KafkaAdminClient获取主题列表
        admin_client = KafkaAdminClient(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            client_id="fastapi-admin"
        )
        topics = admin_client.list_topics()
        admin_client.close()

        return {"topics": topics}
    except Exception as e:
        return {"error": f"获取主题列表失败: {e}"}


@router.post("/topics/{topic_name}")
async def create_kafka_topic(request: Request, topic_name: str, partitions: int = 1, replication_factor: int = 1):
    if not hasattr(request.app.state, "kafka_available") or not request.app.state.kafka_available:
        return {"message": "Kafka 不可用."}

    try:
        # 使用KafkaAdminClient创建主题
        admin_client = KafkaAdminClient(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            client_id="fastapi-admin"
        )

        topic = NewTopic(
            name=topic_name,
            num_partitions=partitions,
            replication_factor=replication_factor
        )

        admin_client.create_topics([topic])
        admin_client.close()

        return {"message": f"主题 '{topic_name}' 已创建"}
    except TopicAlreadyExistsError:
        return {"message": f"主题 '{topic_name}' 已存在"}
    except Exception as e:
        return {"error": f"创建主题失败: {e}"}


@router.post("/topics/create")
async def create_topics_if_not_exist(request: Request):
    """创建所有需要的主题（如果不存在）"""
    if not hasattr(request.app.state, "kafka_available") or not request.app.state.kafka_available:
        return {"message": "Kafka 不可用."}

    try:
        admin_client = AIOKafkaAdminClient(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
        )
        await admin_client.start()

        # 获取现有主题
        existing_topics = await admin_client.list_topics()

        # 需要创建的主题
        from database.kafka_topics import KafkaTopic
        topics_to_create = []

        for topic_enum in KafkaTopic:
            topic_name = topic_enum.with_prefix(settings.KAFKA_TOPIC_PREFIX)
            if topic_name not in existing_topics:
                topics_to_create.append(
                    NewTopic(
                        name=topic_name,
                        num_partitions=settings.KAFKA_NUM_PARTITIONS,
                        replication_factor=settings.KAFKA_REPLICATION_FACTOR
                    )
                )

        # 创建不存在的主题
        if topics_to_create:
            await admin_client.create_topics(topics_to_create)
            logger.info(f"已创建主题: {[t.name for t in topics_to_create]}")

        await admin_client.close()
        return {"message": "已创建主题."}
    except Exception as e:
        logger.error(f"创建主题时出错: {e}")
