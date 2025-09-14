from fastapi import APIRouter
from . import users, category

# 创建 v2 路由组
router = APIRouter()

# 引入子路由
router.include_router(users.router, tags=["v2-users"])
router.include_router(category.router, prefix="/category", tags=["v2-category"])


# 可选：为 v2 路由组添加特定的路由
@router.get("/status")
async def v2_status():
    return {"version": "2.0", "status": "beta"}


# 导出路由
__all__ = ["router"]
