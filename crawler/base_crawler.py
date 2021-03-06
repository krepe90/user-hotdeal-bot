from abc import ABCMeta, abstractmethod
from typing import Any, Dict, List, Optional, TypedDict, Union
import aiohttp
import logging


class CrawlerExcpetion(Exception):
    pass


class BaseArticle(TypedDict):
    article_id: int             # 게시글 번호
    title: str                  # 게시글 제목
    category: str               # 게시글 카테고리
    site_name: str              # 커뮤니티 사이트 이름
    board_name: str             # 게시판 이름
    writer_name: str            # 작성자 이름 (닉네임)
    url: str                    # 게시글 URL
    is_end: bool                # 핫딜 종료 여부
    extra: Dict[str, Any]       # 기타 데이터 저장용
    message: Dict[str, Any]     # 각 메시지 전송 채널별 메시지 객체


class BaseCrawler(metaclass=ABCMeta):
    def __init__(self, url_list: List[str], session: Optional[aiohttp.ClientSession] = None) -> None:
        self.session: aiohttp.ClientSession = session if session is not None else aiohttp.ClientSession(trust_env=True)
        self.url_list: List[str] = url_list
        self.logger = logging.getLogger(f"crawler.{self.__class__.__name__}")
        self._prev_status = 200

    async def get(self) -> Dict[int, BaseArticle]:
        html_list: List[str] = []
        for url in self.url_list:
            if (html := await self.request(url)):
                html_list.append(html)

        data: Dict[int, BaseArticle] = {}
        for html in html_list:
            data.update(await self.parsing(html))

        return data

    async def _request(self, url: str, retry: bool = True) -> Union[aiohttp.ClientResponse, None]:
        # 함수 이름을 제멋대로 대충 지어버리는 사람
        self.logger.debug(f"Send request to {url}")
        try:
            resp = await self.session.get(url)
        except aiohttp.ServerTimeoutError as e:
            self.logger.error(f"Client connection timeout error: {e} ({url})")
            return
        except aiohttp.ClientError as e:
            if retry:
                self.logger.warning(f"Re-send request to {url}")
                resp = await self._request(url, False)
            else:
                self.logger.error(f"Client connection error: {e} ({url})")
                return
        return resp

    async def request(self, url: str) -> Union[str, None]:
        if (resp := await self._request(url)) is None:
            return

        async with resp:
            if resp.status != 200:
                if resp.status != self._prev_status:
                    self.logger.error(f"Client response error: {resp.status} ({url})")
                else:
                    self.logger.info(f"Client response error [skip]: {resp.status} ({url})")
                self._prev_status = resp.status
                return
            else:
                self._prev_status = resp.status

            try:
                await resp.read()
                if (encoding := resp.get_encoding()) == "euc-kr":
                    encoding = "cp949"
                html = await resp.text(encoding=encoding)
            except Exception as e:
                self.logger.exception("Cannot get response html string")
                return
        return html

    @abstractmethod
    async def parsing(self, html: str) -> Dict[int, BaseArticle]:
        pass

    async def close(self):
        await self.session.close()
