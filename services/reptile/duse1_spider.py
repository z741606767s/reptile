import asyncio
import hashlib
import os
import aiofiles
import aiohttp
import logging
from typing import Dict, List, Optional, Any, Coroutine
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
from models import CategoryModel
from services.category import category_service
from services.translate import Translate
from utils.tool.tools import get_left_part_of_valid_url

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
        self.base_img_url = "https://vres.cfaqcgj.com"
        self.categories = []  # 存储分类信息
        self.banners = []  # 存储banner信息
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

    async def get_home_html(self) -> List[Dict[str, str]]:
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

        try:
            # 处理分类信息
            categories = await self.get_categories(soup)

            # 处理banner信息
            await self.get_banners(soup)
            return categories
        except Exception as e:
            logger.error(f"完整首页内容处理失败: {str(e)}")
            return []

    async def get_category_html(self, category_url: str) -> List[Dict[str, str]]:
        """爬取分类页信息"""
        logger.info("开始获取网站分类信息")
        html_content = await self.fetch_url(category_url)
        if not html_content:
            logger.error("获取分类内容失败")
            return []

        soup = BeautifulSoup(html_content, 'html.parser')
        categories = []

        try:
            # 获取所有filter-row元素
            filter_rows = soup.select('.filter-box .filter-row')

            for row in filter_rows:
                # 获取filter-row-side中的strong标签
                side_div = row.select_one('.filter-row-side')
                if not side_div:
                    continue

                strong_tag = side_div.find('strong')
                if not strong_tag:
                    continue

                # 排除包含"排序"的filter-row
                # if '排序' in strong_tag.get_text():
                #     continue

                # 获取level2分类名称
                level2_name = strong_tag.get_text().strip().replace(':', '').replace('：', '')
                category = {
                    'name': level2_name,
                    'url': '',
                    'level': []
                }

                # 获取对应的filter-row-main(level2)中的level3分类
                main_div = row.select_one('.filter-row-main')
                if not main_div:
                    categories.append(category)
                    continue

                # 获取所有filter-item链接
                filter_items = main_div.select('.filter-item')
                for item in filter_items:
                    name = item.get_text().strip()
                    url = item.get('href', '')

                    if name in ['全部', '类型', '综合']:
                        category['url'] = url
                    else:
                        # 确保level3字段是列表类型
                        if not isinstance(category['level'], list):
                            category['level'] = []

                        # 添加到结果列表
                        category['level'].append({
                            'name': name,
                            'url': url
                        })
                # 添加到结果列表
                categories.append(category)

            return categories
        except Exception as e:
            logger.error(f"爬取类型失败: {str(e)}")
            return []

    async def get_categories(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        categories = []

        # 根据网站实际结构查找分类链接
        # 这里需要根据实际网站结构调整选择器
        nav_elements = soup.select('.main .menu-item a')

        # 初始化翻译
        translator = Translate()

        for element in nav_elements:
            href = element.get('href', '')
            text = element.get_text().strip()

            # 获取类名
            name_element = element.select_one('.menu-item-label')
            name = name_element.get_text().strip() if name_element else ''

            # 类名翻译转换slug
            slug = await translator.process_text(name, translate_type="googletrans")
            if not slug or slug == "Translation failed":
                logger.error("googletrans 翻译失败")
                return []

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
                        'name': name,
                        'slug': slug,
                        'parent_id': 0,  # 顶级
                        'level': 1,
                        'site': self.base_url,
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

    async def get_banners(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        banners = []

        # 查找轮播图元素
        carousel_items = soup.select('.swiper-slide .carousel-item')

        # 收集所有需要下载的图片URL
        download_tasks = []

        for item in carousel_items:
            text = item.get_text().strip()

            # 获取图片URL
            img_element = item.select_one('.carousel-item-cover img')
            img_url = img_element.get('data-original', '') if img_element else ''
            if not img_url:
                img_url = img_element.get('src', '') if img_element else ''

            # 转换为绝对URL
            full_img_url = urljoin(self.base_img_url, img_url) if img_url else ''

            # 获取标题
            title_element = item.select_one('.carousel-item-title')
            title = title_element.get_text().strip() if title_element else ''

            # 获取标签
            tags = []
            tag_elements = item.select('.carousel-item-tags .tag')
            for tag in tag_elements:
                tag_text = tag.get_text().strip()
                if tag_text:
                    tags.append(tag_text)

            # 获取描述
            desc_element = item.select_one('.carousel-item-desc')
            desc = desc_element.get_text().strip() if desc_element else ''

            # 生成本地路径（即使图片尚未下载）
            # local_img_path = ""
            # if full_img_url:
            #     try:
            #         # 生成唯一的本地文件名
            #         local_img_path = await self.generate_local_path(full_img_url, 'banners')
            #     except Exception as e:
            #         logger.error(f"生成本地路径失败: {full_img_url}, 错误: {str(e)}")
            #         local_img_path = full_img_url  # 如果生成失败，使用原始URL

            banner = {
                'banner_url': full_img_url,  # 直接使用本地路径
                'original_url': full_img_url,  # 保留原始URL用于下载
                'title': title,
                'tag_names': "/ ".join(tags),
                'desc': desc,
                'jump_url': "",
                'jump_method': "",
                'download_status': 'pending' if full_img_url else 'skipped',  # 下载状态
            }

            # 避免重复添加
            if not any(c['banner_url'] == full_img_url for c in banners):
                banners.append(banner)
                logger.info(f"发现banner: {text} -> {full_img_url}")

                # 如果有图片URL，添加到下载任务
                # if full_img_url:
                #     download_tasks.append((full_img_url, len(banners) - 1))  # 使用当前索引

        # 异步并发下载所有图片
        # if download_tasks:
        #     await self.download_images_async(download_tasks, banners)

        self.banners = banners
        logger.info(f"共找到 {len(banners)} 个banner")

        # 保存分类信息到数据库
        await self.save_banners(banners)

        return banners

    async def generate_local_path(self, image_url: str, path_name: str) -> str:
        """
        生成本地存储路径
        Args:
            image_url: 图片URL
            path_name: 路径
        Returns:
            本地图片路径
        """
        # 创建public目录（如果不存在）
        public_dir = os.path.join(os.getcwd(), 'public')
        images_dir = os.path.join(public_dir, 'images', path_name)

        if not os.path.exists(images_dir):
            os.makedirs(images_dir, exist_ok=True)

        # 从URL中提取文件名
        parsed_url = urlparse(image_url)
        filename = os.path.basename(parsed_url.path)

        # 如果没有文件名或文件名无效，使用URL的MD5哈希
        if not filename or '.' not in filename:
            url_hash = hashlib.md5(image_url.encode()).hexdigest()
            filename = f"{url_hash}.jpg"
        else:
            # 确保文件名安全
            filename = re.sub(r'[^\w\-_.]', '_', filename)

        return f"/images/{path_name}/{filename}"

    async def download_images_async(self, download_tasks: List[tuple], banners: List[Dict[str, Any]]):
        """
        异步并发下载所有图片

        Args:
            download_tasks: 包含(图片URL, banner索引)的元组列表
            banners: banner列表，用于更新下载状态
        """
        # 创建所有下载任务的协程
        tasks = []
        for img_url, banner_idx in download_tasks:
            # 检查索引是否有效
            if banner_idx < 0 or banner_idx >= len(banners):
                logger.error(f"无效的banner索引: {banner_idx}, 列表长度: {len(banners)}")
                continue

            task = self.download_single_image(img_url, banner_idx, banners)
            tasks.append(task)

        # 并发执行所有下载任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理下载结果
        for i, result in enumerate(results):
            if i < len(download_tasks):  # 确保索引有效
                img_url, banner_idx = download_tasks[i]
                if isinstance(result, Exception):
                    logger.error(f"图片下载失败: {img_url}, 错误: {str(result)}")
                    if banner_idx < len(banners):  # 再次检查索引有效性
                        banners[banner_idx]['download_status'] = 'failed'
                else:
                    if banner_idx < len(banners):  # 再次检查索引有效性
                        banners[banner_idx]['download_status'] = 'success'

    async def download_single_image(self, image_url: str, banner_idx: int, banners: List[Dict[str, Any]]):
        """
        下载单个图片到预先生成的本地路径

        Args:
            image_url: 图片URL
            banner_idx: banner在列表中的索引
            banners: banner列表
        """
        # 检查索引是否有效
        if banner_idx < 0 or banner_idx >= len(banners):
            logger.error(f"无效的banner索引: {banner_idx}, 列表长度: {len(banners)}")
            return

        try:
            # 获取banner对象
            banner = banners[banner_idx]
            local_path = banner['banner_url']

            # 如果本地路径不是以/images/开头，说明不是本地路径，跳过下载
            if not local_path.startswith('/images/'):
                logger.debug(f"跳过下载，使用原始URL: {image_url}")
                return

            # 生成完整本地路径
            full_local_path = os.path.join(os.getcwd(), 'public', local_path.lstrip('/'))

            # 如果文件已存在，直接返回
            if os.path.exists(full_local_path):
                logger.debug(f"图片已存在: {full_local_path}")
                return

            # 确保目录存在
            os.makedirs(os.path.dirname(full_local_path), exist_ok=True)

            # 异步下载图片
            session = await self.init_session()

            # 设置更长的超时时间
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_connect=10, sock_read=10)

            # 添加Referer头，模拟从原始网站发起的请求
            headers = {
                'Referer': self.base_img_url,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }

            async with session.get(image_url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    # 异步写入文件
                    async with aiofiles.open(full_local_path, 'wb') as f:
                        await f.write(await response.read())

                    logger.info(f"图片下载成功: {image_url} -> {full_local_path}")
                else:
                    logger.error(f"下载图片失败: {image_url}, 状态码: {response.status}")
                    # 如果下载失败，将banner_url恢复为原始URL
                    banners[banner_idx]['banner_url'] = image_url
                    raise Exception(f"HTTP状态码: {response.status}")
        except asyncio.TimeoutError:
            logger.error(f"下载图片超时: {image_url}")
            # 如果下载超时，将banner_url恢复为原始URL
            banners[banner_idx]['banner_url'] = image_url
            raise Exception(f"下载超时")
        except aiohttp.ClientError as e:
            logger.error(f"下载图片网络错误: {image_url}, 错误: {str(e)}")
            # 如果网络错误，将banner_url恢复为原始URL
            banners[banner_idx]['banner_url'] = image_url
            raise
        except Exception as e:
            logger.error(f"下载图片异常: {image_url}, 错误: {str(e)}")
            # 如果下载失败，将banner_url恢复为原始URL
            banners[banner_idx]['banner_url'] = image_url
            raise

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
        保存分类信息到数据库（支持已存在则更新）
        Args:
            categories: 分类列表
        Returns:
            是否成功保存
        """
        sql = """
            INSERT INTO r_category
                (name, slug, parent_id, level, sort, site, url, href, created_at, updated_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
                name       = VALUES(name),
                parent_id  = VALUES(parent_id),
                level      = VALUES(level),
                sort       = VALUEs(sort),
                url        = VALUES(url),
                href       = VALUES(href),
                updated_at = NOW();
            """
        success_count = 0
        try:
            async with mysql_db.get_connection() as conn:
                async with conn.cursor() as cursor:
                    for index, category in enumerate(categories):
                        try:
                            await cursor.execute(sql, (
                                category['name'],
                                category.get('slug', ''),
                                category.get('parent_id', 0),
                                category.get('level', 1),
                                index + 1,
                                category.get('site', self.base_url),
                                category['url'],
                                category.get('href', '')
                            ))
                            success_count += 1
                            logger.debug(f"成功插入/更新分类: {category['name']}")
                        except Exception as e:
                            logger.error(f"插入分类失败: {category['name']}, 错误: {str(e)}")

                    # 显式提交事务
                    await conn.commit()

            logger.info(f"分类保存完成，成功处理 {success_count}/{len(categories)} 条记录")
            return success_count > 0
        except Exception as e:
            logger.error(f"保存分类信息失败: {str(e)}")
            return False

    async def save_banners(self, banners: List[Dict[str, str]]) -> bool:
        """
        保存分类信息到数据库（支持已存在则更新）
        Args:
            banners: banner列表
        Returns:
            是否成功保存
        """
        sql = """
            INSERT INTO r_drama_banner
                (banner_url, title, tag_names, `desc`, jump_url, jump_method, sort, created_at, updated_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW());
            """
        success_count = 0
        try:
            async with mysql_db.get_connection() as conn:
                async with conn.cursor() as cursor:
                    for index, banner in enumerate(banners):
                        try:
                            await cursor.execute(sql, (
                                banner['banner_url'],
                                banner['title'],
                                banner.get('tag_names', ''),
                                banner.get('desc', ''),
                                banner.get('jump_url', ''),
                                banner.get('jump_method', ''),
                                index + 1
                            ))
                            success_count += 1
                            logger.debug(f"成功插入banner: {banner['title']}")
                        except Exception as e:
                            logger.error(f"插入banner失败: {banner['title']}, 错误: {str(e)}")

                    # 显式提交事务
                    await conn.commit()

            logger.info(f"Banner保存完成，成功处理 {success_count}/{len(banners)} 条记录")
            return success_count > 0
        except Exception as e:
            logger.error(f"保存banner信息失败: {str(e)}")
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
            categories = await self.get_home_html()

            if not categories:
                logger.error("未找到任何分类，爬虫停止")
                return

            # 爬取每个分类
            # all_details = []
            # for category in categories:
            #     details = await self.crawl_category_list(category)
            #     all_details.extend(details)
            #
            #     # 分类间延迟
            #     await asyncio.sleep(random.uniform(2, 5))
            #
            # logger.info(f"爬虫完成，共爬取 {len(all_details)} 个详情页")

        except Exception as e:
            logger.error(f"爬虫运行异常: {str(e)}")
        finally:
            await self.close_session()

    async def details_type(self):
        """抓取子分类"""
        try:
            # 数据库获取顶级分类列表
            top_level_categories = await category_service.get_multi()
            if not top_level_categories:
                logger.error("未找到任何分类，爬虫停止")
                return []

            all_subcategories = []
            for category in top_level_categories:
                # 过滤无效url
                categorie_url = category.url
                if not categorie_url:
                    continue

                logger.info(f"开始爬取: {category.name}")
                subcategories = await self.get_category_html(categorie_url)
                if not subcategories:
                    continue

                category_data = {
                    'name': category.name,
                    'level': subcategories,
                }
                all_subcategories.append(category_data)

                # 发送到Kafka
                await kafka_producer.send_message(
                    KafkaTopic.CRAWL_LEVEL_RESULTS,
                    {
                        'type': 'detail_page',
                        'url': self.base_url,
                        'data': category_data,
                        'timestamp': datetime.now().isoformat()
                    }
                )

                # 直接入库
                # await category_service.save_category_level(category_data)

                logger.info(f"爬取: {category.name} 结束")

            return all_subcategories
        except Exception as e:
            logger.error(f"爬虫运行异常: {str(e)}")
            return []
        finally:
            await self.close_session()

    async def crawl_drama_list(self):
        """
        爬取分类下的剧列表数据
        """
        # 用于记录已爬取的分类URL，避免重复请求
        crawled_urls = set()

        # 获取分类列表
        categories = await category_service.get_by_parent_id(parent_id=197)
        if not categories:
            logger.error("未找到任何分类，爬虫停止")
            return

        # 爬取每个分类下的剧列表
        drama_lists = []
        for category in categories:
            # 检查当前URL是否已爬取过
            if category.url in crawled_urls:
                logger.info(f"URL {category.url} 已爬取过，将跳过")
                continue

            logger.info(f"开始爬取分类: {category.name}")
            drama_list = await self.get_category_drama_list(category.url)
            if not drama_list:
                continue
            drama_lists.append(drama_list)

            # 发送到Kafka
            await kafka_producer.send_message(
                KafkaTopic.CRAWL_DRAMA_LIST,
                {
                    'type': 'crawl_drama_list',
                    'url': self.base_url,
                    'category_id': category.id,
                    'category_name': category.name,
                    'data': drama_list,
                    'timestamp': datetime.now().isoformat()
                }
            )

            # 将已处理的URL加入集合
            crawled_urls.add(category.url)

            logger.info(f"爬取分类: {category.name} 结束")
        return drama_lists

    async def get_category_drama_list(self, category_url: str) -> List[Dict[str, str]]:
        """获取分类下的剧列表"""
        url = get_left_part_of_valid_url(category_url)
        logging.info(f"分类URL: {category_url}，url: {url}")
        if not url:
            drama_list = await self.get_category_drama_list_html(category_url)
            return drama_list
        else:
            drama_list = []
            for i in range(20):
                drama_list_page = await self.get_category_drama_list_html(f"{url}{i+1}.html")
                if not drama_list_page:
                    continue
                drama_list.extend(drama_list_page)
            return drama_list


    async def get_category_drama_list_html(self, category_url: str) -> List[Dict[str, str]]:
        """爬取分类页信息"""
        logger.info(f"开始获取分类: {category_url} 下的剧列表信息")
        html_content = await self.fetch_url(category_url)
        if not html_content:
            logger.error("获取分类内容失败")
            return []

        soup = BeautifulSoup(html_content, 'html.parser')

        try:
            # 找到所有的module-item
            module_items = soup.find_all('div', class_='module-item')

            # 若不存在module-item标签，直接返回空列表
            if not module_items:
                logger.info(f"分类: {category_url} 下未找到module-item标签，无需提取数据")
                return []

            # 存储提取的信息
            results = []

            for item in module_items:
                # 提取链接
                link_tag = item.find('a', class_='v-item')
                link = link_tag['href'] if link_tag else ''

                # 提取标题
                title_tag = item.find('div', class_='v-item-footer').find('div', class_='v-item-title', style=None)
                title = title_tag.get_text(strip=True) if title_tag else ''

                # 提取封面图片URL（data-original属性）
                img_tag = item.find('div', class_='v-item-cover').find_all('img')[1]  # 第二个img是实际封面
                img_url = img_tag.get('data-original', '') if img_tag else ''

                # 提取集数信息
                episode_tag = item.find('div', class_='v-item-bottom').find('span')
                episode = episode_tag.get_text(strip=True) if episode_tag else ''

                # 存储到结果列表
                results.append({
                    'title': title,
                    'link': self.base_url + link,
                    'image_url': self.base_img_url + img_url,
                    'episode': episode
                })

            return results
        except Exception as e:
            logger.error(f"爬取分类: {category_url} 下的剧列表失败: {str(e)}")
            return []

# 创建全局实例
duse1_spider = Duse1Spider()
