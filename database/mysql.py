import aiomysql
from contextlib import asynccontextmanager
from config.settings import settings
from typing import AsyncGenerator, Optional


class MySQLDatabase:
    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None

    async def connect(self):
        """创建MySQL连接池"""
        self.pool = await aiomysql.create_pool(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            db=settings.MYSQL_DB,
            autocommit=True,
            minsize=1,
            maxsize=10
        )
        print("MySQL连接池已创建")

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

        async with self.pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def get_cursor(self) -> AsyncGenerator[aiomysql.Cursor, None]:
        """获取MySQL游标"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                yield cursor


# 全局MySQL实例
mysql_db = MySQLDatabase()