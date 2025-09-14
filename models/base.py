from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any


class BaseModelMixin(BaseModel):
    """基础模型混合类"""

    def to_dict(self) -> Dict[str, Any]:
        """将模型转换为字典"""
        return self.dict()

    def to_json(self) -> str:
        """将模型转换为JSON字符串"""
        return self.json()

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
