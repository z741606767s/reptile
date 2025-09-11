from fastapi import APIRouter, Depends, HTTPException
from dependencies import get_current_admin_user, get_redis
import redis

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get("/stats")
async def admin_stats(
        current_user: dict = Depends(get_current_admin_user),
        redis: redis.Redis = Depends(get_redis)
):
    """管理员统计信息"""
    # 从Redis获取统计信息
    user_count = await redis.get("stats:user_count") or 0
    item_count = await redis.get("stats:item_count") or 0

    return {
        "users": int(user_count),
        "items": int(item_count),
        "active_users": await redis.scard("active_users"),
        "revenue": 10000
    }


@router.post("/cache/{key}")
async def set_cache(
        key: str,
        value: str,
        current_user: dict = Depends(get_current_admin_user),
        redis: redis.Redis = Depends(get_redis)
):
    """设置缓存值"""
    await redis.set(f"admin:{key}", value)
    return {"status": "ok", "key": key, "value": value}


@router.get("/cache/{key}")
async def get_cache(
        key: str,
        current_user: dict = Depends(get_current_admin_user),
        redis: redis.Redis = Depends(get_redis)
):
    """获取缓存值"""
    value = await redis.get(f"admin:{key}")
    return {"key": key, "value": value}