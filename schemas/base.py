from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class ResponseModel(BaseModel):
    """基础响应模型"""
    code: int = Field(200, description="HTTP状态码")
    status: bool = True
    message: Optional[str] = Field(None, description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="时间戳")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ListResponseModel(ResponseModel):
    """列表响应模型"""
    data: List[Any] = Field(..., description="数据列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页数量")


class ErrorResponseModel(ResponseModel):
    """错误响应模型"""
    status: bool = False
    error_code: Optional[str] = None
    error_detail: Optional[str] = None
