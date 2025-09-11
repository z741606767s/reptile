## 项目介绍
```text
爬取页面 www.duse2.com 中的数据
```


```text
# 创建新的 Conda 环境
conda create -n fastapi-reptile python=3.9

# 激活环境
conda activate fastapi-reptile

# 安装基础依赖
conda install -c conda-forge fastapi uvicorn

# 安装数据库和消息系统客户端
conda install -c conda-forge aiomysql aioredis motor aiokafka kazoo

# 安装其他必要的包
conda install -c conda-forge python-dotenv python-jose passlib bcrypt

# 退出环境
conda deactivate
```

```text

--------------------------------------------------
5. 启动方式
------------------------------------------------```bash
# 1. 安装依赖
pip install -r requirements.txt
# 示例 requirements.txt
# fastapi
# uvicorn[standard]
# redis
# sqlalchemy[asyncio]
# aiomysql
# python-dotenv

# 2. 配置 .env
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
MYSQL_DSN=mysql+aiomysql://root:123456@127.0.0.1:3306/test?charset=utf8mb4

# 3. 启动
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```