from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BaseModelMixin(BaseModel):
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True