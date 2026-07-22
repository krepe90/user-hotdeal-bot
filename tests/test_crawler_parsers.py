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
