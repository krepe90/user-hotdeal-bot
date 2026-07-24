import datetime
import logging
import os
from abc import ABCMeta, abstractmethod
from typing import Any, Self, TypedDict

import logfire

from src.http_client import (
    HttpClient,
    HttpClientError,
    HttpResponse,
    HttpTimeoutError,
    create_default_http_client,
)


class CrawlerExcpetion(Exception):
    pass


class BaseArticle(TypedDict):
    article_id: int  # 게시글 번호
    title: str  # 게시글 제목
    category: str  # 게시글 카테고리
    site_name: str  # 커뮤니티 사이트 이름
    board_name: str  # 게시판 이름
    writer_name: str  # 작성자 이름 (닉네임)
    crawler_name: str  # 크롤러 (객체) 이름
    url: str  # 게시글 URL
    is_end: bool  # 핫딜 종료 여부
    extra: dict[str, Any]  # 기타 데이터 저장용


class ArticleCollection(dict[int, BaseArticle]):
    def __init__(self, data: dict[int, BaseArticle] = {}):
        for k, v in data.items():
            self[k] = v

    def __setitem__(self, __key: int | str, __value: BaseArticle) -> None:
        return super().__setitem__(int(__key), __value)

    def __getitem__(self, __key: int) -> BaseArticle:
        return super().__getitem__(__key)

    def __sub__(self, b: Self) -> "ArticleCollection":
        return ArticleCollection({k: v for k, v in self.items() if k not in b})

    def remove_expired(self, i: int) -> None:
        """article_id 값이 i보다 작은 게시글들을 삭제

        Args:
            i (int): 비교할 article_id 값
        """
        # {n: m for n, m in self.article_cache[name].items() if n >= id_min}
        remove_list = [k for k in self.keys() if k < i]
        for k in remove_list:
            self.pop(k)

    def get_new(self, i: int) -> "ArticleCollection":
        """article_id 값이 i보다 큰 게시글들을 모아 새 객체로 반환

        Args:
            i (int): 비교할 article_id 값

        Returns:
            ArticleCollection: 새로운 게시글 모음
        """
        return ArticleCollection({k: v for k, v in self.items() if k > i})


class BaseCrawler(metaclass=ABCMeta):
    def __init__(self, name: str, url_list: list[str], client: HttpClient | None = None) -> None:
        self._owns_client = client is None
        self.client = client if client is not None else create_default_http_client()
        self.url_list: list[str] = url_list
        self.cls_name = self.__class__.__name__
        self.name = name
        self.logger = logging.getLogger(f"crawler.{self.__class__.__name__}")
        self._prev_status = 200

    async def get(self) -> ArticleCollection:
        """게시글 데이터를 크롤링 및 파싱하여 ArticleCollection 객체로 반환

        Returns:
            ArticleCollection: 게시글 목록
        """
        with logfire.span(
            f"crawler_get_{self.name}", crawler_name=self.__class__.__name__, url_count=len(self.url_list)
        ):
            html_list: list[str] = []
            for url in self.url_list:
                if html := await self.request(url):
                    html_list.append(html)

            data = ArticleCollection()
            for html in html_list:
                data.update(await self.parsing(html))

            logfire.info(
                "Crawler completed",
                crawler_name=self.__class__.__name__,
                urls_processed=len(html_list),
                articles_found=len(data),
            )

            return data

    async def _request(self, url: str) -> HttpResponse | None:
        """주입된 HTTP 클라이언트로 GET 요청을 보내고 공통 응답을 반환한다.

        Args:
            url (str): 요청할 URL

        Returns:
            HttpResponse | None: 응답 객체 (실패한 경우 None 반환)
        """
        self.logger.debug("Send request to %s", url)
        try:
            return await self.client.get(url, allow_redirects=False)
        except HttpTimeoutError as e:
            self.logger.error("HTTP request timeout error: %s (%s)", e, url)
            return
        except HttpClientError as e:
            self.logger.error("HTTP client error: %s (%s)", e, url)
            return

    async def request(self, url: str) -> str | None:
        """주어진 URL로부터 HTML 문자열을 반환

        Args:
            url (str): 요청할 URL

        Returns:
            str | None: HTML 문자열 (실패한 경우 None 반환)
        """
        retry_count = 2
        for _ in range(retry_count):
            resp = await self._request(url)
            if resp is not None:
                break
        else:
            self.logger.error("Client connection failed: %s", url)
            return

        if resp.status != 200:
            if resp.status != self._prev_status:
                self.logger.error("Client response error: %s (%s)", resp.status, url)
                await self.dump_http_response(resp)
            else:
                self.logger.info("Client response error [skip]: %s (%s)", resp.status, url)
            self._prev_status = resp.status
            return
        self._prev_status = resp.status

        try:
            return resp.text()
        except (LookupError, UnicodeDecodeError) as e:
            await self.dump_http_response(resp)
            self.logger.error("Cannot decode response body: %s", e)
            return

    @abstractmethod
    async def parsing(self, html: str) -> dict[int, BaseArticle]:
        """HTML 문자열을 파싱하여 게시글 데이터 목록을 반환

        Args:
            html (str): HTML 문자열

        Returns:
            dict[int, BaseArticle]: 게시글 데이터 목록
        """
        pass

    async def close(self):
        """크롤러가 직접 생성한 HTTP 클라이언트를 종료한다."""
        if self._owns_client and not self.client.closed:
            await self.client.close()

    async def dump_http_response(self, resp: HttpResponse) -> None:
        """HTTP 응답을 error/ 폴더에 'YYYYMMDD_HHMMSS_{crawler_name}.html' 형식으로 저장

        Args:
            resp (HttpResponse): 공통 HTTP 응답 객체
        """
        current_datetime = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join("error", f"{current_datetime}_{self.name}.html")

        if not os.path.exists("error"):
            os.makedirs("error")

        with open(filename, "wb") as f:
            f.write(resp.body)
            self.logger.debug("Dumped response binary to %s", filename)
