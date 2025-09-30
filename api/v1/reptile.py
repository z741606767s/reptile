from fastapi import APIRouter, Query
from config import settings
from services.reptile import reptile_service, duse1_spider
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


@router.post("/crawl/translate")
async def translate(txt: str):
    """翻译文本"""
    try:
        translator = Translate()
        result = await translator.process_text(txt, translate_type="googletrans")
        if not result or result == "Translation failed":
            return response_util.error(message="翻译失败")

        return response_util.success(data=result, message="翻译成功")
    except Exception as e:
        logger.error(f"翻译失败: {str(e)}")
        try:
            translator = Translate()
            result = await translator.process_text(txt, translate_type="mymemory")
            if not result or result == "Translation failed":
                return response_util.error(message="翻译失败")
            return response_util.success(data=result, message="翻译成功")
        except Exception as e:
            return response_util.error(
                message=f"翻译失败: {str(e)}"
            )


@router.post("/crawl/dushe1/run")
async def start_crawl_dushe1():
    """启动爬虫获取首页分类与banned"""
    try:
        result = await duse1_spider.run()
        logger.info(f"爬虫获取首页分类与banned")

        return response_util.success(
            data=result,
            message="爬虫任务成功"
        )
    except Exception as e:
        return response_util.error(
            message=f"爬虫任务失败: {str(e)}"
        )


@router.post("/crawl/dushe1/type")
async def start_crawl_dushe1_type():
    """启动爬虫抓取分类下的类型"""
    try:
        result = await duse1_spider.details_type()
        return response_util.success(
            data=result,
            message="爬虫任务成功"
        )
    except Exception as e:
        return response_util.error(
            message=f"爬虫任务失败: {str(e)}"
        )

@router.post("/crawl/dushe1/drama_list")
async def start_crawl_dushe1_drama_list():
    """启动爬虫抓取分类下的剧列表"""
    try:
        result = await duse1_spider.crawl_drama_list()
        return response_util.success(
            data=result,
            message="爬虫任务成功"
        )
    except Exception as e:
        return response_util.error(
            message=f"爬虫任务失败: {str(e)}"
        )


def traverse_tree(node, depth=0):
    # 打印当前节点的信息，使用缩进表示层级
    indent = "  " * depth
    print(f"{indent}层级 {depth}: {node['name']} - URL: {node.get('url', 'N/A')}")

    # 如果当前节点有子层级，递归遍历每个子节点
    if 'level' in node:
        for child in node['level']:
            traverse_tree(child, depth + 1)

@router.post("/crawl/test")
async def start_crawl_test():
    """启动爬虫获取首页分类与banned"""
    try:
        data = {
'name':'电影',
'level':[
{
'name':'类型',
'url':'/show/1-----1-1.html',
'level':[
{
'name':'剧情',
'url':'/show/1-%E5%89%A7%E6%83%85----1-1.html'
},
{
'name':'喜剧',
'url':'/show/1-%E5%96%9C%E5%89%A7----1-1.html'
},
{
'name':'动作',
'url':'/show/1-%E5%8A%A8%E4%BD%9C----1-1.html'
},
{
'name':'爱情',
'url':'/show/1-%E7%88%B1%E6%83%85----1-1.html'
},
{
'name':'恐怖',
'url':'/show/1-%E6%81%90%E6%80%96----1-1.html'
},
{
'name':'惊悚',
'url':'/show/1-%E6%83%8A%E6%82%9A----1-1.html'
},
{
'name':'犯罪',
'url':'/show/1-%E7%8A%AF%E7%BD%AA----1-1.html'
},
{
'name':'科幻',
'url':'/show/1-%E7%A7%91%E5%B9%BB----1-1.html'
},
{
'name':'悬疑',
'url':'/show/1-%E6%82%AC%E7%96%91----1-1.html'
},
{
'name':'奇幻',
'url':'/show/1-%E5%A5%87%E5%B9%BB----1-1.html'
},
{
'name':'冒险',
'url':'/show/1-%E5%86%92%E9%99%A9----1-1.html'
},
{
'name':'战争',
'url':'/show/1-%E6%88%98%E4%BA%89----1-1.html'
},
{
'name':'历史',
'url':'/show/1-%E5%8E%86%E5%8F%B2----1-1.html'
},
{
'name':'古装',
'url':'/show/1-%E5%8F%A4%E8%A3%85----1-1.html'
},
{
'name':'家庭',
'url':'/show/1-%E5%AE%B6%E5%BA%AD----1-1.html'
},
{
'name':'传记',
'url':'/show/1-%E4%BC%A0%E8%AE%B0----1-1.html'
},
{
'name':'武侠',
'url':'/show/1-%E6%AD%A6%E4%BE%A0----1-1.html'
},
{
'name':'歌舞',
'url':'/show/1-%E6%AD%8C%E8%88%9E----1-1.html'
},
{
'name':'短片',
'url':'/show/1-%E7%9F%AD%E7%89%87----1-1.html'
},
{
'name':'动画',
'url':'/show/1-%E5%8A%A8%E7%94%BB----1-1.html'
},
{
'name':'儿童',
'url':'/show/1-%E5%84%BF%E7%AB%A5----1-1.html'
},
{
'name':'职场',
'url':'/show/1-%E8%81%8C%E5%9C%BA----1-1.html'
}
]
},
{
'name':'地区',
'url':'/show/1-----1-1.html',
'level':[
{
'name':'大陆',
'url':'/show/1--%E4%B8%AD%E5%9B%BD%E5%A4%A7%E9%99%86---1-1.html'
},
{
'name':'香港',
'url':'/show/1--%E4%B8%AD%E5%9B%BD%E9%A6%99%E6%B8%AF---1-1.html'
},
{
'name':'台湾',
'url':'/show/1--%E4%B8%AD%E5%9B%BD%E5%8F%B0%E6%B9%BE---1-1.html'
},
{
'name':'美国',
'url':'/show/1--%E7%BE%8E%E5%9B%BD---1-1.html'
},
{
'name':'日本',
'url':'/show/1--%E6%97%A5%E6%9C%AC---1-1.html'
},
{
'name':'韩国',
'url':'/show/1--%E9%9F%A9%E5%9B%BD---1-1.html'
},
{
'name':'英国',
'url':'/show/1--%E8%8B%B1%E5%9B%BD---1-1.html'
},
{
'name':'法国',
'url':'/show/1--%E6%B3%95%E5%9B%BD---1-1.html'
},
{
'name':'德国',
'url':'/show/1--%E5%BE%B7%E5%9B%BD---1-1.html'
},
{
'name':'印度',
'url':'/show/1--%E5%8D%B0%E5%BA%A6---1-1.html'
},
{
'name':'泰国',
'url':'/show/1--%E6%B3%B0%E5%9B%BD---1-1.html'
},
{
'name':'丹麦',
'url':'/show/1--%E4%B8%B9%E9%BA%A6---1-1.html'
},
{
'name':'瑞典',
'url':'/show/1--%E7%91%9E%E5%85%B8---1-1.html'
},
{
'name':'巴西',
'url':'/show/1--%E5%B7%B4%E8%A5%BF---1-1.html'
},
{
'name':'加拿大',
'url':'/show/1--%E5%8A%A0%E6%8B%BF%E5%A4%A7---1-1.html'
},
{
'name':'俄罗斯',
'url':'/show/1--%E4%BF%84%E7%BD%97%E6%96%AF---1-1.html'
},
{
'name':'意大利',
'url':'/show/1--%E6%84%8F%E5%A4%A7%E5%88%A9---1-1.html'
},
{
'name':'比利时',
'url':'/show/1--%E6%AF%94%E5%88%A9%E6%97%B6---1-1.html'
},
{
'name':'爱尔兰',
'url':'/show/1--%E7%88%B1%E5%B0%94%E5%85%B0---1-1.html'
},
{
'name':'西班牙',
'url':'/show/1--%E8%A5%BF%E7%8F%AD%E7%89%99---1-1.html'
},
{
'name':'澳大利亚',
'url':'/show/1--%E6%BE%B3%E5%A4%A7%E5%88%A9%E4%BA%9A---1-1.html'
},
{
'name':'其他',
'url':'/show/1--%E5%85%B6%E4%BB%96---1-1.html'
}
]
},
{
'name':'语言',
'url':'/show/1-----1-1.html',
'level':[
{
'name':'国语',
'url':'/show/1---%E5%9B%BD%E8%AF%AD--1-1.html'
},
{
'name':'粤语',
'url':'/show/1---%E7%B2%A4%E8%AF%AD--1-1.html'
},
{
'name':'英语',
'url':'/show/1---%E8%8B%B1%E8%AF%AD--1-1.html'
},
{
'name':'日语',
'url':'/show/1---%E6%97%A5%E8%AF%AD--1-1.html'
},
{
'name':'韩语',
'url':'/show/1---%E9%9F%A9%E8%AF%AD--1-1.html'
},
{
'name':'法语',
'url':'/show/1---%E6%B3%95%E8%AF%AD--1-1.html'
},
{
'name':'其他',
'url':'/show/1---%E5%85%B6%E4%BB%96--1-1.html'
}
]
},
{
'name':'年份',
'url':'/show/1-----1-1.html',
'level':[
{
'name':'2025',
'url':'/show/1----2025-1-1.html'
},
{
'name':'2024',
'url':'/show/1----2024-1-1.html'
},
{
'name':'2023',
'url':'/show/1----2023-1-1.html'
},
{
'name':'2022',
'url':'/show/1----2022-1-1.html'
},
{
'name':'2021',
'url':'/show/1----2021-1-1.html'
},
{
'name':'2020',
'url':'/show/1----2020-1-1.html'
},
{
'name':'10年代',
'url':'/show/1----2010_2019-1-1.html'
},
{
'name':'00年代',
'url':'/show/1----2000_2009-1-1.html'
},
{
'name':'90年代',
'url':'/show/1----1990_1999-1-1.html'
},
{
'name':'80年代',
'url':'/show/1----1980_1989-1-1.html'
},
{
'name':'更早',
'url':'/show/1----0_1979-1-1.html'
}
]
},
{
'name':'排序',
'url':'/show/1-----1-1.html',
'level':[
{
'name':'最新',
'url':'/show/1-----2-1.html'
},
{
'name':'最热',
'url':'/show/1-----3-1.html'
},
{
'name':'评分',
'url':'/show/1-----4-1.html'
}
]
}
]
}

        traverse_tree(data)

        return response_util.success(
            data=data,
            message="爬虫任务成功"
        )
    except Exception as e:
        return response_util.error(
            message=f"爬虫任务失败: {str(e)}"
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
