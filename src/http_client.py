import asyncio
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import aiohttp
from aiohttp.resolver import AsyncResolver
from curl_cffi import AsyncSession, CurlOpt
from curl_cffi.requests.exceptions import RequestException as CurlRequestException
from curl_cffi.requests.exceptions import Timeout as CurlTimeout

CLOUDFLARE_DNS_SERVERS = ("1.1.1.1", "1.0.0.1")
CLOUDFLARE_DOH_URL = "https://cloudflare-dns.com/dns-query"
DNS_CACHE_TTL_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 20


class HttpClientError(Exception):
    """HTTP 요청 처리 중 발생한 전송 계층 오류."""


class HttpTimeoutError(HttpClientError):
    """HTTP 요청 제한 시간을 초과한 경우."""


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """HTTP 클라이언트 구현과 무관한 공통 응답."""

    status: int
    body: bytes
    headers: Mapping[str, str]
    url: str
    charset: str | None = None

    def text(self) -> str:
        """응답 본문을 선언된 문자 인코딩으로 디코딩한다."""
        encoding = self.charset or "utf-8"
        if encoding.lower().replace("_", "-") == "euc-kr":
            encoding = "cp949"
        return self.body.decode(encoding)


class HttpClient(Protocol):
    """크롤러가 사용하는 비동기 HTTP 클라이언트 계약."""

    @property
    def closed(self) -> bool: ...

    async def get(self, url: str, *, allow_redirects: bool = False) -> HttpResponse: ...

    async def close(self) -> None: ...


class CloudflareDNSConnector(aiohttp.TCPConnector):
    """Cloudflare DNS를 사용하고 세션 종료 시 resolver도 함께 닫는 커넥터."""

    def __init__(self, **kwargs: Any) -> None:
        self._cloudflare_resolver = AsyncResolver(nameservers=list(CLOUDFLARE_DNS_SERVERS))
        self._cloudflare_resolver_closed = False
        super().__init__(
            resolver=self._cloudflare_resolver,
            ttl_dns_cache=DNS_CACHE_TTL_SECONDS,
            **kwargs,
        )

    @property
    def dns_resolver(self) -> AsyncResolver:
        return self._cloudflare_resolver

    def close(self) -> Awaitable[None]:
        connector_close = super().close()
        if self._cloudflare_resolver_closed:
            return connector_close

        self._cloudflare_resolver_closed = True

        async def close_connector_and_resolver() -> None:
            try:
                await connector_close
            finally:
                await self._cloudflare_resolver.close()

        return close_connector_and_resolver()


def create_aiohttp_session(**kwargs: Any) -> aiohttp.ClientSession:
    """Cloudflare DNS를 사용하는 aiohttp 세션을 생성한다."""
    return aiohttp.ClientSession(connector=CloudflareDNSConnector(), **kwargs)


class AiohttpClient:
    """aiohttp 기반의 일반 HTTP 클라이언트 구현."""

    def __init__(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        trust_env: bool = True,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._session = (
            session
            if session is not None
            else create_aiohttp_session(
                headers=headers,
                trust_env=trust_env,
                timeout=aiohttp.ClientTimeout(total=timeout),
            )
        )

    @property
    def closed(self) -> bool:
        return self._session.closed

    async def get(self, url: str, *, allow_redirects: bool = False) -> HttpResponse:
        try:
            response = await self._session.get(url, allow_redirects=allow_redirects)
            try:
                body = await response.read()
                return HttpResponse(
                    status=response.status,
                    body=body,
                    headers=dict(response.headers),
                    url=str(response.url),
                    charset=response.charset,
                )
            finally:
                response.release()
        except (aiohttp.ServerTimeoutError, asyncio.TimeoutError) as e:
            raise HttpTimeoutError(str(e)) from e
        except aiohttp.ClientError as e:
            raise HttpClientError(str(e)) from e

    async def close(self) -> None:
        if not self.closed:
            await self._session.close()


class CurlCffiClient:
    """curl_cffi 기반의 브라우저 지문 위장 HTTP 클라이언트 구현."""

    def __init__(
        self,
        *,
        impersonate: str = "chrome",
        trust_env: bool = True,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        session: AsyncSession | None = None,
    ) -> None:
        self._closed = False
        self._session = (
            session
            if session is not None
            else AsyncSession(
                impersonate=impersonate,
                trust_env=trust_env,
                timeout=timeout,
                curl_options={CurlOpt.DOH_URL: CLOUDFLARE_DOH_URL},
            )
        )

    @property
    def closed(self) -> bool:
        return self._closed

    async def get(self, url: str, *, allow_redirects: bool = False) -> HttpResponse:
        try:
            response = await self._session.get(url, allow_redirects=allow_redirects)
        except CurlTimeout as e:
            raise HttpTimeoutError(str(e)) from e
        except CurlRequestException as e:
            raise HttpClientError(str(e)) from e

        return HttpResponse(
            status=response.status_code,
            body=response.content,
            headers=dict(response.headers),
            url=str(response.url),
            charset=response.charset_encoding,
        )

    async def close(self) -> None:
        if self.closed:
            return
        self._closed = True
        await self._session.close()


def create_default_http_client() -> HttpClient:
    """애플리케이션과 단독 크롤러에서 사용할 기본 HTTP 클라이언트를 생성한다."""
    return CurlCffiClient()
