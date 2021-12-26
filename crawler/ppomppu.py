# 뽐뿌 게시판 https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu
# 해외뽐뿌 게시판 https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu4
import asyncio
from html import unescape
import re
from typing import Dict
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ElementTree

from .base_crawler import BaseCrawler, BaseArticle


class PpomppuCrawler(BaseCrawler):
    async def parsing(self, html: str) -> Dict[int, BaseArticle]:
        soup = BeautifulSoup(html, "html.parser")
        if (_board_name := soup.select_one(".bbs_title h1 a")) is None:
            self.logger.error("Can't find board name.")
            return {}
        if (_board_url := soup.select_one("input[name=id]")) is None:
            self.logger.error("Can't find board url.")
            return {}
        if (table := soup.select_one("table#revolution_main_table")) is None:
            self.logger.error("Can't find article list.")
            return {}
        board_name = _board_name.text.strip()
        board_url = _board_url.attrs["value"]
        rows = table.select("tr.list0, tr.list1")

        data: Dict[int, BaseArticle] = {}
        for row in rows:
            if (_id_tag := row.select_one("td:nth-child(1)")) is None or not _id_tag.text.strip().isnumeric():
                # 뽐뿌 사이트 구조가 이상해서 임시로 로깅 비활성화
                # self.logger.warning("Cannot get article id tag")
                continue
            if (_title_tag := row.select_one("font")) is None:
                self.logger.warning("Cannot get article title tag")
                continue
            if (_writer_tag := row.select_one(".list_name")) is None:
                self.logger.warning("Cannot get article wrtier tag")
                continue
            if (_recommend_tag := row.select_one("td:nth-child(5)")) is None:
                self.logger.warning("Cannot get article recommend tag")
                continue
            if (_view_tag := row.select_one("td:nth-child(6)")) is None:
                self.logger.warning("Cannot get article view count tag")
                continue
            if (_category_tag := row.select_one("td:nth-child(3) tr td div > *:nth-last-child(1)")) is None or not _category_tag.text:
                self.logger.warning("Cannot get category tag")
                continue
            _id = int(_id_tag.text.strip())
            # 게시글 번호가 없는 경우 (== 다른 게시판 글인 경우) 스킵
            data[_id] = {
                "article_id": _id,
                "title": _title_tag.text.strip(),
                "category": _category_tag.text.strip(" []"),
                "site_name": "뽐뿌",
                "board_name": board_name,
                "writer_name": _writer_tag.text.strip(),
                "url": f"https://www.ppomppu.co.kr/zboard/view.php?id={board_url}&no={_id}",
                "is_end": row.select_one("font.list_title") is None,
                "extra": {
                    "recommend": _recommend_tag.text,
                    "view": _view_tag.text,
                },
                "message": {}
            }
        return data


class PpomppuRSSCrawler(BaseCrawler):
    async def parsing(self, html: str) -> Dict[int, BaseArticle]:
        tree = ElementTree.fromstring(html)
        if (_board_title_tag := tree.find("./channel/title")) is None or (_board_title := _board_title_tag.text) is None:
            self.logger.error("Can't find board name.")
            return {}
        board_name = _board_title.split("-")[-1].strip()
        rows = tree.findall("./channel/item")

        data: Dict[int, BaseArticle] = {}
        for row in rows:
            if (_url_tag := row.find("link")) is None or _url_tag.text is None:
                self.logger.warning("Cannot get article url")
                continue
            if (_re_url := re.search(r"id=([\w\d]+)&no=(\d+)", _url_tag.text)) is None:
                self.logger.warning("Cannot get board id and article id")
                continue
            if (_title_tag := row.find("title")) is None or _title_tag.text is None:
                self.logger.warning("Cannot get article title")
                continue
            if (_writer_tag := row.find("author")) is None or _writer_tag.text is None:
                self.logger.warning("Cannot get article author")
                continue
            if (_hits_tag := row.find("hits")) is None or _hits_tag.text is None:
                self.logger.warning("Cannot get hits info")
                continue
            board_url: str = _re_url.group(1)
            _id: int = int(_re_url.group(2))
            comments, view, recommend, not_recommend = _hits_tag.text.strip("[]").split("|", 3)
            data[_id] = {
                "article_id": _id,
                "title": _title_tag.text,
                "category": "",         # 카테고리 정보 없음
                "site_name": "뽐뿌",
                "board_name": board_name,
                "writer_name": _writer_tag.text,
                "url": f"https://www.ppomppu.co.kr/zboard/view.php?id={board_url}&no={_id}",
                "is_end": False,
                "extra": {
                    "comments": comments,
                    "view": view,
                    "recommend": recommend,
                    "not_recommend": not_recommend
                },
                "message": {}
            }
        return data
