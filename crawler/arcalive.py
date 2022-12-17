# 아카라이브 핫딜 채널
# https://arca.live/b/hotdeal
# API 문서화되면 전환 예정
import asyncio
import re
from typing import Dict
from bs4 import BeautifulSoup

from .base_crawler import BaseCrawler, BaseArticle


class ArcaLiveCrawler(BaseCrawler):
    async def parsing(self, html: str) -> Dict[int, BaseArticle]:
        soup = BeautifulSoup(html, "html.parser")

        # 채널 이름
        if (_board_name := soup.select_one(".board-title .title")) is None or (board_name := _board_name.attrs.get("data-channel-name")) is None:
            self.logger.error("Can't find board name, skip parsing")
            return {}
        

        # 게시글 목록
        if (table := soup.select_one(".list-table")) is None:
            self.logger.error("Can't find article list, skip parsing")
            return {}
        rows = table.select(".vrow.hybrid")

        data: Dict[int, BaseArticle] = {}
        for row in rows:
            # 하나라도 실패할 경우 건너뛰기
            if (_title_tag := row.select_one(".title")) is None:
                self.logger.warning("Cannot get article title tag")
                continue
            if (_title := _title_tag.get_text(strip=True)) is None:
                self.logger.warning("Cannot get article title")
                continue
            else:
                # 제목 뒤의 (가격/배송비) 제거
                title = re.sub(r"(.+) \(\S+\/\S+\)", r"\1", _title)
            if (_url := _title_tag.attrs.get("href")) is None or (re_id := re.match(r"\/b\/([\w\d])+\/(\d+)\??.+", _url)) is None:
                self.logger.warning("Cannot parse article url")
                continue
            else:
                _board_id = re_id.group(1)
                _id = int(re_id.group(2))
            if (_category_tag := row.select_one(".badge")) is None:
                self.logger.warning("Cannot get category tag")
                continue
            if (_writer_tag := row.select_one(".user-info span:first-child")) is None:
                self.logger.warning("Cannot get writer tag")
                continue
            if (_recommend_tag := row.select_one(".col-rate")) is None:
                self.logger.warning("Cannot get recommend value tag")
                continue
            if (_view_tag := row.select_one(".col-view")) is None:
                self.logger.warning("Cannot get view count tag")
                continue
            if (_price_tag := row.select_one(".deal-price")) is None:
                self.logger.warning("Cannot get price tag")
                continue
            if (_delivery_tag := row.select_one(".deal-delivery")) is None:
                self.logger.warning("Cannot get delivery price tag")
                continue
            is_end = True if (row.select_one(".deal-close") is not None) else False

            data[_id] = {
                "article_id": _id,
                "title": title,
                "category": _category_tag.text.strip(),
                "site_name": "아카라이브",
                "board_name": board_name,
                "writer_name": _writer_tag.text.strip(),
                "url": f"https://arca.live/b/{_board_id}/{_id}",
                "is_end": is_end,
                "extra": {
                    "recommend": _recommend_tag.text,
                    "view": _view_tag.text,
                    "price": _price_tag.text.strip(),
                    "delivery": [_delivery_tag.text.strip()]
                },
                "message": {}
            }
        return data
