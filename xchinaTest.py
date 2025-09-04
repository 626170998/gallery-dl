import ssl
from urllib import request
from urllib.error import URLError, HTTPError
import re
from bs4 import BeautifulSoup
import time
import random

# 禁用SSL证书验证
ssl._create_default_https_context = ssl._create_unverified_context


def test_extractor_with_urllib(url):
    """使用 urllib 和代理的 XChina 提取器测试函数"""
    match = re.search(r"id-([a-z0-9]+)", url)
    if not match:
        print("无法从 URL 中提取专辑 ID")
        return

    album_id = match.group(1)
    print(f"正在测试专辑 ID: {album_id}")

    # 设置请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Referer": "https://xchina.co/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    # 设置代理处理器
    proxy_handler = request.ProxyHandler({
        "http": "http://127.0.0.1:10809",
        "https": "http://127.0.0.1:10809"
    })

    # 创建开启器
    opener = request.build_opener(proxy_handler)

    # 添加请求头
    opener.addheaders = [(key, value) for key, value in headers.items()]

    try:
        # 打开URL
        response = opener.open(url)
        html_content = response.read().decode('utf-8')

        print("页面访问成功!")

        # 解析HTML内容
        soup = BeautifulSoup(html_content, "html.parser")

        # 提取标题
        title_elem = soup.select_one(".hero-title .hero-title-item")
        title = title_elem.get_text().strip() if title_elem else "未找到标题"
        print(f"标题: {title}")

        # 查找图片容器
        image_containers = soup.select(".amateur-image")
        print(f"找到 {len(image_containers)} 个图片容器")

        # 提取图片URL
        image_urls = []
        for container in image_containers[:3]:  # 只获取前三个
            image_elem = container.select_one(".img")
            if not image_elem:
                continue

            bg_style = image_elem.get("style", "")
            # 尝试多种匹配模式
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
                    image_url = "https://xchina.co" + image_url
                image_urls.append(image_url)

        # 显示提取到的图片URL
        if image_urls:
            print("成功提取图片URL示例:")
            for i, url in enumerate(image_urls, 1):
                print(f"{i}: {url}")
        else:
            print("未能提取任何图片URL")
            if image_containers:
                print("可疑的style属性内容:",
                      image_containers[0].select_one(".img").get("style", "") if image_containers[0].select_one(
                          ".img") else "N/A")

        # 保存HTML内容供调试
        with open(f"debug_page_{album_id}.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"页面内容已保存到 debug_page_{album_id}.html")

    except HTTPError as e:
        print(f"HTTP错误: {e.code} - {e.reason}")
        if e.code == 403:
            print("检测到可能的Cloudflare安全挑战")
    except URLError as e:
        print(f"URL错误: {e.reason}")
    except Exception as e:
        print(f"发生未知错误: {e}")


# 调用测试函数
test_url = "https://xchina.co/amateur/id-68b6d8c3a7e85.html"
test_extractor_with_urllib(test_url)