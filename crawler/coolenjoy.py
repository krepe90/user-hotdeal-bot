# https://coolenjoy.net/bbs/jirum
# https://coolenjoy.net/rss?bo_table=jirum (RSS)
import re
from bs4 import BeautifulSoup
from html import unescape
from typing import Dict
from xml.etree import ElementTree


from .base_crawler import BaseArticle, BaseCrawler


class CoolenjoyCrawler(BaseCrawler):
    async def parsing(self, html: str) -> None:
        pass


class CoolenjoyRSSCrawler(BaseCrawler):
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}

    async def parsing(self, html: str) -> Dict[int, BaseArticle]:
        tree = ElementTree.fromstring(html)
        if (_board_name := tree.find("./channel/title")) is None or _board_name.text is None:
            self.logger.error("Can't find board name.")
            return {}
        board_name = unescape(_board_name.text).split(">")[-1].strip()
        rows = tree.findall("./channel/item")

        data: Dict[int, BaseArticle] = {}
        for row in rows:
            if (_link_tag := row.find("link")) is None or _link_tag.text is None:
                self.logger.warning("Cannot find article url tag")
                continue
            _url = unescape(_link_tag.text).replace(":443", "")
            if (re_url := re.search(r"\/bbs\/(\w+)\/(\d+)", _url)) is None:
                self.logger.warning("Cannot find board id and article id")
                continue
            # elif  (re_url := re.search(r"/bbs/([\w\d]+)/(\d+)", _url)) is None:
            #     continue
            if (_title_tag := row.find("title")) is None or _title_tag.text is None:
                self.logger.warning("Cannot find article title tag")
                continue
            if _title_tag == "삭제된 글":
                continue
            if (_writer_tag := row.find("dc:creator", self.ns)) is None or _writer_tag.text is None:
                self.logger.warning("Cannot find article writer tag")
                continue
            _id = int(re_url.group(2))
            data[_id] = {
                "article_id": _id,
                "title": _title_tag.text,
                "category": "",             # 카테고리 정보 없음
                "site_name": "쿨앤조이",
                "board_name": board_name,
                "writer_name": _writer_tag.text,
                "crawler_name": self.name,
                "url": f"https://coolenjoy.net/bbs/{re_url.group(1)}/{re_url.group(2)}",
                "is_end": False,
                "extra": {}
            }
        return data
