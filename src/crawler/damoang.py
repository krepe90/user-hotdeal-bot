# 다모앙 알뜰구매 게시판 https://damoang.net/economy
# 다모앙 알뜰구매 게시판 (RSS) https://damoang.net/bbs/rss.php?bo_table=economy
import re

from bs4 import BeautifulSoup

from .base_crawler import BaseArticle, BaseCrawler


class DamoangCrawler(BaseCrawler):
    async def parsing(self, html: str) -> dict[int, BaseArticle]:
        soup = BeautifulSoup(html, "html.parser")
        data: dict[int, BaseArticle] = {}

        if (_board_name := soup.select_one(".page-title")) is None:
            self.logger.error("Can't find board name.")
            return data
        if (_board_url := soup.select_one("input[name=bo_table]")) is None:
            self.logger.error("Can't find board url.")
            return data
        board_name = _board_name.text.strip()
        board_url = _board_url.attrs["value"]
        rows = soup.select("#bo_list .list-group-item:not(.d-none)")

        for row in rows:
            # if (_id_tag := row.select_one(".wr-no")) is None:
            #     # TODO 게시글 고유번호가 아니라 그냥 게시글 번호임;;
            #     self.logger.warning("Cannot get article id tag")
            #     continue
            # if not _id_tag.text.strip().isnumeric():
            #     continue
            if (_title_tag := row.select_one(".flex-fill a")) is None:
                self.logger.warning("Cannot get article title tag")
                continue
            if (_url := _title_tag.attrs.get("href")) is None:
                self.logger.warning("Cannot get article url")
                continue
            if (_re_url := re.search(r"/([\w\d]+)/(\d+)", _url)) is None:
                self.logger.warning("Cannot find board id and article id")
                continue
            if (_writer_tag := row.select_one(".sv_wrap .sv_name")) is None:
                self.logger.warning("Cannot get article wrtier tag")
                continue
            if (_recommend_tag := row.select_one(".rcmd-box")) is None:
                # hidden span tag로 "추천" 글자가 들어있음.
                self.logger.warning("Cannot get article recommend tag")
                continue
            if (_view_tag := row.select_one(".wr-num.order-4")) is None:
                # hidden span tag로 "조회" 글자가 들어있음.
                self.logger.warning("Cannot get article view count tag")
                continue
            if (_status_badge_tag := row.select_one(".badge")) is None:
                self.logger.warning("Cannot get article status badge")
                continue
            _status_badge_tag_text = _status_badge_tag.find(string=True, recursive=False)
            if _status_badge_tag_text is None:
                self.logger.warning("Cannot get article status badge text")
                continue

            _board_id = _re_url.group(1)
            _id = int(_re_url.group(2))
            if _status_badge_tag_text.text.strip() == "종료":
                is_end = True
            else:
                is_end = False
            data[_id] = {
                "article_id": _id,
                "title": _title_tag.text.strip(),
                "category": "",     # 카테고리 없음
                "site_name": "다모앙",
                "board_name": board_name,
                "writer_name": _writer_tag.text.strip(),
                "crawler_name": self.name,
                "url": f"https://damoang.net/{_board_id}/{_id}",
                "is_end": is_end,
                "extra": {
                    "recommend": "".join(_recommend_tag.find_all(string=True, recursive=False)).strip(),
                    "view": "".join(_view_tag.find_all(string=True, recursive=False)).strip(),
                },
            }
        return data
