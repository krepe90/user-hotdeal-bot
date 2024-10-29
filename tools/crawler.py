"""커맨드라인에서 사용할 수 있는 CLI 크롤러 도구, 크롤링 테스트용으로 사용 가능.
"""

import asyncio
import typer

from src import crawler


async def main(module_name: str, detail: bool = False):
    """크롤러 도구의 메인 함수.

    Args:
        module_name (str): 크롤러 모듈 이름.
        url (str | None): 크롤링할 URL.
    """
    if module_name == "arca":
        crawler_instance = crawler.ArcaLiveCrawler(
            "arcalive_hotdeal",
            ["https://arca.live/b/hotdeal"],
        )
    elif module_name == "ppomppu":
        crawler_instance = crawler.PpomppuCrawler(
            "ppomppu_crawler",
            ["https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"],
        )
    elif module_name == "ppomppu_rss":
        crawler_instance = crawler.PpomppuRSSCrawler(
            "ppomppu_rss_crawler", ["https://www.ppomppu.co.kr/rss.php?id=ppomppu"]
        )
    elif module_name == "ruliweb":
        crawler_instance = crawler.RuliwebCrawler(
            "ruliweb_crawler",
            ["https://bbs.ruliweb.com/market/board/1020?view=thumbnail&page=1"],
        )
    elif module_name == "clien":
        crawler_instance = crawler.ClienCrawler(
            "clien_crawler", ["https://www.clien.net/service/board/jirum"]
        )
    elif module_name == "damoang":
        crawler_instance = crawler.DamoangCrawler(
            "damoang_crawler", ["https://damoang.net/economy"]
        )
    else:
        raise ValueError(f"Unknown module name: {module_name}")

    data: crawler.ArticleCollection = await crawler_instance.get()
    # print each article using typer with style
    for article_id, article_dict in data.items():
        # print as table with style
        # each row includes article_id, title, category, writer_name
        # if is_end is True, strikethough the title
        if detail:
            typer.echo(
                typer.style(
                    (
                        f"{article_id:<10} [{article_dict['category']}] {article_dict['title']} - {article_dict['writer_name']}"
                        f"\n            {article_dict['url']}"
                        f"\n            {article_dict['extra']}"
                    ),
                    bold=False,
                    dim=article_dict["is_end"],
                )
            )
        else:
            typer.echo(
                typer.style(
                    (
                        f"{article_id:<10} [{article_dict['category']}] {article_dict['title']} - {article_dict['writer_name']}"
                        f"\n            {article_dict['url']}"
                    ),
                    bold=False,
                    dim=article_dict["is_end"],
                )
            )

    await crawler_instance.close()


def run(module_name: str, detail: bool = False):
    asyncio.run(main(module_name, detail=detail))


if __name__ == "__main__":
    typer.run(run)
