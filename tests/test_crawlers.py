import pytest
import pytest_asyncio
import aiohttp

from src import crawler


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}


@pytest_asyncio.fixture
async def session():
    session = aiohttp.ClientSession(
        headers=HEADERS,
        trust_env=True,
        timeout=aiohttp.ClientTimeout(total=10)
    )
    yield session
    await session.close()


@pytest.mark.asyncio
async def test_crawler_arca(session):
    crawler_instance = crawler.ArcaLiveCrawler("arcalive_hotdeal", ["https://arca.live/b/hotdeal"], session=session)
    data: crawler.ArticleCollection = await crawler_instance.get()
    assert len(data) > 0


@pytest.mark.asyncio
async def test_cralwer_ppomppu(session):
    crawler_instance = crawler.PpomppuCrawler("ppomppu_crawler", ["https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"], session=session)
    data: crawler.ArticleCollection = await crawler_instance.get()
    assert len(data) > 0
