# 핫딜 게시판 https://quasarzone.com/bbs/qb_saleinfo
import re

from bs4 import BeautifulSoup, Tag

from .base_crawler import BaseArticle, BaseCrawler


class QuasarzoneMobileCrawler(BaseCrawler):
    # deprecated
    async def parsing(self, html: str) -> dict[int, BaseArticle]:
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

        data: dict[int, BaseArticle] = {}
        for row in rows:
            if (_url_tag := row.select_one(".subject-link")) is None or (_url := _url_tag.attrs.get("href")) is None:
                self.logger.warning("Cannot find article url tag")
                continue
            if (_re_url := re.search(r"/bbs/([\w\d_]+)/views/(\d+)", _url)) is None:
                self.logger.warning("Cannot find board id and article id")
                continue
            # locked article
            if row.select_one(".fa-lock") is not None:
                self.logger.debug("Find locked article, skip")
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
                delivery = " / ".join(n.text.strip() for n in _delivery_tag if n.text.strip())
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
    async def parsing(self, html: str) -> dict[int, BaseArticle]:
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

        data: dict[int, BaseArticle] = {}
        for row in rows:
            if (_url_tag := row.select_one(".subject-link")) is None or (_url := _url_tag.attrs.get("href")) is None:
                self.logger.warning("Cannot find article url tag")
                continue
            if (_re_url := re.search(r"/bbs/([\w\d_]+)/views/(\d+)", _url)) is None:
                self.logger.warning("Cannot find board id and article id")
                continue
            # locked article
            if row.select_one(".fa-lock") is not None:
                self.logger.debug("Find locked article, skip")
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
            if (_info_tag := row.select_one(".market-info-sub p:first-child")) is None:
                self.logger.warning("Cannot get sub info tag")
                continue
            if (_is_end_tag := row.select_one(".label")) and _is_end_tag.text.strip() == "종료":
                is_end = True
            else:
                is_end = False
            _board_id = _re_url.group(1)
            _id = int(_re_url.group(2))
            _info = self.info_tag_parser(_info_tag)
            _category = _info.pop("category", "")
            if not _category:
                self.logger.warning("Cannot get category")
            data[_id] = {
                "article_id": _id,
                "title": _title_tag.text.strip(),
                "category": _category,
                "site_name": "퀘이사존",
                "board_name": board_name,
                "writer_name": _nick_tag.text.strip(),
                "crawler_name": self.name,
                "url": f"https://quasarzone.com/bbs/{_board_id}/views/{_id}",
                "is_end": is_end,
                "extra": {
                    "recommend": _recommend_tag.text.strip(),
                    "view": _view_tag.text.strip(),
                    **_info     # price, delivery, direct_delivery
                }
            }
        return data

    def info_tag_parser(self, el: Tag) -> dict[str, str]:
        """div.market-info-sub p:first-child 받아서 쇼핑몰/가격/배송 데이터 처리해 반환

        Args:
            el (BeautifulSoup): div.market-info-sub p:first-child

        Returns:
            dict[str, str]: 쇼핑몰/가격/배송 데이터
        """
        data = {}
        for e in el.find_all("span", recursive=False):
            if not isinstance(e, Tag):
                continue
            if "category" in e.attrs.get("class", []):
                # 카테고리 태그 - PC/하드웨어
                data["category"] = e.text.strip()
            elif e.find(string=True, recursive=False).strip() == "가격":
                # 가격 태그 - ￦ 121,687 (KRW)
                data["price"] = e.find("span").text.strip()
            elif "brand" in e.attrs.get("class", []):
                # TODO 쇼핑몰 아이콘으로 이름 가져오기
                continue
            elif e.find(string=True, recursive=False).strip() == "직배":
                # 해외 배송 직배 가능 여부 태그 - 가능 / 불가능
                data["direct_delivery"] = True if "가능" in e.text else False
            elif "배송비" in e.text.strip():
                # 배송비 태그 - 배송비 {텍스트}
                data["delivery"] = e.text.replace("배송비", "").strip()
        return data
