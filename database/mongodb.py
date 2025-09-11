from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import settings


class MongoDB:
    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.db = None

    async def connect(self):
        """连接MongoDB"""
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB]
        print("MongoDB连接已建立")

    async def disconnect(self):
        """断开MongoDB连接"""
        if self.client:
            self.client.close()
            print("MongoDB连接已关闭")

    def get_database(self):
        """获取数据库实例"""
        return self.db


# 全局MongoDB实例
mongodb = MongoDB()