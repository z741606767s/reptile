from fastapi import APIRouter, HTTPException, Depends
from typing import List

from starlette import status

from models.user import User, UserCreate, UserUpdate
from dependencies import get_current_user, get_mysql, get_kafka
from database.kafka_topics import KafkaTopic
import aiomysql
from utils.response import response_util

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[User])
async def get_users(
        skip: int = 0,
        limit: int = 10,
        cursor: aiomysql.Cursor = Depends(get_mysql)
):
    """获取用户列表"""
    try:
        await cursor.execute(
            "SELECT id, name, email, is_active, created_at, updated_at FROM users LIMIT %s OFFSET %s",
            (limit, skip)
        )
        users = await cursor.fetchall()
        user_list = [dict(user) for user in users]
    except Exception as e:
        return response_util.error(f"获取用户列表失败: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response_util.success(user_list, "获取用户列表成功", status.HTTP_200_OK)


@router.get("/{user_id}", response_model=User)
async def get_user(
        user_id: int,
        cursor: aiomysql.Cursor = Depends(get_mysql)
):
    """根据ID获取用户"""
    await cursor.execute(
        "SELECT id, name, email, is_active, created_at, updated_at FROM users WHERE id = %s",
        (user_id,)
    )
    user = await cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(user)


@router.post("/", response_model=User)
async def create_user(
        user: UserCreate,
        cursor: aiomysql.Cursor = Depends(get_mysql),
        kafka_producer=Depends(get_kafka)
):
    """创建新用户"""
    # 插入用户到MySQL
    await cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
        (user.name, user.email, f"hashed_{user.password}")  # 实际应用中应该使用密码哈希
    )
    user_id = cursor.lastrowid

    # 发送消息到Kafka
    user_data = {
        "user_id": user_id,
        "name": user.name,
        "email": user.email,
        "action": "user_created"
    }

    await kafka_producer.send_message(KafkaTopic.USER_CREATED, user_data)

    # 同时发送审计日志
    audit_log = {
        "event": "user_created",
        "user_id": user_id,
        "timestamp": "2023-01-01T00:00:00Z",  # 实际应用中应该使用当前时间
        "details": f"User {user.name} created with email {user.email}"
    }
    await kafka_producer.send_message(KafkaTopic.AUDIT_LOG, audit_log)

    # 返回创建的用户
    await cursor.execute(
        "SELECT id, name, email, is_active, created_at, updated_at FROM users WHERE id = %s",
        (user_id,)
    )
    new_user = await cursor.fetchone()
    return dict(new_user)