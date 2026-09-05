import pytest

from src.crawler.quasarzone import QuasarzoneCrawler

TITLE = "[쇼핑몰] 할인 상품 (9,900원/무료배송)"


def make_page(layout, title, ended=False, locked=False):
    lock = '<i class="fa-lock"></i>' if locked else ""
    link = f'<a class="subject-link" href="/bbs/qb_saleinfo/views/123">{lock}{title}</a>'
    if layout == "v2":
        return f"""
        <a class="v2-board-head__title">핫딜 게시판</a>
        <div class="v2-notice-row"><a href="/bbs/qb_saleinfo/views/999">공지</a></div>
        <div class="v2-list">
          <div class="v2-list-row v2-list-row--hotdeal v2-partner-row">
            <a class="subject-link" href="/bbs/qb_partnersaleinfo/views/999">파트너 광고</a>
          </div>
          <div class="v2-list-row v2-list-row--hotdeal {"is-done" if ended else ""}">
            <span class="qc-count-good">0</span>
            <div class="v2-list-row__stack">
              <div class="v2-list-row__line1"><span class="v2-badge">생활/식품</span></div>
              <div class="v2-list-row__line2"><div class="tit-with-badge"><p class="tit">
                {link}<span class="board-list-comment"><span class="ctn-count">12</span></span>
              </p></div></div>
              <div class="v2-list-row__line3">
                <div class="v2-list-row__price-group">
                  <span class="v2-list-row__ship"><img alt="쇼핑몰"></span>
                  <span class="v2-list-row__price">￦9,900</span>
                  <span class="v2-list-row__ship">배송비 무배</span>
                </div>
                <div class="v2-list-row__meta-group">
                  <span class="v2-nick" data-nick="작성자"><span class="user-nick-label">작성자</span></span>
                  <span class="v2-list-row__hit">조회 <span class="qc-count-hit">1.1천</span></span>
                </div>
              </div>
            </div>
          </div>
        </div>
        """
    return f"""
    <div class="l-title"><h2>핫딜 게시판</h2></div>
    <div class="market-info-type-list"><table><tbody><tr>
      <td><span class="num">0</span></td><td>
        <span class="label">{"종료" if ended else "진행중"}</span>
        {link}<span class="board-list-comment">12</span>
        <span class="nick" data-nick="작성자">작성자</span><span class="count">1.1천</span>
        <div class="market-info-sub"><p>
          <span class="category">생활/식품</span>
          <span>가격 <span>￦9,900</span></span><span>배송비 무배</span>
        </p></div>
      </td>
    </tr></tbody></table></div>
    """


@pytest.mark.asyncio
@pytest.mark.parametrize("layout", ["v2", "legacy"])
@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("ended", [False, True])
async def test_quasarzone_parses_title_and_metadata(layout, nested, ended):
    title = f'<span class="ellipsis-with-reply-cnt">{TITLE}</span>' if nested else TITLE
    instance = QuasarzoneCrawler("quasarzone", [])
    try:
        data = await instance.parsing(make_page(layout, f"\n  {title}\n ", ended))
    finally:
        await instance.close()
    assert data == {
        123: {
            "article_id": 123,
            "title": TITLE,
            "category": "생활/식품",
            "site_name": "퀘이사존",
            "board_name": "핫딜 게시판",
            "writer_name": "작성자",
            "crawler_name": "quasarzone",
            "url": "https://quasarzone.com/bbs/qb_saleinfo/views/123",
            "is_end": ended,
            "extra": {"recommend": "0", "view": "1.1천", "price": "￦9,900", "delivery": "무배"},
        }
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("layout", ["v2", "legacy"])
@pytest.mark.parametrize("title,locked", [(" \n ", False), (TITLE, True)])
async def test_quasarzone_skips_empty_titles_and_locked_articles(layout, title, locked):
    instance = QuasarzoneCrawler("quasarzone", [])
    try:
        assert await instance.parsing(make_page(layout, title, locked=locked)) == {}
    finally:
        await instance.close()
