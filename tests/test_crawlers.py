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
    """아카라이브 핫딜 채널 크롤링 테스트 수행"""
    crawler_instance = crawler.ArcaLiveCrawler("arcalive_hotdeal", ["https://arca.live/b/hotdeal"], session=session)
    data: crawler.ArticleCollection = await crawler_instance.get()
    assert len(data) > 0


@pytest.mark.asyncio
async def test_cralwer_ppomppu(session):
    """뽐뿌 뽐뿌게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.PpomppuCrawler("ppomppu_crawler", ["https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"], session=session)
    data: crawler.ArticleCollection = await crawler_instance.get()
    assert len(data) > 0


@pytest.mark.asyncio
async def test_crawler_ppomppu_rss(session):
    """뽐뿌 뽐뿌게시판 RSS 크롤링 테스트 수행"""
    crawler_instance = crawler.PpomppuRSSCrawler("ppomppu_rss_crawler", ["https://www.ppomppu.co.kr/rss.php?id=ppomppu"], session=session)
    data: crawler.ArticleCollection = await crawler_instance.get()
    assert len(data) > 0


@pytest.mark.asyncio
async def test_crawler_ruliweb(session):
    """루리웹 예구핫딜 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.RuliwebCrawler("ruliweb_crawler", ["https://bbs.ruliweb.com/market/board/1020?view=thumbnail"], session=session)
    data: crawler.ArticleCollection = await crawler_instance.get()
    assert len(data) > 0


@pytest.mark.asyncio
async def test_crawler_clien(session):
    """클리앙 알뜰구매 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.ClienCrawler("clien_crawler", ["https://www.clien.net/service/board/jirum"], session=session)
    data: crawler.ArticleCollection = await crawler_instance.get()
    assert len(data) > 0


@pytest.mark.asyncio
async def test_crawler_damoang(session):
    """다모앙 알뜰구매 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.DamoangCrawler("damoang_crawler", ["https://damoang.net/economy"], session=session)
    data: crawler.ArticleCollection = await crawler_instance.get()
    assert len(data) > 0


@pytest.mark.asyncio
async def test_crawler_quasarzone(session):
    """퀘이사존 핫딜 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.QuasarzoneCrawler("quasarzone_crawler", ["https://quasarzone.com/bbs/qb_saleinfo"], session=session)
    data: crawler.ArticleCollection = await crawler_instance.get()
    assert len(data) > 0


@pytest.mark.asyncio
async def test_crawler_fmkorea(session):
    """에펨코리아 핫딜 게시판 크롤링 테스트 수행"""
    crawler_instance = crawler.FmkoreaCrawler("fmkorea_crawler", ["https://www.fmkorea.com/hotdeal"], session=session)
    data: crawler.ArticleCollection = await crawler_instance.get()
    assert len(data) > 0
