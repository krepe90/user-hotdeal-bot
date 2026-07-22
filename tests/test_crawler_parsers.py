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
