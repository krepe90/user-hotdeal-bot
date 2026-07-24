import pytest

from src.crawler.base_crawler import BaseArticle, BaseCrawler
from src.http_client import AiohttpClient, CurlCffiClient, HttpResponse


class FakeAiohttpResponse:
    status = 200
    headers = {"Content-Type": "text/html; charset=euc-kr"}
    url = "https://example.com/aiohttp"
    charset = "euc-kr"

    def __init__(self, body: bytes) -> None:
        self.body = body
        self.released = False

    async def read(self) -> bytes:
        return self.body

    def release(self) -> None:
        self.released = True


class FakeAiohttpSession:
    def __init__(self, response: FakeAiohttpResponse) -> None:
        self.response = response
        self.closed = False
        self.requests: list[tuple[str, bool]] = []

    async def get(self, url: str, *, allow_redirects: bool) -> FakeAiohttpResponse:
        self.requests.append((url, allow_redirects))
        return self.response

    async def close(self) -> None:
        self.closed = True


class FakeCurlResponse:
    status_code = 200
    headers = {"Content-Type": "text/html; charset=utf-8"}
    url = "https://example.com/curl"
    charset_encoding = "utf-8"

    def __init__(self, body: bytes) -> None:
        self.content = body


class FakeCurlSession:
    def __init__(self, response: FakeCurlResponse) -> None:
        self.response = response
        self.closed = False
        self.requests: list[tuple[str, bool]] = []

    async def get(self, url: str, *, allow_redirects: bool) -> FakeCurlResponse:
        self.requests.append((url, allow_redirects))
        return self.response

    async def close(self) -> None:
        self.closed = True


class FakeHttpClient:
    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.closed = False

    async def get(self, url: str, *, allow_redirects: bool = False) -> HttpResponse:
        return self.response

    async def close(self) -> None:
        self.closed = True


class TextCrawler(BaseCrawler):
    async def parsing(self, html: str) -> dict[int, BaseArticle]:
        return {}


@pytest.mark.asyncio
async def test_aiohttp_client_normalizes_response():
    native_response = FakeAiohttpResponse("한글".encode("cp949"))
    native_session = FakeAiohttpSession(native_response)
    client = AiohttpClient(session=native_session)  # type: ignore[arg-type]

    response = await client.get("https://example.com/aiohttp")

    assert response.status == 200
    assert response.text() == "한글"
    assert response.charset == "euc-kr"
    assert native_response.released is True
    assert native_session.requests == [("https://example.com/aiohttp", False)]

    await client.close()
    assert client.closed is True


@pytest.mark.asyncio
async def test_curl_cffi_client_normalizes_response():
    native_session = FakeCurlSession(FakeCurlResponse("본문".encode()))
    client = CurlCffiClient(session=native_session)  # type: ignore[arg-type]

    response = await client.get("https://example.com/curl")

    assert response.status == 200
    assert response.text() == "본문"
    assert response.charset == "utf-8"
    assert native_session.requests == [("https://example.com/curl", False)]

    await client.close()
    assert client.closed is True
    assert native_session.closed is True


@pytest.mark.asyncio
async def test_crawler_does_not_close_injected_client():
    client = FakeHttpClient(
        HttpResponse(
            status=200,
            body="본문".encode(),
            headers={"Content-Type": "text/html; charset=utf-8"},
            url="https://example.com",
            charset="utf-8",
        )
    )
    crawler = TextCrawler("text", ["https://example.com"], client=client)

    assert await crawler.request("https://example.com") == "본문"

    await crawler.close()
    assert client.closed is False


@pytest.mark.asyncio
async def test_crawler_closes_owned_default_client(monkeypatch):
    client = FakeHttpClient(
        HttpResponse(
            status=200,
            body=b"",
            headers={},
            url="https://example.com",
        )
    )
    monkeypatch.setattr("src.crawler.base_crawler.create_default_http_client", lambda: client)
    crawler = TextCrawler("text", [])

    await crawler.close()

    assert client.closed is True
