from fastapi import APIRouter, HTTPException
from typing import List
from config import settings
from models.user import User, UserCreate
import logging

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


# 创建 v2 用户路由组
router = APIRouter(
    prefix="/users",
    tags=["users"],
)

# 模拟数据库 (v2 可能有不同的结构)
fake_users_db_v2 = {
    1: {"id": 1, "name": "Alice", "email": "alice@example.com", "preferences": {}},
    2: {"id": 2, "name": "Bob", "email": "bob@example.com", "preferences": {}}
}


@router.get("/", response_model=List[User])
async def get_users_v2(skip: int = 0, limit: int = 10, search: str = None):
    """获取用户列表 (v2) - 支持搜索"""
    users = list(fake_users_db_v2.values())

    # v2 新增功能：搜索
    if search:
        users = [user for user in users if search.lower() in user["name"].lower()]

    return users[skip:skip + limit]


@router.get("/{user_id}", response_model=User)
async def get_user_v2(user_id: int):
    """根据ID获取用户 (v2)"""
    if user_id not in fake_users_db_v2:
        raise HTTPException(status_code=404, detail="User not found")
    return fake_users_db_v2[user_id]


# v2 新增路由
@router.get("/{user_id}/preferences")
async def get_user_preferences(user_id: int):
    """获取用户偏好设置 (v2 新增)"""
    if user_id not in fake_users_db_v2:
        raise HTTPException(status_code=404, detail="User not found")
    return fake_users_db_v2[user_id].get("preferences", {})