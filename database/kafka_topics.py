import logging
from enum import Enum
from config import settings

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


class KafkaTopic(str, Enum):
    USER_CREATED = "user_created"  # 用户创建
    ITEM_CREATED = "item_created"  # 商品创建
    ORDER_CREATED = "order_created"  # 订单创建
    NOTIFICATION = "notification"  # 通知
    AUDIT_LOG = "audit_log"  # 审计日志
    CRAWL_RESULTS = "crawl_results"  # 爬取结果
    CRAWL_LEVEL_RESULTS = "crawl_level_results"  # 爬取顶级分类的子类

    def with_prefix(self, prefix: str = "fastapi_"):
        """为主题添加前缀"""
        return f"{prefix}{self.value}"
