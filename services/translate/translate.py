import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import requests
from googletrans import Translator
import re
from config import settings

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)


class Translate:
    def __init__(self):
        self.translator = Translator()
        self.executor = ThreadPoolExecutor(max_workers=5)  # 创建线程池执行同步操作

    @staticmethod
    async def translate_chinese_to_english_with_mymemory(self, text, retries=3, delay=1):
        """
        使用免费翻译API将中文文本翻译成英文
        注意：这个API有使用限制，仅适用于演示目的
        :param self:
        :param text: 中文文本
        :param retries: 重试次数
        :param delay: 重试延迟秒数
        :return: 英文文本
        """
        for attempt in range(retries):
            try:
                # 在线程池中执行同步的requests操作
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    self._translate_with_mymemory_sync,
                    text
                )
                return result
            except Exception as e:
                logger.error(f"翻译出错 (尝试 {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                else:
                    return text

    def _translate_with_mymemory_sync(self, text):
        """同步执行的mymemory翻译"""
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": text,
            "langpair": "zh|en"
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data["responseStatus"] == 200:
            return data["responseData"]["translatedText"]
        else:
            return "Translation failed"

    @staticmethod
    async def translate_chinese_to_english_with_googletrans(self, text, retries=3, delay=1):
        """
        使用googletrans库将中文文本翻译成英文
        :param self:
        :param text: 中文文本
        :param retries: 重试次数
        :param delay: 重试延迟秒数
        :return: 英文文本
        """
        for attempt in range(retries):
            try:
                # 在线程池中执行同步的googletrans操作
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    self._translate_with_googletrans_sync,
                    text
                )
                return result
            except Exception as e:
                logger.error(f"翻译出错 (尝试 {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                else:
                    return text

    def _translate_with_googletrans_sync(self, text):
        """同步执行的googletrans翻译"""
        translation = self.translator.translate(text, src='zh-cn', dest='en')
        return translation.text

    async def process_text(self, text, translate_type="googletrans"):
        """
        处理文本：翻译中文→英文→小写→用下划线连接单词
        :param text: 中文文本
        :param translate_type: 翻译类型，可选"googletrans"或"mymemory"
        :return: 处理后的文本
        """
        # 翻译中文到英文
        if translate_type == "googletrans":
            english_text = await self.translate_chinese_to_english_with_googletrans(self, text)
        elif translate_type == "mymemory":
            english_text = await self.translate_chinese_to_english_with_mymemory(self, text)
        else:
            english_text = text
        logger.info(f"翻译结果: {english_text}")

        # 转换为小写
        lower_text = english_text.lower()

        # 移除非字母数字字符，用下划线替换空格
        processed_text = re.sub(r'[^a-zA-Z0-9\s]', '', lower_text)  # 移除非字母数字字符
        processed_text = re.sub(r'\s+', '_', processed_text.strip())  # 用下划线替换空格

        return processed_text


