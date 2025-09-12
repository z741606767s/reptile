from fastapi import APIRouter
from utils.response.response import response_util

router = APIRouter()

@router.get("/reptile_url")
async def start_reptile(url: str):
    """启动爬虫"""
    return response_util.success(data={"url": url})
