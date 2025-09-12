from fastapi import APIRouter, HTTPException, Query
from config import settings
from services.reptile import ReptileService, reptile_service
from services.translate import Translate
from utils.response import response_util
import logging

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/crawl")
async def start_crawl(url: str = Query(...), depth: int = 1, max_pages: int = 10000000):
    """启动爬虫任务"""
    try:
        result = await reptile_service.crawl_url(url, depth, max_pages)
        logger.info(f"爬虫任务已启动，任务ID: {result['task_id']}，URL: {url}，深度: {depth}，最大页面数: {max_pages}")

        return response_util.success(
            data=result,
            message="爬虫任务已启动"
        )
    except Exception as e:
        return response_util.error(
            message=f"启动爬虫任务失败: {str(e)}"
        )


@router.get("/crawl/results")
async def get_crawl_result(url: str = Query(...)):
    """获取爬取结果"""
    try:
        result = await reptile_service.get_crawl_result(url)
        if not result:
            return response_util.not_found("未找到爬取结果")

        return response_util.success(data=result)
    except Exception as e:
        return response_util.error(
            message=f"获取爬取结果失败: {str(e)}"
        )


@router.get("/crawl/{task_id}")
async def get_crawl_status(task_id: str):
    """获取爬虫任务状态"""
    try:
        status = await reptile_service.get_task_status(task_id)
        if not status:
            return response_util.not_found("任务不存在")

        return response_util.success(data=status)
    except Exception as e:
        return response_util.error(
            message=f"获取任务状态失败: {str(e)}"
        )


@router.get("/crawl/tasks")
async def get_all_tasks():
    """获取所有任务"""
    try:
        tasks = await reptile_service.get_all_tasks()
        return response_util.success(data=tasks)
    except Exception as e:
        return response_util.error(
            message=f"获取任务列表失败: {str(e)}"
        )


@router.post("/crawl/{task_id}/stop")
async def stop_crawl_task(task_id: str):
    """停止爬虫任务"""
    try:
        success = await reptile_service.stop_task(task_id)
        if not success:
            return response_util.not_found("任务不存在")

        return response_util.success(message="任务已停止")
    except Exception as e:
        return response_util.error(
            message=f"停止任务失败: {str(e)}"
        )

@router.post("/crawl/translate")
async def translate(txt: str):
    """翻译文本"""
    try:
        translator = Translate()
        result  = await translator.process_text(txt, translate_type="googletrans")
        if not result or result == "Translation failed":
            return response_util.error(message="翻译失败")

        return response_util.success(data=result, message="翻译成功")
    except Exception as e:
        return response_util.error(
            message=f"翻译失败: {str(e)}"
        )
