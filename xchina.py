"""XChina extractor for gallery-dl"""
import ssl
from urllib import request
from urllib.error import URLError, HTTPError
import re
from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import exception
from bs4 import BeautifulSoup
import time
import random

# 禁用SSL证书验证
ssl._create_default_https_context = ssl._create_unverified_context


class XChinaExtractor(Extractor):
    """Base class for XChina extractors"""
    category = "xchina"
    root = "https://xchina.fit"
    directory_fmt = ("{category}", "{subcategory}", "{album_id} - {title}")
    filename_fmt = "{filename}.{extension}"
    archive_fmt = "{album_id}_{num}"

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.album_id = match.group(1)

        # 设置请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Referer": self.root,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        # 设置代理处理器
        self.proxy_handler = request.ProxyHandler({
            "http": "http://127.0.0.1:10809",
            "https": "http://127.0.0.1:10809"
        })

        # 创建开启器
        self.opener = request.build_opener(self.proxy_handler)

        # 添加请求头
        self.opener.addheaders = [(key, value) for key, value in self.headers.items()]

    def items(self):
        try:
            page_html = self._request_page(1)
            soup = BeautifulSoup(page_html, 'html.parser')

            # 提取元数据
            title_elem = soup.select_one(".hero-title .hero-title-item")
            date_elem = soup.select_one(".info-card .item .text:-soup-contains('202')")
            uploader_elem = soup.select_one(".info-card .item .text a")

            # 确定总页数
            total_pages = 1
            pagination = soup.select(".pager-num")
            if pagination:
                last_page_link = pagination[-1].get_text()
                if last_page_link.isdigit():
                    total_pages = int(last_page_link)

            data = {
                "album_id": self.album_id,
                "title": title_elem.get_text().strip() if title_elem else f"XChina Album {self.album_id}",
                "date": date_elem.get_text().strip() if date_elem else None,
                "uploader": uploader_elem.get_text().strip() if uploader_elem else None,
                "count": 0,
                "category": self.category,
                "subcategory": self.subcategory,
            }

            yield Message.Directory, data

            # 处理所有页面以提取图片URL
            image_urls = []
            for page_num in range(1, total_pages + 1):
                if page_num > 1:
                    page_html = self._request_page(page_num)
                    soup = BeautifulSoup(page_html, 'html.parser')

                # 从当前页面提取图片
                image_containers = soup.select(".amateur-image")
                for container in image_containers:
                    image_elem = container.select_one(".img")
                    if not image_elem:
                        continue

                    # 从内联样式中提取图片URL
                    bg_style = image_elem.get("style", "")
                    url_match = re.search(r"background-image:url\(\'([^']+)\'\)", bg_style)
                    if not url_match:
                        url_match = re.search(r'background-image:url\("([^"]+)"\)', bg_style)
                    if not url_match:
                        url_match = re.search(r"background-image:url\(([^)]+)\)", bg_style)

                    if url_match:
                        image_url = url_match.group(1).strip()
                        # 确保URL是完整的
                        if image_url.startswith("//"):
                            image_url = "https:" + image_url
                        elif image_url.startswith("/"):
                            image_url = self.root + image_url
                        image_urls.append(image_url)

            # 为每个URL生成图片数据
            for idx, image_url in enumerate(image_urls, 1):
                image_data = data.copy()
                image_data["count"] = len(image_urls)
                image_data["num"] = idx

                # 从URL中提取文件名和原始扩展名
                filename_parts = image_url.rpartition('/')
                if filename_parts[2]:
                    filename = filename_parts[2].split('?')[0]  # 移除查询参数
                    name_parts = filename.rsplit('.', 1)
                    if len(name_parts) > 1:
                        image_data["filename"] = name_parts[0]
                        original_extension = name_parts[1].lower()  # 获取原始扩展名并转为小写
                    else:
                        image_data["filename"] = filename
                        original_extension = "webp"  # 默认假设为webp
                else:
                    image_data["filename"] = f"{str(idx).zfill(4)}"
                    original_extension = "webp"  # 默认假设为webp

                # 确保设置 extension 字段
                image_data["extension"] = original_extension

                yield Message.Url, image_url, image_data

        except Exception as e:
            raise exception.StopExtraction(f"提取过程中发生错误: {e}")

    def _request_page(self, page_num):
        """请求相册的特定页面"""
        if page_num == 1:
            url = f"{self.root}/amateur/id-{self.album_id}.html"
        else:
            url = f"{self.root}/amateur/id-{self.album_id}/{page_num}.html"

        try:
            # 添加随机延迟以避免请求过于频繁
            time.sleep(random.uniform(1, 10))

            # 使用urllib打开URL
            response = self.opener.open(url)
            html_content = response.read().decode('utf-8')
            return html_content

        except HTTPError as e:
            raise exception.StopExtraction(f"获取页面 {page_num} 失败 (HTTP错误: {e.code} - {e.reason})")
        except URLError as e:
            raise exception.StopExtraction(f"获取页面 {page_num} 失败 (URL错误: {e.reason})")
        except Exception as e:
            raise exception.StopExtraction(f"获取页面 {page_num} 失败: {e}")


class XChinaAmateurExtractor(XChinaExtractor):
    """Extractor for amateur galleries from xchina.fit"""
    subcategory = "amateur"
    pattern = r"(?:https?://)?(?:www\.)?xchina\.fit/amateur/id-([a-z0-9]+)(?:/\d+)?.html"
    example = "https://xchina.fit//amateur/id-68b6d8c3a7e85.html"

    def __init__(self, match):
        XChinaExtractor.__init__(self, match)