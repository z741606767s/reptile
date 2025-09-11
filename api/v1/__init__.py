from fastapi import APIRouter
from . import kafka, users, admin  # 导入所有路由模块

router = APIRouter()

# 引入子路由，可以在这里添加统一的前缀或标签
router.include_router(kafka.router, prefix="/kafka", tags=["kafka"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])


# 可选：为 v1 路由组添加特定的路由
@router.get("/status")
async def v1_status():
    return {"version": "1.0", "status": "stable"}


# 确保导出 router
__all__ = ["router"]
