from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from .response import response_util
import traceback
from config import settings
import logging

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
):
    """处理参数验证异常"""
    return response_util.validation_error(
        errors=exc.errors(),
        message="参数验证失败"
    )


async def http_exception_handler(request: Request, exc):
    """处理HTTP异常"""
    status_code = exc.status_code if hasattr(exc, 'status_code') else 500
    message = exc.detail if hasattr(exc, 'detail') else "服务器错误"

    if status_code == status.HTTP_404_NOT_FOUND:
        return response_util.not_found(message)
    elif status_code == status.HTTP_401_UNAUTHORIZED:
        return response_util.unauthorized(message)
    elif status_code == status.HTTP_403_FORBIDDEN:
        return response_util.forbidden(message)
    else:
        return response_util.error(message, status_code)


async def global_exception_handler(request: Request, exc: Exception):
    """处理全局异常"""
    # 记录详细的错误信息
    error_details = {
        "error_type": exc.__class__.__name__,
        "error_message": str(exc),
        "traceback": traceback.format_exc()
    }

    # 在生产环境中，可能不希望将详细错误信息返回给客户端
    # 可以根据环境变量决定返回的信息详细程度
    is_debug = True  # 可以从配置中读取

    if is_debug:
        return response_util.server_error(
            message=str(exc) or "服务器内部错误",
            data=error_details  # 传递 data 参数
        )
    else:
        return response_util.server_error(
            message="服务器内部错误"
        )