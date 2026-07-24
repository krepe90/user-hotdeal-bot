import pytest
import pytest_asyncio

from src import crawler
from src.http_client import CurlCffiClient


@pytest_asyncio.fixture
async def client():
    client = CurlCffiClient(timeout=10)
    yield client
    await client.close()


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
async def test_crawler_arca(client):
    """아카라이브 핫딜 채널 크롤링 테스트 수행"""
    crawler_instance = crawler.ArcaLiveCrawler("arcalive_hotdeal", ["https://arca.live/b/hotdeal"], client=client)
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_ppomppu(client):
    """뽐뿌 뽐뿌게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.PpomppuCrawler(
        "ppomppu_crawler",
        ["https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"],
        client=client,
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_ppomppu_rss(client):
    """뽐뿌 뽐뿌게시판 RSS 크롤링 테스트 수행"""
    crawler_instance = crawler.PpomppuRSSCrawler(
        "ppomppu_rss_crawler",
        ["https://www.ppomppu.co.kr/rss.php?id=ppomppu"],
        client=client,
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_ruliweb(client):
    """루리웹 예구핫딜 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.RuliwebCrawler(
        "ruliweb_crawler",
        ["https://bbs.ruliweb.com/market/board/1020?view=thumbnail"],
        client=client,
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)

    for article in data.values():
        assert not article["category"].startswith("[")
        assert not article["category"].endswith("]")


@pytest.mark.asyncio
async def test_crawler_clien(client):
    """클리앙 알뜰구매 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.ClienCrawler(
        "clien_crawler", ["https://www.clien.net/service/board/jirum"], client=client
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_coolenjoy_rss(client):
    """쿨엔조이 지름/알뜰정보 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.CoolenjoyRSSCrawler(
        "coolenjoy_rss_crawler",
        ["https://coolenjoy.net/bbs/rss.php?bo_table=jirum"],
        client=client,
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_damoang(client):
    """다모앙 알뜰구매 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.DamoangCrawler("damoang_crawler", ["https://damoang.net/economy"], client=client)
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_quasarzone(client):
    """퀘이사존 핫딜 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.QuasarzoneCrawler(
        "quasarzone_crawler",
        ["https://quasarzone.com/bbs/qb_saleinfo"],
        client=client,
    )
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_fmkorea(client):
    """에펨코리아 핫딜 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.FmkoreaCrawler("fmkorea_crawler", ["https://www.fmkorea.com/hotdeal"], client=client)
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)


@pytest.mark.asyncio
async def test_crawler_zod(client):
    """ZOD 특가 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.ZodCrawler("zod_crawler", ["https://zod.kr/deal"], client=client)
    data: crawler.ArticleCollection = await crawler_instance.get()
    validate_article_collection(data)
