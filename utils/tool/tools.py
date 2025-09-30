import re
from urllib.parse import urlparse


def extract_num_before_html(url):
    # 正则规则：匹配末尾“1个及以上数字 + .html”，排除“- + .html”
    # \d+ 匹配连续数字（1位/多位），(?<!-) 是负向断言：确保数字前不是“-”
    match = re.search(r'(?<!-)(\d+)\.html$', url)
    # 有匹配则返回连续数字，无匹配（如-.html、无数字.html）返回空字符串
    return match.group(1) if match else ""


def get_left_part_of_valid_url(url):
    # 修正正则：仅匹配末尾“连续数字+.html”，删除(?<!-)，避免误判数字前有-的场景
    # (\d+\.html)$：确保URL末尾是“数字+.html”，捕获该后缀用于截取
    match = re.search(r'(\d+\.html)$', url)
    if match:
        suffix = match.group(1)  # 例如“1.html”“12.html”
        left_part = url[:-len(suffix)]  # 截取左侧内容
        return left_part
    else:
        # 无效场景：末尾是-.html、无数字.html等，返回空
        return ""


def is_valid_url(url):
    if not url:
        return False
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False
