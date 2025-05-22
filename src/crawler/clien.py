# 클리앙 알들구매 게시판 https://www.clien.net/service/board/jirum
from bs4 import BeautifulSoup

from .base_crawler import BaseArticle, BaseCrawler


class ClienCrawler(BaseCrawler):
    async def parsing(self, html: str) -> dict[int, BaseArticle]:
        soup = BeautifulSoup(html, "html.parser")
        data: dict[int, BaseArticle] = {}

        if (_board_name := soup.select_one("input#boardName")) is None:
            self.logger.error("Can't find board name.")
            return data
        if (_board_url := soup.select_one("input#boardCd")) is None:
            self.logger.error("Can't find board url.")
            return data
        rows = soup.select(".list_content > .contents_jirum > .list_item.jirum")
        board_name = _board_name.attrs["value"]
        board_url = _board_url.attrs["value"]

        for row in rows:
            if (_title_tag := row.select_one(".list_subject")) is None:
                self.logger.warning("Cannot get article title tag")
                continue
            if "●▅" in _title_tag.attrs["title"]:
                # 시위성 게시글(?) 무시
                continue
            if "난리난" in _title_tag.attrs["title"]:
                # 스팸 게시글 무시
                continue
            if (_writer_tag := row.select_one(".list_author")) is None:
                self.logger.warning("Cannot get article writer tag")
                continue
            if (_view_tag := row.select_one(".list_hit .hit")) is None:
                self.logger.warning("Cannot get article view count tag")
                continue
            if (_category_tag := row.select_one(".icon_keyword")) is None or not _category_tag.text:
                self.logger.warning("Cannot get category tag")
                continue
            _id_str = row.attrs.get("data-board-sn")
            if _id_str is None:
                self.logger.warning("Cannot get article id")
                continue
            _id = int(_id_str)
            _recommend_tag = row.select_one(".list_votes")
            _recommend = _recommend_tag.text.strip() if _recommend_tag else "0"
            data[_id] = {
                "article_id": _id,
                "title": _title_tag.attrs["title"],
                "category": _category_tag.text,
                "site_name": "클리앙",
                "board_name": board_name,
                "writer_name": _writer_tag.text.strip(),
                "crawler_name": self.name,
                "url": f"https://www.clien.net/service/board/{board_url}/{_id}",
                "is_end": "sold_out" in row["class"],
                "extra": {
                    "recommend": _recommend,
                    "view": _view_tag.text
                },
            }
        return data
