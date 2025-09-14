from datetime import datetime
from typing import List, Optional, Dict, Any
from config import settings
from database.mysql import mysql_db
from models import CategoryModel
from schemas import CategoryCreate, CategoryUpdate
import logging
from services.translate import Translate

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


class CategoryService(object):
    """分类CRUD操作"""

    @staticmethod
    async def get(category_id: int) -> Optional[CategoryModel]:
        """根据ID获取分类"""
        try:
            query = "SELECT * FROM r_category WHERE id = %s"
            result = await mysql_db.fetch_one(query, (category_id,))
            return CategoryModel(**result) if result else None
        except Exception as e:
            logger.error(f"获取分类失败: {e}")
            return None

    @staticmethod
    async def get_category_by_name(name: str) -> Optional[CategoryModel]:
        """根据ID获取分类"""
        try:
            query = "SELECT * FROM r_category WHERE name = %s limit 1"
            result = await mysql_db.fetch_one(query, (name,))
            return CategoryModel(**result) if result else None
        except Exception as e:
            logger.error(f"获取分类失败: {e}")
            return None

    @staticmethod
    async def get_multi(
            skip: int = 0,
            limit: int = 100,
            site: Optional[str] = None,
            is_enabled: Optional[bool] = None,
            parent_id: Optional[int] = None
    ) -> List[CategoryModel]:
        """获取分类列表"""
        try:
            query = "SELECT * FROM r_category"
            conditions = []
            params = []

            if site:
                conditions.append("site = %s")
                params.append(site)

            if is_enabled is not None:
                conditions.append("is_enabled = %s")
                params.append(is_enabled)

            if parent_id is not None:
                conditions.append("parent_id = %s")
                params.append(parent_id)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY sort ASC, id ASC LIMIT %s OFFSET %s"
            params.extend([limit, skip])

            results = await mysql_db.fetch_all(query, params)
            return [CategoryModel(**result) for result in results]
        except Exception as e:
            logger.error(f"获取分类列表失败: {e}")
            return []

    @staticmethod
    async def get_by_slug(slug: str, parent_id: Optional[int], site: str) -> Optional[CategoryModel]:
        """根据slug、parent_id和site获取分类"""
        try:
            if parent_id is None:
                query = "SELECT * FROM r_category WHERE slug = %s AND parent_id IS NULL AND site = %s"
                params = [slug, site]
            else:
                query = "SELECT * FROM r_category WHERE slug = %s AND parent_id = %s AND site = %s"
                params = [slug, parent_id, site]

            result = await mysql_db.fetch_one(query, params)
            return CategoryModel(**result) if result else None
        except Exception as e:
            logger.error(f"根据slug获取分类失败: {e}")
            return None

    @staticmethod
    async def create(category: CategoryCreate) -> Optional[CategoryModel]:
        """创建分类"""
        try:
            # 检查slug是否在同级唯一
            existing = await CategoryService.get_by_slug(category.slug, category.parent_id, category.site)
            if existing:
                return None

            # 计算路径和URI路径
            path = None
            uri_path = category.slug
            level = 1

            if category.parent_id:
                parent = await CategoryService.get(category.parent_id)
                if parent:
                    path = f"{parent.path},{parent.id}" if parent.path else str(parent.id)
                    uri_path = f"{parent.uri_path}/{category.slug}" if parent.uri_path else category.slug
                    level = parent.level + 1

            # 获取当前时间
            current_time = datetime.now()

            # 构建插入数据
            data = category.dict()
            data.update({
                "path": path,
                "uri_path": uri_path,
                "level": level,
                "created_at": current_time,  # 添加创建时间
                "updated_at": current_time  # 添加更新时间
            })

            # 执行插入
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            query = f"INSERT INTO r_category ({columns}) VALUES ({placeholders})"

            category_id = await mysql_db.execute(query, tuple(data.values()))

            # 获取新创建的分类
            return await CategoryService.get(category_id)
        except Exception as e:
            logger.error(f"创建分类失败: {e}")
            return None

    @staticmethod
    async def update(category_id: int, category: CategoryUpdate) -> Optional[CategoryModel]:
        """更新分类"""
        try:
            # 获取现有分类
            existing = await CategoryService.get(category_id)
            if not existing:
                return None

            # 构建更新数据
            update_data = category.dict(exclude_unset=True)

            # 如果父分类有变化，需要重新计算路径和URI路径
            if 'parent_id' in update_data and update_data['parent_id'] != existing.parent_id:
                path = None
                uri_path = existing.slug
                level = 1

                if update_data['parent_id']:
                    parent = await CategoryService.get(update_data['parent_id'])
                    if parent:
                        path = f"{parent.path},{parent.id}" if parent.path else str(parent.id)
                        uri_path = f"{parent.uri_path}/{existing.slug}" if parent.uri_path else existing.slug
                        level = parent.level + 1

                update_data.update({
                    "path": path,
                    "uri_path": uri_path,
                    "level": level
                })

            # 如果没有更新字段，直接返回现有分类
            if not update_data:
                return existing

            # 构建更新查询
            set_clause = ", ".join([f"{k} = %s" for k in update_data.keys()])
            query = f"UPDATE r_category SET {set_clause} WHERE id = %s"

            # 执行更新
            params = list(update_data.values()) + [category_id]
            await mysql_db.execute(query, params)

            # 获取更新后的分类
            return await CategoryService.get(category_id)
        except Exception as e:
            logger.error(f"更新分类失败: {e}")
            return None

    @staticmethod
    async def delete(category_id: int) -> bool:
        """删除分类"""
        try:
            query = "DELETE FROM r_category WHERE id = %s"
            result = await mysql_db.execute(query, (category_id,))
            return result > 0
        except Exception as e:
            logger.error(f"删除分类失败: {e}")
            return False

    @staticmethod
    async def get_children(category_id: int) -> List[CategoryModel]:
        """获取子分类"""
        try:
            query = "SELECT * FROM r_category WHERE parent_id = %s ORDER BY sort ASC, id ASC"
            results = await mysql_db.fetch_all(query, (category_id,))
            return [CategoryModel(**result) for result in results]
        except Exception as e:
            logger.error(f"获取子分类失败: {e}")
            return []

    @staticmethod
    async def get_tree(site: str, parent_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取分类树"""
        try:
            # 获取指定父分类下的所有分类
            if parent_id is None:
                query = "SELECT * FROM r_category WHERE site = %s AND parent_id IS NULL AND is_enabled = 1 ORDER BY sort ASC, id ASC"
                params = [site]
            else:
                query = "SELECT * FROM r_category WHERE site = %s AND parent_id = %s AND is_enabled = 1 ORDER BY sort ASC, id ASC"
                params = [site, parent_id]

            categories = await mysql_db.fetch_all(query, params)
            result = []

            for category in categories:
                # 递归获取子分类
                children = await CategoryService.get_tree(site, category['id'])

                # 构建分类树节点
                node = {
                    'id': category['id'],
                    'name': category['name'],
                    'slug': category['slug'],
                    'level': category['level'],
                    'sort': category['sort'],
                    'is_enabled': bool(category['is_enabled']),
                    'children': children
                }

                result.append(node)

            return result
        except Exception as e:
            logger.error(f"获取分类树失败: {e}")
            return []

    async def save_category_level(self, data):
        """顶级分类子类落库"""
        logger.info(f"{data['name']} save_category_level开始消费")
        if not data or len(data['level']) <= 0:
            logger.error("data 数据不存在")
            return None
        logger.info(f"====data: {str(data)}")
        try:
            category = await self.get_category_by_name(data['name'])
            if not category:
                logger.error(f"{data['name']} 数据不存在")
                return None

            # 初始化翻译
            translator = Translate()

            # 遍历所有二级分类（类型、地区、语言、年份、排序）
            for index, level2 in enumerate(data['level']):
                try:
                    # 类名翻译转换slug
                    slug = await translator.process_text(level2['name'], translate_type="googletrans")
                    if not slug or slug == "Translation failed":
                        logger.error(f"googletrans 翻译失败: {level2['name']}")
                        continue  # 跳过此项而不是返回空

                    # 处理URL为空的情况
                    url = level2['url']
                    if url and url.startswith('/'):
                        url = f"{category.site}{level2['url']}"
                    elif not url:
                        url = f"{category.site}/show/2-----1-1.html"  # 默认URL
                        logger.warning(f"{level2['name']} URL为空，使用默认URL: {url}")

                    category_level2 = await self.create(CategoryCreate(
                        name=level2['name'],
                        slug=slug,
                        parent_id=category.id,
                        level=2,
                        sort=index + 1,
                        is_enabled=1,
                        site=category.site,
                        url=url,
                        href=level2['url'],
                    ))
                    if not category_level2:
                        logger.error(f"{level2['name']} 新增失败")
                        continue  # 跳过此项而不是返回

                    logger.info(f"{level2['name']} 新增成功")

                    # 检查是否有三级分类
                    if not level2.get('level'):
                        logger.info(f"{level2['name']} 无子分类")
                        continue

                    # 遍历三级分类
                    for index2, level3 in enumerate(level2['level']):
                        try:
                            # 类名翻译转换slug
                            slug3 = await translator.process_text(level3['name'], translate_type="googletrans")
                            if not slug3 or slug3 == "Translation failed":
                                logger.error(f"googletrans 翻译失败: {level3['name']}")
                                continue  # 跳过此项

                            # 处理URL
                            url3 = level3['url']
                            if url3 and url3.startswith('/'):
                                url3 = f"{category.site}{level3['url']}"
                            elif not url3:
                                url3 = f"{category.site}/show/2-----1-1.html"  # 默认URL
                                logger.warning(f"{level3['name']} URL为空，使用默认URL: {url3}")

                            category_level3 = await self.create(CategoryCreate(
                                name=level3['name'],
                                slug=slug3,
                                parent_id=category_level2.id,
                                level=3,
                                sort=index2 + 1,
                                is_enabled=1,
                                site=category.site,
                                url=url3,
                                href=level3['url'],
                            ))
                            if not category_level3:
                                logger.error(f"{level3['name']} 新增失败")
                                continue  # 跳过此项
                            logger.info(f"{level2['name']}-{level3['name']} 新增成功")
                        except Exception as e:
                            logger.error(f"处理三级分类 {level3['name']} 时出错: {e}")
                            continue  # 继续处理下一个三级分类
                except Exception as e:
                    logger.error(f"处理二级分类 {level2['name']} 时出错: {e}")
                    continue  # 继续处理下一个二级分类

            return True  # 所有处理完成
        except Exception as e:
            logger.error(f"顶级分类子类落库失败: {e}")
            return None


# 创建service实例
category_service = CategoryService()
