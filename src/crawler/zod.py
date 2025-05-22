# zod 특가 게시판
# https://zod.kr/deal
from bs4 import BeautifulSoup

from .base_crawler import BaseArticle, BaseCrawler


class ZodCrawler(BaseCrawler):
    async def parsing(self, html: str) -> dict[int, BaseArticle]:
        soup = BeautifulSoup(html, "html.parser")
        data: dict[int, BaseArticle] = {}

        if (_board_name_tag := soup.select_one(".app-board-title a")) is None:
            self.logger.error("Cannot find board tag.")
            return data
        board_name = _board_name_tag.text.strip()
        board_url = _board_name_tag.attrs["href"]
        board_id = board_url.split("/")[-1]

        list_tag = soup.select_one("#board-list .zod-board-list--deal")
        if list_tag is None:
            self.logger.error("Cannot find list tag.")
            return data
        rows = list_tag.select("li")
        for row in rows:
            if "notice" in row.get("class", []):
                self.logger.debug("Skipping notice row.")
                continue

            article_link = row.select_one("a")
            if not article_link:
                self.logger.error("Cannot find article link.")
                continue

            article_url = article_link.attrs.get("href", "")
            article_id = int(article_url.split("/")[-1]) if article_url else 0

            if not article_url:
                self.logger.error("Cannot find article url.")
                continue

            title_tag = article_link.select_one(".app-list-title-item")
            title = title_tag.text.strip() if title_tag else ""

            category_tag = article_link.select_one(".zod-board--deal-meta-category")
            category = category_tag.text.strip() if category_tag else ""

            writer_tag = article_link.select_one(".app-list-member .tw-inline-flex")
            writer_name = writer_tag.text.strip() if writer_tag else ""

            meta_tags = article_link.select(".app-list-meta.zod-board--deal-meta span")
            extra = {}
            for meta in meta_tags:
                strong_tag = meta.select_one("strong")
                if strong_tag:
                    meta_text = meta.text.strip()
                    if "가격:" in meta_text:
                        extra["price"] = strong_tag.text.strip()
                    elif "배송비:" in meta_text:
                        extra["delivery"] = strong_tag.text.strip()
                    elif strong_tag.text.strip():
                        extra["mall"] = strong_tag.text.strip()

            recommend_tag = article_link.select_one(".app-list__voted-count span")
            if recommend_tag and recommend_tag.text.strip().isdigit():
                extra["recommend"] = int(recommend_tag.text.strip())

            comment_tag = article_link.select_one(".app-list-comment")
            if comment_tag and comment_tag.text.strip().isdigit():
                extra["comment"] = int(comment_tag.text.strip())

            is_end = (
                "종료" in title
                or "품절" in title
                or "zod-board-list--deal-ended" in row.get("class", [])
            )

            base_url = "https://zod.kr"
            full_url = f"{base_url}{article_url}"

            data[article_id] = BaseArticle(
                article_id=article_id,
                title=title,
                category=category,
                site_name="zod",
                board_name=board_name,
                writer_name=writer_name,
                crawler_name=self.name,
                url=full_url,
                is_end=is_end,
                extra=extra,
            )

        return data
