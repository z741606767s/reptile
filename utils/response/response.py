from datetime import datetime
from typing import Any, Optional, Dict, List
from pydantic import BaseModel
from enum import Enum
from fastapi.responses import JSONResponse
from fastapi import status
import logging
from config import settings

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class BaseResponse(BaseModel):
    status: ResponseStatus
    message: Optional[str] = None
    data: Optional[Any] = None
    timestamp: str = datetime.now().isoformat()  # 直接存储为字符串
    code: int = 200

    def dict(self, *args, **kwargs):
        # 重写 dict 方法，确保所有字段都是 JSON 可序列化的
        result = super().dict(*args, **kwargs)
        # 确保 timestamp 是字符串
        if isinstance(result.get('timestamp'), datetime):
            result['timestamp'] = result['timestamp'].isoformat()
        return result


class SuccessResponse(BaseResponse):
    status: ResponseStatus = ResponseStatus.SUCCESS


class ErrorResponse(BaseResponse):
    status: ResponseStatus = ResponseStatus.ERROR


class PaginatedResponse(SuccessResponse):
    pagination: Optional[Dict[str, Any]] = None


class ResponseUtil:
    @staticmethod
    def _serialize_data(data: Any) -> Any:
        """递归序列化数据，确保所有日期时间对象转换为字符串"""
        if isinstance(data, dict):
            return {k: ResponseUtil._serialize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [ResponseUtil._serialize_data(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        elif hasattr(data, 'dict') and callable(getattr(data, 'dict')):
            return ResponseUtil._serialize_data(data.dict())
        else:
            return data

    @staticmethod
    def success(
            data: Any = None,
            message: str = "操作成功",
            code: int = status.HTTP_200_OK
    ) -> JSONResponse:
        """成功响应"""
        # 序列化数据
        serialized_data = ResponseUtil._serialize_data(data)

        response = SuccessResponse(
            message=message,
            data=serialized_data,
            code=code
        )
        return JSONResponse(
            content=response.dict(),
            status_code=code
        )

    @staticmethod
    def error(
            message: str = "操作失败",
            code: int = status.HTTP_400_BAD_REQUEST,
            data: Any = None
    ) -> JSONResponse:
        """错误响应"""
        # 序列化数据
        serialized_data = ResponseUtil._serialize_data(data)

        response = ErrorResponse(
            message=message,
            data=serialized_data,
            code=code
        )
        return JSONResponse(
            content=response.dict(),
            status_code=code
        )

    @staticmethod
    def paginated(
            data: List[Any],
            total: int,
            page: int,
            limit: int,
            message: str = "查询成功",
            code: int = status.HTTP_200_OK
    ) -> JSONResponse:
        """分页响应"""
        total_pages = (total + limit - 1) // limit if limit > 0 else 0

        pagination = {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }

        # 序列化数据
        serialized_data = ResponseUtil._serialize_data(data)

        response = PaginatedResponse(
            message=message,
            data=serialized_data,
            code=code,
            pagination=pagination
        )

        return JSONResponse(
            content=response.dict(),
            status_code=code
        )

    @staticmethod
    def created(
            data: Any = None,
            message: str = "创建成功",
            code: int = status.HTTP_201_CREATED
    ) -> JSONResponse:
        """创建成功响应"""
        return ResponseUtil.success(data, message, code)

    @staticmethod
    def not_found(
            message: str = "资源不存在",
            code: int = status.HTTP_404_NOT_FOUND
    ) -> JSONResponse:
        """未找到资源响应"""
        return ResponseUtil.error(message, code)

    @staticmethod
    def unauthorized(
            message: str = "未授权访问",
            code: int = status.HTTP_401_UNAUTHORIZED
    ) -> JSONResponse:
        """未授权响应"""
        return ResponseUtil.error(message, code)

    @staticmethod
    def forbidden(
            message: str = "禁止访问",
            code: int = status.HTTP_403_FORBIDDEN
    ) -> JSONResponse:
        """禁止访问响应"""
        return ResponseUtil.error(message, code)

    @staticmethod
    def validation_error(
            errors: Any,
            message: str = "参数验证失败",
            code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    ) -> JSONResponse:
        """参数验证失败响应"""
        return ResponseUtil.error(message, code, data=errors)

    @staticmethod
    def server_error(
            message: str = "服务器内部错误",
            code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
            data: Any = None  # 添加 data 参数
    ) -> JSONResponse:
        """服务器错误响应"""
        return ResponseUtil.error(message, code, data=data)


# 创建全局实例
response_util = ResponseUtil()