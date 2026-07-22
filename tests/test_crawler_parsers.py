import pytest

from src import crawler


@pytest.mark.asyncio
async def test_ppomppu_parses_writer_from_direct_link_text():
    html = """
    <div class="bbs_title"><span class="bname"><a>뽐뿌게시판</a></span></div>
    <input name="id" value="ppomppu">
    <table id="revolution_main_table">
      <tr class="baseList bbs_new1">
        <td>722021</td>
        <td>
          <div class="baseList-box">
            <a class="baseList-title">국내산 쪽파 1kg</a>
            <small class="baseList-small">[식품/건강]</small>
          </div>
        </td>
        <td><a class="baseList-name"><i class="nlevel lv3"></i>작성자</a></td>
        <td class="baseList-rec">1</td>
        <td class="baseList-views">1517</td>
      </tr>
    </table>
    """
    crawler_instance = crawler.PpomppuCrawler("ppomppu", [])

    try:
        data = await crawler_instance.parsing(html)
    finally:
        await crawler_instance.close()

    assert data[722021]["writer_name"] == "작성자"


@pytest.mark.asyncio
async def test_ppomppu_rss_strips_whitespace_before_hits_fields():
    xml = """
    <rss>
      <channel>
        <title>안녕하세요. 뽐뿌입니다 - 뽐뿌게시판</title>
        <item>
          <title>국내산 쪽파 1kg</title>
          <link>http://www.ppomppu.co.kr/zboard/view.php?id=ppomppu&amp;no=722021</link>
          <author>작성자</author>
          <hits> [1|1517|0|0]</hits>
        </item>
      </channel>
    </rss>
    """
    crawler_instance = crawler.PpomppuRSSCrawler("ppomppu_rss", [])

    try:
        data = await crawler_instance.parsing(xml)
    finally:
        await crawler_instance.close()

    assert data[722021]["extra"] == {
        "comments": "1",
        "view": "1517",
        "recommend": "0",
        "not_recommend": "0",
    }


@pytest.mark.asyncio
async def test_fmkorea_parses_nested_ellipsis_title():
    html = """
    <div class="bd_tl"><h1><a href="/hotdeal">핫딜</a></h1></div>
    <div id="content">
      <div class="fm_best_widget">
        <ul>
          <li>
            <h3 class="title">
              <a href="/10118769542">
                <span class="ellipsis-target">닌텐도 프로콘2</span>
                <span class="comment_count">[3]</span>
              </a>
            </h3>
            <div class="hotdeal_info">
              <span>쇼핑몰: <a>SSG</a></span>
              <span>가격: <a>84,537원</a></span>
              <span>배송: <a>무배</a></span>
            </div>
            <span class="category"><a>SW/게임</a></span>
            <span class="author"> / 작성자</span>
          </li>
        </ul>
      </div>
    </div>
    """
    crawler_instance = crawler.FmkoreaCrawler("fmkorea", [])

    try:
        data = await crawler_instance.parsing(html)
    finally:
        await crawler_instance.close()

    assert data[10118769542]["title"] == "닌텐도 프로콘2"


@pytest.mark.asyncio
async def test_damoang_parses_current_post_rows():
    html = """
    <meta property="og:title" content="알뜰구매">
    <link rel="canonical" href="https://damoang.net/economy">
    <a class="post-row" href="/economy/77811">
      <div>
        <div><div>22</div></div>
        <div>
          <div>
            <span>종료</span>
            <span><span class="post-title">미친 가성비 백팩 추천</span></span>
          </div>
          <span class="post-meta-text"><span>작성자</span></span>
          <span class="post-meta-text">07.22</span>
          <span class="post-meta-text">2.8k</span>
          <div class="mobile-meta"><span>22</span><span>07.22</span><span>2.8k</span></div>
        </div>
      </div>
    </a>
    """
    crawler_instance = crawler.DamoangCrawler("damoang", [])

    try:
        data = await crawler_instance.parsing(html)
    finally:
        await crawler_instance.close()

    assert data[77811] == {
        "article_id": 77811,
        "title": "미친 가성비 백팩 추천",
        "category": "종료",
        "site_name": "다모앙",
        "board_name": "알뜰구매",
        "writer_name": "작성자",
        "crawler_name": "damoang",
        "url": "https://damoang.net/economy/77811",
        "is_end": True,
        "extra": {"recommend": "22", "view": "2.8k"},
    }


@pytest.mark.asyncio
async def test_zod_parses_current_definition_list_metadata():
    html = """
    <div class="app-board-title"><a href="/deal">특가</a></div>
    <div id="board-list">
      <ul class="zod-board-list--deal">
        <li>
          <a href="/deal/8473120">
            <span class="app-list-title-item">네이버페이 포인트</span>
            <dl class="app-list-meta zod-board--deal-meta">
              <dt>홈페이지/장소</dt><dd><strong>네이버</strong></dd>
              <dt>가격</dt><dd>가격: <strong>0원</strong></dd>
              <dt>배송비</dt><dd>배송비: <strong>무료</strong></dd>
            </dl>
            <dl class="app-list-meta">
              <dt>작성자 닉네임</dt>
              <dd class="app-list-member"><span>작성자</span></dd>
              <dt>추천수</dt><dd class="app-list__voted-count">0</dd>
            </dl>
          </a>
        </li>
      </ul>
    </div>
    """
    crawler_instance = crawler.ZodCrawler("zod", [])

    try:
        data = await crawler_instance.parsing(html)
    finally:
        await crawler_instance.close()

    assert data[8473120]["writer_name"] == "작성자"
    assert data[8473120]["category"] == "네이버"
    assert data[8473120]["extra"] == {
        "mall": "네이버",
        "price": "0원",
        "delivery": "무료",
        "recommend": 0,
    }
