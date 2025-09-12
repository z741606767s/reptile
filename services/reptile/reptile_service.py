import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import random
from config import settings
from database.mysql import mysql_db
from database.kafka_producer import kafka_producer
from database.kafka_topics import KafkaTopic
import logging

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


class ReptileService:
    def __init__(self):
        self.session = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
        ]
        self.active_tasks = {}
        self.task_timeout = 300  # 5分钟超时

    async def init_session(self):
        """初始化aiohttp会话"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.task_timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'User-Agent': random.choice(self.user_agents)
                }
            )
        return self.session

    async def close_session(self):
        """关闭aiohttp会话"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def fetch_url(self, url: str, method: str = "GET", **kwargs) -> Optional[str]:
        """
        获取URL内容

        Args:
            url: 要获取的URL
            method: HTTP方法 (GET, POST等)
            **kwargs: 其他aiohttp请求参数

        Returns:
            网页内容或None
        """
        try:
            session = await self.init_session()

            # 设置默认头
            headers = kwargs.pop('headers', {})
            if 'User-Agent' not in headers:
                headers['User-Agent'] = random.choice(self.user_agents)

            async with session.request(method, url, headers=headers, **kwargs) as response:
                if response.status == 200:
                    content = await response.text()
                    return content
                else:
                    logger.error(f"请求失败: {url}, 状态码: {response.status}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"请求超时: {url}")
            return None
        except Exception as e:
            logger.error(f"请求异常: {url}, 错误: {str(e)}")
            return None

    async def parse_html(self, html_content: str, base_url: str = None) -> Dict[str, Any]:
        """
        解析HTML内容

        Args:
            html_content: HTML内容
            base_url: 基础URL，用于处理相对链接

        Returns:
            解析后的数据字典
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 提取标题
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "无标题"

            # 提取所有链接
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(base_url, href) if base_url else href
                links.append({
                    'text': link.get_text().strip(),
                    'url': absolute_url
                })

            # 提取所有图片
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                absolute_src = urljoin(base_url, src) if base_url else src
                images.append({
                    'alt': img.get('alt', ''),
                    'src': absolute_src
                })

            # 提取正文文本（简单实现）
            paragraphs = [p.get_text().strip() for p in soup.find_all('p')]
            text_content = '\n'.join(paragraphs)

            return {
                'title': title_text,
                'links': links,
                'images': images,
                'text_content': text_content,
                'metadata': self._extract_metadata(soup)
            }
        except Exception as e:
            logger.error(f"解析HTML失败: {str(e)}")
            return {}

    def _extract_metadata(self, soup) -> Dict[str, Any]:
        """提取元数据"""
        metadata = {}

        # 提取meta标签
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                metadata[name] = content

        return metadata

    async def crawl_url(self, url: str, depth: int = 1, max_pages: int = 10000000) -> Dict[str, Any]:
        """
        爬取URL及其链接

        Args:
            url: 起始URL
            depth: 爬取深度
            max_pages: 最大爬取页面数

        Returns:
            爬取结果
        """
        task_id = f"crawl_{hash(url)}_{datetime.now().timestamp()}"
        self.active_tasks[task_id] = {
            'status': 'running',
            'start_time': datetime.now(),
            'url': url
        }

        try:
            visited_urls = set()
            results = []

            # 使用队列进行广度优先爬取
            queue = [(url, 0)]

            while queue and len(visited_urls) < max_pages:
                current_url, current_depth = queue.pop(0)

                if current_url in visited_urls or current_depth > depth:
                    continue

                # 获取页面内容
                html_content = await self.fetch_url(current_url)
                if not html_content:
                    continue

                # 解析页面
                parsed_data = await self.parse_html(html_content, current_url)
                parsed_data['url'] = current_url
                parsed_data['depth'] = current_depth

                # 保存结果
                results.append(parsed_data)
                visited_urls.add(current_url)

                # 发送到Kafka
                await kafka_producer.send_message(
                    KafkaTopic.CRAWL_RESULTS,
                    {
                        'type': 'web_page',
                        'url': current_url,
                        'data': parsed_data,
                        'timestamp': datetime.now().isoformat()
                    }
                )

                # 保存到数据库
                await self.save_crawl_result(current_url, parsed_data)

                # 如果未达到最大深度，将链接加入队列
                if current_depth < depth:
                    for link in parsed_data.get('links', []):
                        link_url = link['url']
                        # 只添加同域的链接
                        if self._is_same_domain(url, link_url) and link_url not in visited_urls:
                            queue.append((link_url, current_depth + 1))

                # 添加随机延迟，避免被封
                await asyncio.sleep(random.uniform(0.5, 2.0))

            # 更新任务状态
            self.active_tasks[task_id]['status'] = 'completed'
            self.active_tasks[task_id]['end_time'] = datetime.now()
            self.active_tasks[task_id]['results'] = len(results)

            return {
                'task_id': task_id,
                'status': 'completed',
                'total_pages': len(results),
                'results': results
            }

        except Exception as e:
            logger.error(f"爬取任务失败: {str(e)}")
            self.active_tasks[task_id]['status'] = 'failed'
            self.active_tasks[task_id]['error'] = str(e)
            self.active_tasks[task_id]['end_time'] = datetime.now()

            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }

    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """检查两个URL是否属于同一域名"""
        try:
            domain1 = urlparse(url1).netloc
            domain2 = urlparse(url2).netloc
            return domain1 == domain2
        except:
            return False

    async def save_crawl_result(self, url: str, data: Dict[str, Any]) -> bool:
        """
        保存爬取结果到数据库

        Args:
            url: 爬取的URL
            data: 爬取的数据

        Returns:
            是否成功保存
        """
        try:
            # 使用正确的数据库连接方式
            async with mysql_db.get_cursor() as cursor:
                # 检查是否已存在
                await cursor.execute(
                    "SELECT id FROM crawl_results WHERE url = %s",
                    (url,)
                )
                existing = await cursor.fetchone()

                if existing:
                    # 更新现有记录
                    await cursor.execute(
                        """UPDATE crawl_results 
                           SET title = %s, content = %s, metadata = %s, updated_at = NOW() 
                           WHERE url = %s""",
                        (data.get('title'),
                         json.dumps(data, ensure_ascii=False),
                         json.dumps(data.get('metadata', {}), ensure_ascii=False),
                         url)
                    )
                else:
                    # 插入新记录
                    await cursor.execute(
                        """INSERT INTO crawl_results 
                           (url, title, content, metadata, created_at, updated_at) 
                           VALUES (%s, %s, %s, %s, NOW(), NOW())""",
                        (url,
                         data.get('title'),
                         json.dumps(data, ensure_ascii=False),
                         json.dumps(data.get('metadata', {}), ensure_ascii=False))
                    )

                return True
        except Exception as e:
            logger.error(f"保存爬取结果失败: {str(e)}")
            return False

    async def get_crawl_result(self, url: str) -> Optional[Dict[str, Any]]:
        """
        从数据库获取爬取结果

        Args:
            url: 要查询的URL

        Returns:
            爬取结果或None
        """
        try:
            # 使用正确的数据库连接方式
            async with mysql_db.get_cursor() as cursor:
                await cursor.execute(
                    "SELECT id, url, title, content, metadata, created_at, updated_at FROM crawl_results WHERE url = %s",
                    (url,)
                )
                result = await cursor.fetchone()

                if result:
                    return {
                        'id': result['id'],
                        'url': result['url'],
                        'title': result['title'],
                        'content': json.loads(result['content']) if result['content'] else {},
                        'metadata': json.loads(result['metadata']) if result['metadata'] else {},
                        'created_at': result['created_at'],
                        'updated_at': result['updated_at']
                    }
                return None
        except Exception as e:
            logger.error(f"获取爬取结果失败: {str(e)}")
            return None

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态或None
        """
        task = self.active_tasks.get(task_id)
        if not task:
            return None

        # 计算任务运行时间
        if 'start_time' in task and 'end_time' in task:
            duration = (task['end_time'] - task['start_time']).total_seconds()
        elif 'start_time' in task:
            duration = (datetime.now() - task['start_time']).total_seconds()
        else:
            duration = 0

        return {
            'task_id': task_id,
            'status': task.get('status', 'unknown'),
            'url': task.get('url'),
            'start_time': task.get('start_time'),
            'end_time': task.get('end_time'),
            'duration': duration,
            'results': task.get('results', 0),
            'error': task.get('error')
        }

    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        清理旧任务

        Args:
            max_age_hours: 最大保留时间（小时）
        """
        now = datetime.now()
        cutoff_time = now - timedelta(hours=max_age_hours)

        tasks_to_remove = []
        for task_id, task in self.active_tasks.items():
            if 'end_time' in task and task['end_time'] < cutoff_time:
                tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self.active_tasks[task_id]

        logger.info(f"清理了 {len(tasks_to_remove)} 个旧任务")

    async def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有任务

        Returns:
            任务列表
        """
        tasks = []
        for task_id in self.active_tasks:
            task_status = await self.get_task_status(task_id)
            if task_status:
                tasks.append(task_status)
        return tasks

    async def stop_task(self, task_id: str) -> bool:
        """
        停止任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功停止
        """
        # 在这个简单实现中，我们只是标记任务为停止
        # 在实际应用中，可能需要更复杂的机制来真正停止正在运行的任务
        if task_id in self.active_tasks:
            self.active_tasks[task_id]['status'] = 'stopped'
            self.active_tasks[task_id]['end_time'] = datetime.now()
            return True
        return False


# 创建全局实例
reptile_service = ReptileService()