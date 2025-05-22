# 에펨코리아 핫딜 게시판 https://www.fmkorea.com/hotdeal
from bs4 import BeautifulSoup

from .base_crawler import BaseArticle, BaseCrawler


class FmkoreaCrawler(BaseCrawler):
    async def parsing(self, html: str) -> dict[int, BaseArticle]:
        soup = BeautifulSoup(html, "html.parser")
        data: dict[int, BaseArticle] = {}
        if (_board_name_tag := soup.select_one(".bd_tl h1 a")) is None:
            self.logger.error("Can't find board name.")
            return data
        board_name = _board_name_tag.text.strip()
        board_url = _board_name_tag.attrs["href"].lstrip("/")
        rows = soup.select("#content .fm_best_widget ul li")

        for row in rows:
            if (_title_tag := row.select_one(".title a")) is None:
                self.logger.warning("Cannot get article title tag")
                continue
            if (_category_tag := row.select_one(".category a")) is None:
                self.logger.warning("Cannot get article category tag")
                continue
            if (_writer_tag := row.select_one(".author")) is None:
                # "/ (이름)" 형식으로 되어있음
                self.logger.warning("Cannot get article writer tag")
                continue

            # 추천, 댓글은 없으면 태그 자체가 없음.
            if (_recommend_tag := row.select_one(".pc_voted_count .count")) is None:
                _recommend = "0"
            else:
                _recommend = _recommend_tag.text.strip()
            if (_comment_tag := row.select_one(".comment_count")) is None:
                _comment = "0"
            else:
                _comment = _comment_tag.text.strip(" \r\n\t[]")
            _extra = self.info_tag_parser(row.select_one(".hotdeal_info"))

            if not (_id_str := _title_tag.attrs["href"].lstrip("/")).isnumeric():
                self.logger.warning("Cannot get article id")
                continue
            _id = int(_id_str)
            is_end = row.select_one(".hotdeal_var8Y") is not None

            data[_id] = {
                "article_id": _id,
                "title": _title_tag.find(string=True, recursive=False).text.strip(),
                "category": _category_tag.text.strip(),
                "site_name": "에펨코리아",
                "board_name": board_name,
                "writer_name": _writer_tag.text.strip(" /\r\n\t"),
                "crawler_name": self.name,
                "url": f"https://www.fmkorea.com/{_id}",
                "is_end": is_end,
                "extra": {
                    "recommend": _recommend,
                    # "rel_url": "",
                    **_extra,
                    "comment": _comment,
                },
            }
        return data

    def info_tag_parser(self, el: BeautifulSoup) -> dict[str, str]:
        # div.hotdeal_info 받아서 쇼핑몰/가격/배송 데이터 처리해 반환
        data = {}
        for e in el.select("span"):
            if "쇼핑몰" in e.text:
                data["brand"] = e.find("a").text.strip()
            elif "가격" in e.text:
                data["price"] = e.find("a").text.strip()
            elif "배송" in e.text:
                data["delivery"] = e.find("a").text.strip()
        return data
