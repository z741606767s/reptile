"""
API 包初始化文件
导出所有版本的路由
"""

# 导出v1路由
from .v1 import router as v1_router

# 导出v2路由
from .v2 import router as v2_router

# 导出所有路由
__all__ = ["v1_router", "v2_router"]
