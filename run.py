import requests
import re
import os
import subprocess
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import json
import threading
import time


class VideoDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def extract_video_info(self, url):
        """提取页面中的视频信息"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取标题
            title = soup.find('title').text.strip() if soup.find('title') else 'video'
            title = re.sub(r'[\\/*?:"<>|]', '', title)  # 移除非法文件名字符

            # 查找可能的视频源
            video_sources = []

            # 方法1: 查找script标签中的视频信息
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # 查找m3u8地址
                    m3u8_matches = re.findall(r'"(https?://[^"]*\.m3u8[^"]*)"', script.string)
                    video_sources.extend(m3u8_matches)

                    # 查找mp4地址
                    mp4_matches = re.findall(r'"(https?://[^"]*\.mp4[^"]*)"', script.string)
                    video_sources.extend(mp4_matches)

            # 方法2: 查找视频播放器配置
            for script in scripts:
                if script.string and 'xgplayer' in script.string:
                    # 尝试提取视频地址
                    url_matches = re.findall(r'url[\s:]*["\'](https?://[^"\']+)["\']', script.string)
                    video_sources.extend(url_matches)

            # 去重
            video_sources = list(set(video_sources))

            return {
                'title': title,
                'sources': video_sources,
                'page_content': response.text
            }

        except Exception as e:
            print(f"提取视频信息时出错: {e}")
            return None

    def download_video(self, url, output_path=None):
        """下载视频主函数"""
        video_info = self.extract_video_info(url)
        if not video_info:
            print("无法提取视频信息")
            return False

        print(f"视频标题: {video_info['title']}")
        print(f"找到 {len(video_info['sources'])} 个可能的视频源")

        for i, source in enumerate(video_info['sources']):
            print(f"{i + 1}. {source}")

        # 尝试下载第一个可用的视频源
        for source in video_info['sources']:
            if '.m3u8' in source:
                if self.download_m3u8(source, video_info['title'], output_path):
                    return True
            elif '.mp4' in source:
                if self.download_mp4(source, video_info['title'], output_path):
                    return True

        print("没有找到可下载的视频源")
        return False

    def download_m3u8(self, m3u8_url, title, output_path=None):
        """下载m3u8视频"""
        try:
            print(f"尝试下载m3u8视频: {m3u8_url}")

            # 获取m3u8内容
            response = self.session.get(m3u8_url)
            response.raise_for_status()

            # 解析m3u8文件
            lines = response.text.split('\n')
            ts_list = [line.strip() for line in lines if line.strip() and not line.startswith('#')]

            if not ts_list:
                print("m3u8文件中没有找到ts片段")
                return False

            # 确定输出目录和文件名
            if not output_path:
                output_path = os.path.join(os.getcwd(), title)
            os.makedirs(output_path, exist_ok=True)

            # 下载所有ts片段
            ts_files = []
            for i, ts_url in enumerate(ts_list):
                # 处理相对URL
                if not ts_url.startswith('http'):
                    base_url = '/'.join(m3u8_url.split('/')[:-1])
                    ts_url = urljoin(base_url + '/', ts_url)

                ts_filename = os.path.join(output_path, f'segment_{i:04d}.ts')
                ts_files.append(ts_filename)

                if not os.path.exists(ts_filename):
                    print(f"下载片段 {i + 1}/{len(ts_list)}: {ts_url}")
                    ts_response = self.session.get(ts_url, stream=True)
                    with open(ts_filename, 'wb') as f:
                        for chunk in ts_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                else:
                    print(f"片段 {i + 1}/{len(ts_list)} 已存在，跳过下载")

            # 合并ts文件
            output_file = os.path.join(output_path, f"{title}.mp4")
            self.merge_ts_files(ts_files, output_file)

            print(f"视频已保存到: {output_file}")
            return True

        except Exception as e:
            print(f"下载m3u8视频时出错: {e}")
            return False

    def download_mp4(self, mp4_url, title, output_path=None):
        """下载mp4视频"""
        try:
            print(f"尝试下载mp4视频: {mp4_url}")

            # 确定输出目录和文件名
            if not output_path:
                output_path = os.getcwd()
            output_file = os.path.join(output_path, f"{title}.mp4")

            # 下载视频
            response = self.session.get(mp4_url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"下载进度: {progress:.2f}%", end='\r')

            print(f"\n视频已保存到: {output_file}")
            return True

        except Exception as e:
            print(f"下载mp4视频时出错: {e}")
            return False

    def merge_ts_files(self, ts_files, output_file):
        """合并ts文件"""
        try:
            # 使用ffmpeg合并ts文件
            if self.has_ffmpeg():
                # 创建文件列表
                list_file = output_file + '_list.txt'
                with open(list_file, 'w') as f:
                    for ts_file in ts_files:
                        f.write(f"file '{os.path.abspath(ts_file)}'\n")

                # 使用ffmpeg合并
                cmd = [
                    'ffmpeg', '-f', 'concat', '-safe', '0',
                    '-i', list_file, '-c', 'copy', output_file
                ]

                subprocess.run(cmd, check=True)
                os.remove(list_file)

                # 删除临时ts文件
                for ts_file in ts_files:
                    os.remove(ts_file)
            else:
                # 简单的二进制合并
                with open(output_file, 'wb') as outfile:
                    for ts_file in ts_files:
                        with open(ts_file, 'rb') as infile:
                            outfile.write(infile.read())
                        os.remove(ts_file)

            return True

        except Exception as e:
            print(f"合并ts文件时出错: {e}")
            return False

    def has_ffmpeg(self):
        """检查系统是否安装了ffmpeg"""
        try:
            subprocess.run(['ffmpeg', '-version'],
                           capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


# 使用示例
if __name__ == "__main__":
    downloader = VideoDownloader()
    url = "https://www.duse1.com/play/219290-37-355507.html"  # 替换为目标URL

    # 下载视频
    success = downloader.download_video(url)

    if success:
        print("视频下载成功!")
    else:
        print("视频下载失败!")