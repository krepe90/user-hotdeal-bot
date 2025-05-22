import random

import aiohttp

from .base_crawler import ArticleCollection, BaseArticle, BaseCrawler


class DummyCrawler(BaseCrawler):
    def __init__(self, name: str, url_list: list[str], session: aiohttp.ClientSession | None = None) -> None:
        super().__init__(name, url_list, session)
        self.start = 1
        self.dummy_data = {i: self._generate_article_object(i) for i in range(self.start, self.start + 10)}

    async def get(self) -> ArticleCollection:
        # 2개 게시글 새로 생성
        new = self._generate_article_object(max(list(self.dummy_data.keys())) + 1)
        new2 = self._generate_article_object(max(list(self.dummy_data.keys())) + 2)
        # 가장 오래된 게시글 1개 삭제
        self.dummy_data.pop(min(list(self.dummy_data.keys())))
        # 무작위 중간에 낀 게시글 1개 삭제
        self.dummy_data.pop(random.choice(sorted(list(self.dummy_data.keys()))[:-1]))
        # 아무거나 하나 잡고 수정
        rand_target = random.choice(list(self.dummy_data.keys()))
        self.dummy_data[rand_target]["title"] += "!"
        # 목록에 추가
        self.dummy_data[new["article_id"]] = new
        self.dummy_data[new2["article_id"]] = new2
        # 정렬 후 반환
        return ArticleCollection({k: self.dummy_data[k].copy() for k in sorted(self.dummy_data.keys())})

    async def parsing(self, html: str) -> dict[int, BaseArticle]:
        return {}

    def _generate_article_object(self, n: int):
        return BaseArticle(
            article_id=n,
            title=f"Dummy Article {n}",
            category="Dummy",
            site_name="Dummy",
            board_name="Dummy",
            writer_name="Dummy",
            crawler_name=self.name,
            url=f"https://example.com/{n}",
            is_end=False,
            extra={},
        )
