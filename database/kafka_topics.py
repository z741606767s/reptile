from enum import Enum


class KafkaTopic(str, Enum):
    USER_CREATED = "user_created"
    ITEM_CREATED = "item_created"
    ORDER_CREATED = "order_created"
    NOTIFICATION = "notification"
    AUDIT_LOG = "audit_log"

    def with_prefix(self, prefix: str = "fastapi_"):
        """为主题添加前缀"""
        return f"{prefix}{self.value}"
