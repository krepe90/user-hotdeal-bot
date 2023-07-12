# 지름/할인정보 https://quasarzone.com/bbs/qb_saleinfo
import re
from bs4 import BeautifulSoup
from typing import Dict

from .base_crawler import BaseCrawler, BaseArticle


class QuasarzoneMobileCrawler(BaseCrawler):
    # deprecated
    async def parsing(self, html: str) -> Dict[int, BaseArticle]:
        soup = BeautifulSoup(html, "html.parser")
        # 게시판 이름
        if (_board_name := soup.select_one(".page-name")) is None:
            self.logger.error("Can't find board name, skip parsing")
            return {}
        board_name = _board_name.text.strip()
        # 게시글 목록
        if (table := soup.select_one("ul.market-info-type-list")) is None:
            self.logger.error("Can't find article list, skip parsing")
            return {}
        rows = table.select("li")

        data: Dict[int, BaseArticle] = {}
        for row in rows:
            if (_url_tag := row.select_one(".subject-link")) is None or (_url := _url_tag.attrs.get("href")) is None:
                self.logger.warning("Cannot find article url tag")
                continue
            if (_re_url := re.search(r"/bbs/([\w\d_]+)/views/(\d+)", _url)) is None:
                self.logger.warning("Cannot find board id and article id")
                continue
            # locked article
            if row.select_one(".fa-lock") is not None:
                self.logger.debug(f"Find locked article, skip")
                continue
            if (_title_tag := row.select_one(".ellipsis-with-reply-cnt")) is None or not _title_tag.text:
                self.logger.warning("Cannot find article title tag")
                continue
            if (_nick_tag := row.select_one(".nick")) is None or not _nick_tag.attrs.get("data-nick"):
                self.logger.warning("Cannot find article writer tag")
                continue
            if (_recommend_tag := row.select_one(".count:last-child")) is None or not _recommend_tag.text:
                self.logger.warning("Cannot get recommend value tag")
                continue
            if (_view_tag := row.select_one(".count")) is None or not _view_tag.text:
                self.logger.warning("Cannot get view count tag")
                continue
            if (_category_tag := row.select_one(".category")) is None or not _category_tag.text:
                self.logger.warning("Cannot get category tag")
                continue
            if (_price_tag := row.select_one(".market-info-sub .text-orange")) is None:
                self.logger.warning("Cannot get price tag")
                continue
            if not (_delivery_tag := row.select(".market-info-sub > p:nth-child(2) > span:not(.brand)")):
                self.logger.warning("Cannot get delivery info tags")
                continue
            else:
                delivery = [n.text for n in _delivery_tag if n.text]
            if (_is_end_tag := row.select_one(".label")) and _is_end_tag.text.strip() == "종료":
                is_end = True
            else:
                is_end = False
            _board_id = _re_url.group(1)
            _id = int(_re_url.group(2))
            data[_id] = {
                "article_id": _id,
                "title": _title_tag.text.strip(),
                "category": _category_tag.text.strip(),
                "site_name": "퀘이사존",
                "board_name": board_name,
                "writer_name": _nick_tag.text.strip(),
                "crawler_name": self.name,
                "url": f"https://quasarzone.com/bbs/{_board_id}/views/{_id}",
                "is_end": is_end,
                "extra": {
                    "recommend": _recommend_tag.text.strip().replace("추천 : ", ""),
                    "view": _view_tag.text.strip(),
                    "price": _price_tag.text.strip(),
                    "delivery": delivery
                }
            }
        return data


class QuasarzoneCrawler(BaseCrawler):
    async def parsing(self, html: str) -> Dict[int, BaseArticle]:
        soup = BeautifulSoup(html, "html.parser")
        # 게시판 이름
        if (_board_name := soup.select_one(".l-title h2")) is None:
            self.logger.error("Can't find board name, skip parsing")
            return {}
        board_name = _board_name.text.strip()
        # 게시글 목록
        if (table := soup.select_one(".market-info-type-list > table > tbody")) is None:
            self.logger.error("Can't find article list, skip parsing")
            return {}
        rows = table.select("tr")

        data: Dict[int, BaseArticle] = {}
        for row in rows:
            if (_url_tag := row.select_one(".subject-link")) is None or (_url := _url_tag.attrs.get("href")) is None:
                self.logger.warning("Cannot find article url tag")
                continue
            if (_re_url := re.search(r"/bbs/([\w\d_]+)/views/(\d+)", _url)) is None:
                self.logger.warning("Cannot find board id and article id")
                continue
            # locked article
            if row.select_one(".fa-lock") is not None:
                self.logger.debug(f"Find locked article, skip")
                continue
            if (_title_tag := row.select_one(".ellipsis-with-reply-cnt")) is None or not _title_tag.text:
                self.logger.warning("Cannot find article title tag")
                continue
            if (_nick_tag := row.select_one(".nick")) is None or not _nick_tag.attrs.get("data-nick"):
                self.logger.warning("Cannot find article writer tag")
                continue
            if (_recommend_tag := row.select_one("td .num")) is None or not _recommend_tag.text:
                self.logger.warning("Cannot get recommend value tag")
                continue
            if (_view_tag := row.select_one(".count")) is None or not _view_tag.text:
                self.logger.warning("Cannot get view count tag")
                continue
            if (_category_tag := row.select_one(".category")) is None or not _category_tag.text:
                self.logger.warning("Cannot get category tag")
                continue
            if (_price_tag := row.select_one(".market-info-sub .text-orange")) is None:
                self.logger.warning("Cannot get price tag")
                continue
            if not (_delivery_tag := row.select(".market-info-sub > p:nth-child(1) > span:last-child")):
                self.logger.warning("Cannot get delivery info tags")
                continue
            else:
                delivery = [n.text for n in _delivery_tag if n.text]
            if (_is_end_tag := row.select_one(".label")) and _is_end_tag.text.strip() == "종료":
                is_end = True
            else:
                is_end = False
            _board_id = _re_url.group(1)
            _id = int(_re_url.group(2))
            data[_id] = {
                "article_id": _id,
                "title": _title_tag.text.strip(),
                "category": _category_tag.text.strip(),
                "site_name": "퀘이사존",
                "board_name": board_name,
                "writer_name": _nick_tag.text.strip(),
                "crawler_name": self.name,
                "url": f"https://quasarzone.com/bbs/{_board_id}/views/{_id}",
                "is_end": is_end,
                "extra": {
                    "recommend": _recommend_tag.text.strip(),
                    "view": _view_tag.text.strip(),
                    "price": _price_tag.text.strip(),
                    "delivery": delivery
                }
            }
        return data
