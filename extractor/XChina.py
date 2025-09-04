"""XChina extractor for gallery-dl"""
from gallery_dl.extractor.common import Extractor, Message
from gallery_dl import text, util, exception
import re
from bs4 import BeautifulSoup


class XChinaExtractor(Extractor):
    """Base class for XChina extractors"""
    category = "xchina"
    root = "https://xchina.co"

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.album_id = match.group(1)
        self.session.headers['Referer'] = self.root
        self.session.headers['User-Agent'] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )

    def items(self):
        page = self._request_page(1)
        soup = BeautifulSoup(page, 'html.parser')

        # Extract metadata
        title_elem = soup.select_one(".hero-title .hero-title-item")
        date_elem = soup.select_one(".info-card .item .text:contains('202')")
        uploader_elem = soup.select_one(".info-card .item .text a")

        # Determine total pages
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
        }

        yield Message.Directory, data

        # Process all pages to extract image URLs
        image_urls = []
        for page_num in range(1, total_pages + 1):
            if page_num > 1:
                page_html = self._request_page(page_num)
                soup = BeautifulSoup(page_html, 'html.parser')

            # Extract images from current page
            image_containers = soup.select(".amateur-image")
            for container in image_containers:
                image_elem = container.select_one(".img")
                if not image_elem:
                    continue

                # Extract image URL from inline style
                bg_style = image_elem.get("style", "")
                url_match = re.search(r"background-image:url('([^']+)')", bg_style)
                if not url_match:
                    url_match = re.search(r"background-image:url("([ ^ "]+)")
                    ", bg_style)
                    if not url_match:
                        url_match = re.search(r"background-image:url(([^)]+))", bg_style)

                    if url_match:
                        image_url = url_match.group(1).strip()
                    image_urls.append(image_url)

                    # Generate image data for each URL
                    for idx, image_url in enumerate(image_urls, 1):
                        image_data = data.copy()
                    image_data["count"] = len(image_urls)
                    image_data["num"] = idx
                    image_data["filename"] = f"{str(idx).zfill(4)}"
                    image_data["extension"] = image_url.rpartition('.')[2]

                    yield Message.Url, image_url, image_data

    def _request_page(self, page_num):
        """Request a specific page of the album"""
        if page_num == 1:
            url = f"{self.root}/amateur/id-{self.album_id}.html"
        else:
            url = f"{self.root}/amateur/id-{self.album_id}/{page_num}.html"

        response = self.request(url)
        if response.status_code >= 400:
            raise exception.StopExtraction(f"Failed to get page {page_num} (status code: {response.status_code})")
        return response.text


class XChinaAmateurExtractor(XChinaExtractor):
    """Extractor for amateur galleries from xchina.co"""
    subcategory = "amateur"
    directory_fmt = ["{category}", "{subcategory}", "{album_id} - {title}"]
    filename_fmt = "{filename}.{extension}"
    archive_fmt = "{album_id}_{num}"
    pattern = r"(?:https?://)?(?:www.)?xchina.co/amateur/id-([a-z0-9]+)(?:/d+)?.html"
    test = [
        ("https://xchina.co/amateur/id-68b6d8c3a7e85.html", {
            "pattern": r"https://img.xchina.io/amateurs/68b6d8c3a7e85/d+.webp",
            "count": ">=16"
        }),
    ]