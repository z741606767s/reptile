from datetime import datetime
from typing import Optional, Any
from pydantic import field_serializer
from models.base import BaseModelMixin


class CategoryModel(BaseModelMixin):
    """分类模型"""
    id: Optional[int] = None
    name: str
    slug: str
    parent_id: Optional[int] = None
    level: int = 1
    sort: int = 0
    is_enabled: bool = True
    path: Optional[str] = None
    uri_path: Optional[str] = None
    site: str
    url: str
    href: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer('created_at', 'updated_at')
    def serialize_dt(self, dt: Optional[datetime], _info: Any) -> Optional[str]:
        """将 datetime 对象序列化为指定格式的字符串"""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    class Config:
        table_name = "r_category"
