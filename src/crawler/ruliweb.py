# 유저 예판 핫딜 뽐뿌 게시판 https://bbs.ruliweb.com/market/board/1020
# 유저 예판 핫딜 뽐뿌 게시판 (RSS) https://bbs.ruliweb.com/market/board/1020/rss

from bs4 import BeautifulSoup, NavigableString, Tag

from .base_crawler import BaseArticle, BaseCrawler


class RuliwebCrawler(BaseCrawler):
    async def parsing(self, html: str) -> dict[int, BaseArticle]:
        soup = BeautifulSoup(html, "html.parser")
        # 게시판 이름
        if (_board_name := soup.select_one("#board_name")) is None:
            self.logger.error("Can't find board name, skip parsing")
            return {}
        board_name = _board_name.text.strip()
        # 게시글 목록
        if (table := soup.select_one("table.board_list_table")) is None:
            self.logger.error("Can't find article list, skip parsing")
            return {}
        rows = table.select("tr.table_body.normal:not(.best, .notice)")

        data: dict[int, BaseArticle] = {}
        for row in rows:
            # 하나라도 실패할 경우 건너뛰기
            if (_id_tag := row.select_one(".info_article_id")) is None or not _id_tag.attrs.get("value", "").isnumeric():
                self.logger.warning("Cannot get article id tag")
                continue
            if (_title_tag := row.select_one(".title_wrapper")) is None:
                self.logger.warning("Cannot get article title tag")
                continue
            _category_el = _title_tag.next_element
            if not isinstance(_category_el, NavigableString):
                self.logger.warning("Cannot get category tag")
                continue
            category = _category_el.strip(" \t\n[]")
            _title_text_tag = _title_tag.find_next("a")
            if not isinstance(_title_text_tag, Tag):
                self.logger.warning("Cannot get title text tag")
                continue
            title = _title_text_tag.text.strip()
            if (_writer_tag := row.select_one(".nick a")) is None:
                self.logger.warning("Cannot get writer tag")
                continue
            if (_recommend_tag := row.select_one(".recomd > strong")) is None:
                self.logger.warning("Cannot get recommend value tag")
                continue
            if (_view_tag := row.select_one(".hit > strong")) is None:
                self.logger.warning("Cannot get view count tag")
                continue
            # 섬네일 모드 보기 기준 (제목 길이 제한 떄문에;;)
            _id = int(_id_tag.attrs["value"])
            data[_id] = {
                "article_id": _id,
                "title": title,
                "category": category,
                "site_name": "루리웹",
                "board_name": board_name,
                "writer_name": _writer_tag.text.strip(),
                "crawler_name": self.name,
                "url": f"https://bbs.ruliweb.com/market/board/1020/read/{_id}",
                "is_end": False,
                "extra": {
                    "recommend": _recommend_tag.text,
                    "view": _view_tag.text,
                }
            }
            # 제목에 ["품절", "종료", "매진", "마감"] 네 단어가 들어간 경우 핫딜이 종료된 것으로 판단
            for kw in ["품절", "종료", "매진", "마감"]:
                if kw in data[_id]["title"]:
                    data[_id]["is_end"] = True
                    break
            else:
                data[_id]["is_end"] = False
        return data
