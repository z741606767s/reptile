import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import random
import re
from config import settings
from database.mysql import mysql_db
from database.kafka_producer import kafka_producer
from database.kafka_topics import KafkaTopic

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


class Duse1Spider:
    def __init__(self):
        self.session = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
        ]
        self.base_url = "https://www.duse1.com"
        self.categories = []  # 存储分类信息
        self.visited_urls = set()  # 已访问的URL集合
        self.task_timeout = 300  # 5分钟超时

    async def init_session(self):
        """初始化aiohttp会话"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.task_timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'User-Agent': random.choice(self.user_agents),
                    'Referer': self.base_url,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
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

    async def get_categories(self) -> List[Dict[str, str]]:
        """
        获取网站分类信息

        Returns:
            分类信息列表
        """
        logger.info("开始获取网站分类信息")
        html_content = await self.fetch_url(self.base_url)
        if not html_content:
            logger.error("获取首页内容失败")
            return []

        soup = BeautifulSoup(html_content, 'html.parser')
        categories = []

        # 根据网站实际结构查找分类链接
        # 这里需要根据实际网站结构调整选择器
        nav_elements = soup.select('.main .menu-item a')

        for element in nav_elements:
            href = element.get('href', '')
            text = element.get_text().strip()

            # 过滤无效链接和非分类链接
            if (href and href != '#' and href != '/' and
                    not href.startswith('javascript:') and
                    not href.startswith('mailto:') and
                    not href.startswith('tel:') and
                    text and len(text) > 1):

                # 转换为绝对URL
                full_url = urljoin(self.base_url, href)

                # 检查是否是本站链接
                if self._is_same_domain(self.base_url, full_url):
                    category = {
                        'name': text,
                        'url': full_url,
                        'href': href
                    }

                    # 避免重复添加
                    if not any(c['url'] == full_url for c in categories):
                        categories.append(category)
                        logger.info(f"发现分类: {text} -> {full_url}")

        self.categories = categories
        logger.info(f"共找到 {len(categories)} 个分类")

        # 保存分类信息到数据库
        await self.save_categories(categories)

        return categories

    async def crawl_category_list(self, category: Dict[str, str], max_pages: int = 10) -> List[Dict[str, Any]]:
        """
        爬取分类下的列表页

        Args:
            category: 分类信息
            max_pages: 最大爬取页数

        Returns:
            列表页内容
        """
        logger.info(f"开始爬取分类: {category['name']}")
        list_items = []
        page = 1

        while page <= max_pages:
            # 构建分页URL（根据网站实际结构调整）
            if page == 1:
                list_url = category['url']
            else:
                # 根据网站分页规则构建URL
                list_url = f"{category['url']}?page={page}"  # 或者 /page/2 等形式

            # 检查是否已访问过
            if list_url in self.visited_urls:
                logger.info(f"已访问过: {list_url}, 跳过")
                page += 1
                continue

            logger.info(f"爬取列表页: {list_url}")
            html_content = await self.fetch_url(list_url)

            if not html_content:
                logger.error(f"获取列表页失败: {list_url}")
                break

            self.visited_urls.add(list_url)

            # 解析列表页获取详情页链接
            soup = BeautifulSoup(html_content, 'html.parser')

            # 根据网站实际结构调整选择器
            item_links = soup.select('.post a, .item a, .title a, .list-item a, article a')

            detail_urls = []
            for link in item_links:
                href = link.get('href', '')
                if href and not href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    full_url = urljoin(self.base_url, href)
                    if (self._is_same_domain(self.base_url, full_url) and
                            full_url not in self.visited_urls and
                            not any(x in full_url for x in ['/page/', '/category/', '/tag/', '/author/'])):
                        detail_urls.append(full_url)

            logger.info(f"从列表页 {list_url} 中找到 {len(detail_urls)} 个详情页链接")

            # 爬取每个详情页
            for detail_url in detail_urls:
                if detail_url not in self.visited_urls:
                    detail_data = await self.crawl_detail_page(detail_url)
                    if detail_data:
                        list_items.append(detail_data)

                    # 添加随机延迟，避免被封
                    await asyncio.sleep(random.uniform(1, 3))

            # 检查是否有下一页
            next_page = soup.select_one('.next, .next-page, a[rel="next"]')
            if next_page and page < max_pages:
                page += 1
            else:
                break

        logger.info(f"分类 {category['name']} 爬取完成，共获取 {len(list_items)} 个详情页")
        return list_items

    async def crawl_detail_page(self, url: str) -> Optional[Dict[str, Any]]:
        """
        爬取详情页内容

        Args:
            url: 详情页URL

        Returns:
            详情页数据
        """
        logger.info(f"爬取详情页: {url}")
        html_content = await self.fetch_url(url)

        if not html_content:
            logger.error(f"获取详情页失败: {url}")
            return None

        self.visited_urls.add(url)
        soup = BeautifulSoup(html_content, 'html.parser')

        # 提取标题
        title_element = soup.select_one('h1, .title, .entry-title, .post-title')
        title = title_element.get_text().strip() if title_element else "无标题"

        # 提取内容
        content_element = soup.select_one('.content, .entry-content, .post-content, .article-content')
        content = content_element.get_text().strip() if content_element else ""

        # 提取参数信息（根据网站实际结构调整）
        params = {}
        param_elements = soup.select('.param, .info, .metadata, .specs, .attributes')

        for elem in param_elements:
            # 尝试提取键值对
            try:
                key = elem.select_one('.key, .label, dt').get_text().strip().replace('：', '').replace(':', '')
                value = elem.select_one('.value, .data, dd').get_text().strip()
                if key and value:
                    params[key] = value
            except:
                # 如果无法提取键值对，则保存整个文本
                text = elem.get_text().strip()
                if text and len(text) < 100:  # 避免过长的文本
                    params[f"param_{len(params)}"] = text

        # 提取播放地址（根据网站实际结构调整）
        play_urls = []

        # 查找视频标签
        video_elements = soup.select('video, audio, iframe, embed, object')
        for elem in video_elements:
            src = elem.get('src') or elem.get('data-src')
            if src:
                full_src = urljoin(self.base_url, src)
                play_urls.append(full_src)

        # 查找包含播放链接的a标签
        play_links = soup.select('a[href*="play"], a[href*="video"], a[href*="embed"], a[onclick*="play"]')
        for link in play_links:
            href = link.get('href', '')
            if href:
                full_href = urljoin(self.base_url, href)
                play_urls.append(full_href)

        # 查找JavaScript中的播放地址
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string:
                # 查找常见的视频URL模式
                url_patterns = [
                    r'(https?://[^\s"\'<>]*?\.(mp4|m3u8|flv|avi|mov|wmv|mkv))',
                    r'(https?://[^\s"\'<>]*?/play[^\s"\'<>]*)',
                    r'(https?://[^\s"\'<>]*?/video[^\s"\'<>]*)'
                ]

                for pattern in url_patterns:
                    matches = re.findall(pattern, script.string, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            url = match[0]
                        else:
                            url = match
                        play_urls.append(url)

        # 去重播放地址
        play_urls = list(set(play_urls))

        # 构建详情数据
        detail_data = {
            'url': url,
            'title': title,
            'content': content,
            'params': params,
            'play_urls': play_urls,
            'crawled_at': datetime.now().isoformat()
        }

        # 保存到数据库
        await self.save_detail_data(detail_data)

        # 发送到Kafka
        await kafka_producer.send_message(
            KafkaTopic.CRAWL_RESULTS,
            {
                'type': 'detail_page',
                'url': url,
                'data': detail_data,
                'timestamp': datetime.now().isoformat()
            }
        )

        logger.info(f"详情页爬取完成: {title}")
        return detail_data

    async def save_categories(self, categories: List[Dict[str, str]]) -> bool:
        """
        保存分类信息到数据库

        Args:
            categories: 分类列表

        Returns:
            是否成功保存
        """
        try:
            async with mysql_db.get_cursor() as cursor:
                # 清空现有分类（根据需求决定是否保留历史分类）
                await cursor.execute("DELETE FROM website_categories WHERE site = %s", (self.base_url,))

                # 插入新分类
                for category in categories:
                    await cursor.execute(
                        """INSERT INTO website_categories 
                           (site, name, url, href, created_at) 
                           VALUES (%s, %s, %s, %s, NOW())""",
                        (self.base_url, category['name'], category['url'], category['href'])
                    )

                return True
        except Exception as e:
            logger.error(f"保存分类信息失败: {str(e)}")
            return False

    async def save_detail_data(self, detail_data: Dict[str, Any]) -> bool:
        """
        保存详情数据到数据库

        Args:
            detail_data: 详情数据

        Returns:
            是否成功保存
        """
        try:
            async with mysql_db.get_cursor() as cursor:
                # 检查是否已存在
                await cursor.execute(
                    "SELECT id FROM content_details WHERE url = %s",
                    (detail_data['url'],)
                )
                existing = await cursor.fetchone()

                if existing:
                    # 更新现有记录
                    await cursor.execute(
                        """UPDATE content_details 
                           SET title = %s, content = %s, params = %s, 
                           play_urls = %s, updated_at = NOW() 
                           WHERE url = %s""",
                        (detail_data['title'],
                         detail_data['content'],
                         json.dumps(detail_data['params'], ensure_ascii=False),
                         json.dumps(detail_data['play_urls'], ensure_ascii=False),
                         detail_data['url'])
                    )
                else:
                    # 插入新记录
                    await cursor.execute(
                        """INSERT INTO content_details 
                           (url, title, content, params, play_urls, site, created_at, updated_at) 
                           VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                        (detail_data['url'],
                         detail_data['title'],
                         detail_data['content'],
                         json.dumps(detail_data['params'], ensure_ascii=False),
                         json.dumps(detail_data['play_urls'], ensure_ascii=False),
                         self.base_url)
                    )

                return True
        except Exception as e:
            logger.error(f"保存详情数据失败: {str(e)}")
            return False

    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """检查两个URL是否属于同一域名"""
        try:
            domain1 = urlparse(url1).netloc
            domain2 = urlparse(url2).netloc
            return domain1 == domain2
        except:
            return False

    async def run(self):
        """
        运行爬虫
        """
        logger.info("开始运行Duse1爬虫")

        try:
            # 获取分类
            categories = await self.get_categories()

            if not categories:
                logger.error("未找到任何分类，爬虫停止")
                return

            # 爬取每个分类
            all_details = []
            for category in categories:
                details = await self.crawl_category_list(category)
                all_details.extend(details)

                # 分类间延迟
                await asyncio.sleep(random.uniform(2, 5))

            logger.info(f"爬虫完成，共爬取 {len(all_details)} 个详情页")

        except Exception as e:
            logger.error(f"爬虫运行异常: {str(e)}")
        finally:
            await self.close_session()


# 创建全局实例
duse1_spider = Duse1Spider()