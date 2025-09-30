from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import HttpUrl
import logging
from config import settings
from database.mysql import mysql_db  # 全局异步MySQL连接池实例
from models.drama_model import DramaModel  # 数据库表对应的数据模型
from schemas.drama_schemas import (  # API层数据验证与响应模型
    DramaCreate,
    DramaUpdate,
    DramaList,
    DramaBrief,
    Drama
)
from utils.tool.tools import is_valid_url

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


class DramaService:
    """剧集    剧集业务逻辑服务层
    封装所有与剧集相关的数据库操作和业务规则
    所有方法均为静态方法，通过mysql_db实例与数据库交互
    """

    # ------------------------------ 基础CRUD操作 ------------------------------

    @staticmethod
    async def create_drama(drama_in: DramaCreate) -> Optional[DramaModel]:
        """创建新剧集 - 适配数据库工具类API，解决acquire方法不存在问题"""
        try:
            # 1. 处理特殊类型转换
            drama_data = drama_in.dict()

            # 转换URL类型为字符串
            cover_str = str(drama_data["cover"]) if isinstance(drama_data["cover"], HttpUrl) else drama_data["cover"]
            url_str = str(drama_data["url"]) if isinstance(drama_data["url"], HttpUrl) else drama_data["url"]

            # 转换Decimal为float
            score_float = float(drama_data["score"])

            # 处理日期时间
            current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 2. 显式构建INSERT语句，为desc字段添加反引号
            table_name = DramaModel.Config.table_name
            insert_query = f"""
                INSERT INTO {table_name} (
                    category_id, title, `desc`, premiere, remark, site, 
                    cover, score, hot, 
                    douban_film_review, douyin_film_review, xinlang_film_review,
                    kuaishou_film_review, baidu_film_review,
                    url, href, created_at, updated_at
                ) VALUES (
                     %s, %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s
                )
            """

            # 3. 准备参数
            params = (
                drama_data["category_id"],
                drama_data["title"],
                drama_data["desc"],
                drama_data["premiere"].strftime("%Y-%m-%d"),
                drama_data["remark"],
                drama_data["site"],
                cover_str,
                score_float,
                drama_data["hot"],
                drama_data["douban_film_review"],
                drama_data["douyin_film_review"],
                drama_data["xinlang_film_review"],
                drama_data["kuaishou_film_review"],
                drama_data["baidu_film_review"],
                url_str,
                drama_data["href"],
                current_dt,
                current_dt
            )

            # 4. 执行SQL - 适配没有acquire()方法的数据库工具类
            # 假设mysql_db有execute方法直接执行SQL并返回结果
            await mysql_db.execute(insert_query, params)

            # 5. 获取刚插入的记录ID
            # 不同数据库工具类获取lastrowid方式可能不同
            last_id_query = "SELECT LAST_INSERT_ID()"
            result = await mysql_db.fetch_one(last_id_query)
            new_drama_id = result[0] if result else None

            if new_drama_id:
                return await DramaService.get_drama(drama_id=new_drama_id)
            return None

        except Exception as e:
            logger.error(f"创建剧失败: {str(e)}")
            return None

    @staticmethod
    async def get_drama(drama_id: int) -> Optional[DramaModel]:
        """
        根据ID获取单部剧集详情
        :param drama_id: 剧集ID（自增主键）
        :return: 存在返回DramaModel，不存在返回None
        """
        try:
            # 构建查询SQL（`desc`为SQL关键字，需用反引号包裹）
            query = f"""
                SELECT id, category_id, title, `desc`, premiere, remark, cover, 
                       score, hot, douban_film_review, douyin_film_review,
                       xinlang_film_review, kuaishou_film_review, baidu_film_review,
                       site, url, href, created_at, updated_at
                FROM {DramaModel.Config.table_name}
                WHERE id = %s
                LIMIT 1
            """

            # 执行查询（使用dict_cursor返回字典格式结果）
            drama_dict = await mysql_db.fetch_one(
                query=query,
                params=(drama_id,),
                dict_cursor=True
            )

            # 无结果返回None
            if not drama_dict:
                return None

            # 转换数据库结果为DramaModel（处理类型适配）
            return DramaService._parse_db_dict_to_model(drama_dict)

        except Exception as e:
            logger.error(f"获取剧集ID={drama_id}失败: {str(e)}")
            return None

    @staticmethod
    async def get_dramas(
            skip: int = 0,
            limit: int = 10,
            category_id: Optional[int] = None,
            title: Optional[str] = None,
            site: Optional[str] = None,
            min_score: Optional[float] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            sort_by: str = "created_at",
            sort_desc: bool = True
    ) -> DramaList:
        """
        获取剧集列表（支持多条件过滤、排序、分页）
        :param category_id: 分类id
        :param skip: 分页偏移量（默认0）
        :param limit: 分页大小（默认10）
        :param title: 标题模糊查询（可选）
        :param site: 站点精确查询（可选）
        :param min_score: 最低评分过滤（可选）
        :param start_date: 首映开始时间（可选）
        :param end_date: 首映结束时间（可选）
        :param sort_by: 排序字段（默认created_at）
        :param sort_desc: 是否降序（默认True）
        :return: 包含总数量和剧集列表的DramaList模型
        """
        try:
            # 1. 构建查询条件
            where_clause = []
            params = []

            if category_id:
                where_clause.append(f"category_id={category_id}")
                params.append(f"category_id={category_id}")
            if title:
                where_clause.append("title LIKE %s")
                params.append(f"%{title}%")
            if site:
                where_clause.append("site = %s")
                params.append(site)
            if min_score is not None:
                where_clause.append("score >= %s")
                params.append(round(min_score, 1))
            if start_date:
                where_clause.append("premiere >= %s")
                params.append(start_date.strftime("%Y-%m-%d"))
            if end_date:
                where_clause.append("premiere <= %s")
                params.append(end_date.strftime("%Y-%m-%d"))

            # 2. 处理排序
            valid_sort_fields = ["title", "premiere", "score", "hot", "created_at"]
            sort_field = sort_by if sort_by in valid_sort_fields else "created_at"
            sort_order = "DESC" if sort_desc else "ASC"

            # 3. 构建完整SQL
            where_sql = "WHERE " + " AND ".join(where_clause) if where_clause else ""

            # 统计总数
            count_query = f"SELECT COUNT(*) AS total FROM {DramaModel.Config.table_name} {where_sql}"

            # 查询列表数据
            data_query = f"""
                SELECT id, category_id, title, `desc`, premiere, remark, cover, 
                       score, hot, douban_film_review, douyin_film_review,
                       xinlang_film_review, kuaishou_film_review, baidu_film_review,
                       site, url, href, created_at, updated_at
                FROM {DramaModel.Config.table_name}
                {where_sql}
                ORDER BY {sort_field} {sort_order}
                LIMIT %s OFFSET %s
            """

            # 4. 执行查询
            total_result = await mysql_db.fetch_one(count_query, tuple(params))
            total = total_result["total"] if total_result else 0

            data_params = tuple(params) + (limit, skip)
            drama_dicts = await mysql_db.fetch_all(data_query, data_params)

            # 5. 转换为DramaModel列表
            drama_items = [
                DramaService._parse_db_dict_to_model(item)
                for item in drama_dicts
            ]

            return DramaList(total=total, items=drama_items)

        except Exception as e:
            logger.error(f"获取剧集列表失败: {str(e)}")
            return DramaList(total=0, items=[])

    @staticmethod
    async def update_drama(
            drama_id: int,
            drama_update: DramaUpdate
    ) -> Optional[DramaModel]:
        """
        更新剧集信息（支持部分字段更新）
        :param drama_id: 要更新的剧集ID
        :param drama_update: 更新的字段数据
        :return: 更新成功返回新数据，失败返回None
        """
        try:
            # 1. 筛选非空更新字段
            update_data = drama_update.dict(exclude_unset=True)
            if not update_data:
                return await DramaService.get_drama(drama_id)

            # 2. 处理特殊类型转换
            if "cover" in update_data and isinstance(update_data["cover"], HttpUrl):
                update_data["cover"] = str(update_data["cover"])
            if "url" in update_data and isinstance(update_data["url"], HttpUrl):
                update_data["url"] = str(update_data["url"])
            if "score" in update_data and isinstance(update_data["score"], Decimal):
                update_data["score"] = float(update_data["score"])
            if "premiere" in update_data and isinstance(update_data["premiere"], datetime.date):
                update_data["premiere"] = update_data["premiere"].strftime("%Y-%m-%d")

            # 强制更新时间戳
            update_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 3. 执行更新操作
            affected_rows = await mysql_db.update(
                table=DramaModel.Config.table_name,
                data=update_data,
                where="id = %s",
                where_params=(drama_id,)
            )

            if affected_rows == 0:
                logger.warning(f"剧集ID={drama_id}无更新（ID不存在或数据未变化）")
                return None

            # 4. 返回更新后的完整数据
            return await DramaService.get_drama(drama_id)

        except Exception as e:
            logger.error(f"更新剧集ID={drama_id}失败: {str(e)}")
            return None

    @staticmethod
    async def delete_drama(drama_id: int) -> bool:
        """
        删除剧集
        :param drama_id: 要删除的剧集ID
        :return: 成功返回True，失败/不存在返回False
        """
        try:
            affected_rows = await mysql_db.delete(
                table=DramaModel.Config.table_name,
                where="id = %s",
                where_params=(drama_id,)
            )

            result = affected_rows > 0
            if result:
                logger.info(f"剧集ID={drama_id}删除成功")
            else:
                logger.warning(f"剧集ID={drama_id}不存在，删除失败")
            return result

        except Exception as e:
            logger.error(f"删除剧集ID={drama_id}失败: {str(e)}")
            return False

    # ------------------------------ 业务扩展功能 ------------------------------
    @staticmethod
    async def get_hot_dramas(limit: int = 5) -> List[DramaModel]:
        """获取热门剧集（按热度降序）"""
        try:
            query = f"""
                SELECT id, title, `desc`, premiere, remark, cover, 
                       score, hot, douban_film_review, douyin_film_review,
                       xinlang_film_review, kuaishou_film_review, baidu_film_review,
                       site, url, href, created_at, updated_at
                FROM {DramaModel.Config.table_name}
                ORDER BY hot DESC
                LIMIT %s
            """
            drama_dicts = await mysql_db.fetch_all(query, (limit,))
            return [DramaService._parse_db_dict_to_model(item) for item in drama_dicts]

        except Exception as e:
            logger.error(f"获取热门剧集失败: {str(e)}")
            return []

    @staticmethod
    async def get_recent_dramas(limit: int = 5) -> List[DramaModel]:
        """获取最近上映剧集（按首映时间降序）"""
        try:
            query = f"""
                SELECT id, title, `desc`, premiere, remark, cover, 
                       score, hot, douban_film_review, douyin_film_review,
                       xinlang_film_review, kuaishou_film_review, baidu_film_review,
                       site, url, href, created_at, updated_at
                FROM {DramaModel.Config.table_name}
                ORDER BY premiere DESC
                LIMIT %s
            """
            drama_dicts = await mysql_db.fetch_all(query, (limit,))
            return [DramaService._parse_db_dict_to_model(item) for item in drama_dicts]

        except Exception as e:
            logger.error(f"获取最近上映剧集失败: {str(e)}")
            return []

    @staticmethod
    async def get_top_rated_dramas(limit: int = 5) -> List[DramaModel]:
        """获取高分剧集（按评分降序，过滤评分>0）"""
        try:
            query = f"""
                SELECT id, title, `desc`, premiere, remark, cover, 
                       score, hot, douban_film_review, douyin_film_review,
                       xinlang_film_review, kuaishou_film_review, baidu_film_review,
                       site, url, href, created_at, updated_at
                FROM {DramaModel.Config.table_name}
                WHERE score > 0
                ORDER BY score DESC
                LIMIT %s
            """
            drama_dicts = await mysql_db.fetch_all(query, (limit,))
            return [DramaService._parse_db_dict_to_model(item) for item in drama_dicts]

        except Exception as e:
            logger.error(f"获取高分剧集失败: {str(e)}")
            return []

    @staticmethod
    async def search_dramas(keyword: str, limit: int = 20) -> List[DramaBrief]:
        """搜索剧集（标题/简介包含关键词）"""
        try:
            query = f"""
                SELECT id, title, cover, score, premiere, site 
                FROM {DramaModel.Config.table_name}
                WHERE title LIKE %s OR `desc` LIKE %s
                LIMIT %s
            """
            params = (f"%{keyword}%", f"%{keyword}%", limit)
            drama_dicts = await mysql_db.fetch_all(query, params)

            # 转换为DramaBrief模型
            brief_list = []
            for item in drama_dicts:
                brief_list.append(DramaBrief(
                    id=item["id"],
                    title=item["title"],
                    cover=item["cover"],
                    score=Decimal(str(item["score"])),
                    premiere=datetime.strptime(item["premiere"], "%Y-%m-%d").date(),
                    site=item["site"]
                ))
            return brief_list

        except Exception as e:
            logger.error(f"搜索剧集失败: {str(e)}")
            return []

    @staticmethod
    async def get_drama_stats() -> Dict[str, Any]:
        """获取剧集统计信息"""
        try:
            # 1. 总数统计
            total_query = f"SELECT COUNT(*) AS total FROM {DramaModel.Config.table_name}"
            total_result = await mysql_db.fetch_one(total_query)
            total = total_result["total"] if total_result else 0

            # 2. 平均分统计
            avg_query = f"""
                SELECT AVG(score) AS avg_score 
                FROM {DramaModel.Config.table_name}
                WHERE score > 0
            """
            avg_result = await mysql_db.fetch_one(avg_query)
            avg_score = round(float(avg_result["avg_score"]) if avg_result["avg_score"] else 0.0, 1)

            # 3. 站点分布统计
            site_query = f"""
                SELECT site, COUNT(*)(*) AS count 
                FROM {DramaModel.Config.table_name}
                GROUP BY site
                ORDER BY count DESC
            """
            site_result = await mysql_db.fetch_all(site_query)
            site_distribution = {item["site"]: item["count"] for item in site_result}

            # 4. 首映时间范围统计
            date_query = f"""
                SELECT MIN(premiere) AS earliest_date, MAX(premiere) AS latest_date
                FROM {DramaModel.Config.table_name}
                WHERE premiere IS IS NOT NULL
            """
            date_result = await mysql_db.fetch_one(date_query)
            earliest_premiere = date_result["earliest_date"] if date_result["earliest_date"] else None
            latest_premiere = date_result["latest_date"] if date_result["latest_date"] else None

            return {
                "total_count": total,
                "average_score": avg_score,
                "site_distributionbution": site_distribution,
                "earliest_premiere": earliest_premiere,
                "latest_premiere": latest_premiere,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        except Exception as e:
            logger.error(f"获取剧集统计信息失败: {str(e)}")
            return {
                "total_count": 0,
                "average_score": 0.0,
                "site_distribution": {},
                "earliest_premiere": None,
                "latest_premiere": None,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    # ------------------------------ 私有工具方法 ------------------------------
    @staticmethod
    def _parse_db_dict_to_model(drama_dict: Dict[str, Any]) -> DramaModel:
        """
        将数据库查询结果字典转换为DramaModel
        处理类型转换和格式适配
        """
        # 转换数值类型
        drama_dict["score"] = Decimal(str(drama_dict["score"]))
        drama_dict["hot"] = int(drama_dict["hot"])

        # 转换日期时间类型
        drama_dict["created_at"] = datetime.strptime(
            drama_dict["created_at"], "%Y-%m-%d %H:%M:%S"
        )
        drama_dict["updated_at"] = datetime.strptime(
            drama_dict["updated_at"], "%Y-%m-%d %H:%M:%S"
        )
        drama_dict["premiere"] = datetime.strptime(
            drama_dict["premiere"], "%Y-%m-%d"
        ).date()

        return DramaModel(**drama_dict)

    @staticmethod
    async def is_title_exists(title: str) -> bool:
        """检查标题是否已存在"""
        try:
            query = f"""
                    SELECT COUNT(*) AS count 
                    FROM {DramaModel.Config.table_name}
                    WHERE title = %s
                    LIMIT 1
                """
            result = await mysql_db.fetch_one(query, (title,))
            return result["count"] > 0 if result else False
        except Exception as e:
            logger.error(f"检查标题存在性失败: {str(e)}")
            return False  # 发生错误时默认视为存在，避免重复写入

    async def save_drama_list(self, drama_list: List[Dict[str, Any]], category_id: int, category_name: str) -> Dict[
        str, int]:
        """
        批量保存剧集列表到数据库
        :param drama_list: 剧集数据列表
        :param category_id: 分类ID
        :param category_name: 分类名称
        :return: 包含成功插入、已存在和失败数量的字典
        """
        if not drama_list:
            logger.info("没有剧集数据需要保存")
            return {"inserted": 0, "existing": 0, "failed": 0}

        # 先获取所有已存在的标题，减少数据库查询次数
        existing_titles = await self._get_existing_titles()
        current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        premiere_date = date.today().strftime("%Y-%m-%d")

        # 准备批量插入的数据
        batch_data = []
        existing_count = 0

        for index, drama_dict in enumerate(drama_list, 1):
            title = drama_dict.get("title", f"未知剧_{index}")

            # 检查标题是否已存在
            if title in existing_titles:
                existing_count += 1
                logger.debug(f"剧集《{title}》已存在，将跳过写入")
                continue

            # 处理URL
            cover_url = drama_dict.get('image_url')
            cover_str = str(cover_url) if is_valid_url(cover_url) else ''

            url = drama_dict.get('url')
            url_str = str(url) if is_valid_url(url) else ''

            # 处理评分
            try:
                score = float(drama_dict.get('score', 0.0))
            except (ValueError, TypeError):
                score = 0.0

            # 构建单条记录数据
            drama_data = (
                category_id,
                title,
                f"剧集《{drama_dict.get('title')}》{drama_dict.get('episode')}",
                premiere_date,
                drama_dict.get('episode', '未知更新状态'),
                drama_dict.get('site', ''),
                cover_str,
                score,
                0,  # 初始热度值
                "",  # douban_film_review
                "",  # douyin_film_review
                "",  # xinlang_film_review
                "",  # kuaishou_film_review
                "",  # baidu_film_review
                url_str,
                drama_dict.get('href', ''),
                current_dt,
                current_dt
            )

            batch_data.append(drama_data)

        # 执行批量插入
        inserted_count = 0
        failed_count = 0

        if batch_data:
            try:
                table_name = DramaModel.Config.table_name
                insert_query = f"""
                    INSERT INTO {table_name} (
                        category_id, title, `desc`, premiere, remark, site, 
                        cover, score, hot, 
                        douban_film_review, douyin_film_review, xinlang_film_review,
                        kuaishou_film_review, baidu_film_review,
                        url, href, created_at, updated_at
                    ) VALUES (
                         %s, %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s, %s, %s
                    )
                """

                # 执行批量插入
                result = await mysql_db.execute_many(insert_query, batch_data)
                inserted_count = result if result is not None else 0
                logger.info(f"批量插入成功，共插入 {inserted_count} 条剧集数据")

            except Exception as e:
                logger.error(f"批量插入剧集数据失败: {str(e)}", exc_info=True)
                failed_count = len(batch_data)

        logger.info(f"====category_id: {category_id} -- category_name: {category_name} -- inserted: {inserted_count} -- existing: {existing_count} -- failed: {failed_count}")
        return {
            "inserted": inserted_count,
            "existing": existing_count,
            "failed": failed_count
        }

    @staticmethod
    async def _get_existing_titles() -> set:
        """获取所有已存在的剧集标题，用于批量检查"""
        try:
            query = f"SELECT title FROM {DramaModel.Config.table_name}"
            results = await mysql_db.fetch_all(query)
            return {item["title"] for item in results} if results else set()
        except Exception as e:
            logger.error(f"获取已存在标题列表失败: {str(e)}")
            return set()


# 创建service实例
drama_service = DramaService()