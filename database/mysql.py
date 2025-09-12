import logging
import aiomysql
from contextlib import asynccontextmanager
from config.settings import settings
from typing import AsyncGenerator, Optional, Any
from functools import wraps

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


class MySQLDatabase:
    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None

    async def connect(self):
        """创建MySQL连接池"""
        try:
            self.pool = await aiomysql.create_pool(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                db=settings.MYSQL_DB,
                autocommit=False,  # 禁用自动提交，手动控制事务
                minsize=1,
                maxsize=10,
                connect_timeout=60,
                echo=settings.DEBUG  # 设置为True可以打印SQL语句，用于调试
            )
            logger.info("MySQL连接池已创建")
        except Exception as e:
            logger.error(f"创建MySQL连接池失败: {e}")
            raise

    async def disconnect(self):
        """关闭MySQL连接池"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None  # 设置为None，避免__del__中再次尝试关闭
            print("MySQL连接池已关闭")

    # 移除或修改__del__方法，避免在垃圾回收时尝试异步操作
    def __del__(self):
        # 不要在这里尝试异步操作，因为事件循环可能已经关闭
        # 依赖disconnect方法进行显式清理
        pass

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiomysql.Connection, None]:
        """获取MySQL连接"""
        if not self.pool:
            await self.connect()

        conn = await self.pool.acquire()
        try:
            yield conn
        finally:
            self.pool.release(conn)

    @asynccontextmanager
    async def get_cursor(self, dict_cursor: bool = True) -> AsyncGenerator[aiomysql.Cursor, None]:
        """获取MySQL游标"""
        async with self.get_connection() as conn:
            cursor_class = aiomysql.DictCursor if dict_cursor else aiomysql.Cursor
            async with conn.cursor(cursor_class) as cursor:
                try:
                    yield cursor
                    await conn.commit()  # 自动提交事务
                except Exception as e:
                    await conn.rollback()  # 发生异常时回滚
                    raise e

    async def execute(self, query: str, params: Any = None, dict_cursor: bool = True):
        """执行SQL查询并返回结果"""
        async with self.get_cursor(dict_cursor) as cursor:
            await cursor.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                return await cursor.fetchall()
            return cursor.lastrowid

    async def fetch_one(self, query: str, params: Any = None, dict_cursor: bool = True):
        """执行SQL查询并返回单条结果"""
        async with self.get_cursor(dict_cursor) as cursor:
            await cursor.execute(query, params)
            return await cursor.fetchone()

    async def fetch_all(self, query: str, params: Any = None, dict_cursor: bool = True):
        """执行SQL查询并返回所有结果"""
        async with self.get_cursor(dict_cursor) as cursor:
            await cursor.execute(query, params)
            return await cursor.fetchall()

    async def insert(self, table: str, data: dict) -> int:
        """插入数据到指定表"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        async with self.get_cursor() as cursor:
            await cursor.execute(query, tuple(data.values()))
            return cursor.lastrowid

    async def update(self, table: str, data: dict, where: str, where_params: Any = None) -> int:
        """更新表中的数据"""
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"

        params = tuple(data.values())
        if where_params:
            if isinstance(where_params, tuple):
                params += where_params
            else:
                params += (where_params,)

        async with self.get_cursor() as cursor:
            await cursor.execute(query, params)
            return cursor.rowcount

    async def delete(self, table: str, where: str, where_params: Any = None) -> int:
        """从表中删除数据"""
        query = f"DELETE FROM {table} WHERE {where}"

        async with self.get_cursor() as cursor:
            await cursor.execute(query, where_params)
            return cursor.rowcount

    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = """
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            """
        result = await self.fetch_one(query, (settings.MYSQL_DB, table_name))
        return result['count'] > 0 if result else False

    async def health_check(self) -> bool:
        """检查数据库连接是否健康"""
        try:
            async with self.get_cursor() as cursor:
                await cursor.execute("SELECT 1")
                return True
        except Exception:
            return False


# 全局MySQL实例
mysql_db = MySQLDatabase()


# 装饰器用于自动处理数据库连接
def with_db_connection(func):
    """装饰器，自动为函数提供数据库连接"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 检查是否已经提供了连接或游标
        if 'conn' not in kwargs and 'cursor' not in kwargs:
            async with mysql_db.get_connection() as conn:
                kwargs['conn'] = conn
                return await func(*args, **kwargs)
        return await func(*args, **kwargs)

    return wrapper


def with_db_cursor(dict_cursor=True):
    """装饰器，自动为函数提供数据库游标"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 检查是否已经提供了游标
            if 'cursor' not in kwargs:
                async with mysql_db.get_cursor(dict_cursor) as cursor:
                    kwargs['cursor'] = cursor
                    return await func(*args, **kwargs)
            return await func(*args, **kwargs)

        return wrapper

    return decorator