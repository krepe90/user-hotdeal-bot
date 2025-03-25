import asyncio
import json
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
        headers=HEADERS, trust_env=True, timeout=aiohttp.ClientTimeout(total=10)
    )
    yield session
    await session.close()


def validate_article_collection(data: crawler.ArticleCollection):
    assert len(data) > 0

    for article_id, article in data.items():
        assert isinstance(article_id, int)
        assert isinstance(article, dict)
        assert "title" in article
        assert "url" in article
        assert article["url"].startswith("http")
        assert "category" in article


@pytest.mark.skip("blocked by cloudflare")
@pytest.mark.asyncio
async def test_crawler_arca(session):
    """아카라이브 핫딜 채널 크롤링 테스트 수행"""
    crawler_instance = crawler.ArcaLiveCrawler(
        "arcalive_hotdeal", ["https://arca.live/b/hotdeal"], session=session
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_ppomppu(session):
    """뽐뿌 뽐뿌게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.PpomppuCrawler(
        "ppomppu_crawler",
        ["https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"],
        session=session,
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_ppomppu_rss(session):
    """뽐뿌 뽐뿌게시판 RSS 크롤링 테스트 수행"""
    crawler_instance = crawler.PpomppuRSSCrawler(
        "ppomppu_rss_crawler",
        ["https://www.ppomppu.co.kr/rss.php?id=ppomppu"],
        session=session,
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_ruliweb(session):
    """루리웹 예구핫딜 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.RuliwebCrawler(
        "ruliweb_crawler",
        ["https://bbs.ruliweb.com/market/board/1020?view=thumbnail"],
        session=session,
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)

    for article in data.values():
        assert not article["category"].startswith("[")
        assert not article["category"].endswith("]")


@pytest.mark.asyncio
async def test_crawler_clien(session):
    """클리앙 알뜰구매 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.ClienCrawler(
        "clien_crawler", ["https://www.clien.net/service/board/jirum"], session=session
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_coolenjoy_rss(session):
    """쿨엔조이 지름/알뜰정보 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.CoolenjoyRSSCrawler(
        "coolenjoy_rss_crawler",
        ["https://coolenjoy.net/bbs/rss.php?bo_table=jirum"],
        session=session,
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_damoang(session):
    """다모앙 알뜰구매 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.DamoangCrawler(
        "damoang_crawler", ["https://damoang.net/economy"], session=session
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_quasarzone(session):
    """퀘이사존 핫딜 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.QuasarzoneCrawler(
        "quasarzone_crawler",
        ["https://quasarzone.com/bbs/qb_saleinfo"],
        session=session,
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_fmkorea(session):
    """에펨코리아 핫딜 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.FmkoreaCrawler(
        "fmkorea_crawler", ["https://www.fmkorea.com/hotdeal"], session=session
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_zod(session):
    """ZOD 특가 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.ZodCrawler(
        "zod_crawler", ["https://zod.kr/deal"], session=session
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)
