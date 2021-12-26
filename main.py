import time
from typing import Dict, List
import asyncio
import json
import logging
import logging.config

import aiohttp

import crawler
import bot
import util


__version__ = "1.1.0"


URL_RULIWEB_USER_HOTDEAL = [
    "https://bbs.ruliweb.com/market/board/1020?view=thumbnail&page=1",
    # "https://bbs.ruliweb.com/market/board/1020?view=thumbnail&page=2"
]
URL_PPOMPPU = ["https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"]
URL_PPOMPPU_RSS = ["http://www.ppomppu.co.kr/rss.php?id=ppomppu"]
URL_PPOMPPU_FOREIGN = ["https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu4"]
URL_CLIEN_JIRUM = ["https://www.clien.net/service/board/jirum"]
URL_COOLENJOY_JIRUM_RSS = ["https://coolenjoy.net/rss?bo_table=jirum"]
URL_QUASARZONE_SALEINFO_MOBILE = ["https://quasarzone.com/bbs/qb_saleinfo?device=mobile"]


with open("config_logger.json", "r") as f:
    _config_logger: "logging.config._DictConfigArgs" = json.load(f)
    logging.config.dictConfig(_config_logger)
with open("config.json", "r") as f:
    _config = json.load(f)
logger_status = logging.getLogger("status")


class BotManager:
    def __init__(self):
        self.logger = logging.getLogger("BotManager")
        self.logger.info("Initializing start")
        self.session = aiohttp.ClientSession()
        self.crawlers: Dict[str, crawler.BaseCrawler] = {
            "ruliweb_user_hotdeal": crawler.RuliwebCrawler(URL_RULIWEB_USER_HOTDEAL, self.session),
            "ppomppu_board": crawler.PpomppuCrawler(URL_PPOMPPU, self.session),
            "ppomppu_foreign": crawler.PpomppuCrawler(URL_PPOMPPU_FOREIGN, self.session),
            "clien_jirum": crawler.ClienCrawler(URL_CLIEN_JIRUM, self.session),
            "coolenjoy_jirum_rss": crawler.CoolenjoyRSSCrawler(URL_COOLENJOY_JIRUM_RSS, self.session),
            "quasarzone_saleinfo_mobile": crawler.QuasarzoneMobileCrawler(URL_QUASARZONE_SALEINFO_MOBILE, self.session)
        }
        self.logger.info(f"{len(self.crawlers)} crawler(s) initialized")
        self.bots: Dict[str, bot.BaseBot] = {
            "telegram": bot.TelegramBot(**_config["telegram"])
        }
        self.logger.info(f"{len(self.bots)} bot(s) initialized")
        self.article_cache: Dict[str, Dict[int, crawler.BaseArticle]] = {k: {} for k in self.crawlers.keys()}

    async def _crawling(self, name: str, cwr: crawler.BaseCrawler) -> Dict[str, List[crawler.BaseArticle]]:
        result: Dict[str, List[crawler.BaseArticle]] = {"new": [], "update": [], "remove": []}
        # 크롤러로부터 글 목록 불러오기
        recent_data: Dict[int, crawler.BaseArticle] = await cwr.get()
        if not recent_data:
            self.logger.warning(f"{cwr.__class__.__name__}: Crawling result is empty!!")
            return result
        # 글 번호 최소
        id_min: int = min(recent_data.keys())
        self.logger.debug(f"{cwr.__class__.__name__}: {len(recent_data)} article(s) crawled")
        self.logger.debug(f"{cwr.__class__.__name__}: article_id range: [{id_min}, {max(recent_data.keys())}]")

        # 초기화
        if not self.article_cache[name]:
            self.article_cache[name].update(recent_data)
            self.logger.info(f"{cwr.__class__.__name__}: Article cache initialized, skip crawling")
            return result

        # 글 목록 페이지 뒤로 넘어간 게시글들 메모리에서 지우기 (채팅은 안지움)
        self.article_cache[name] = {n: m for n, m in self.article_cache[name].items() if n >= id_min}
        # 새로 추가된 글 업데이트 (저장된 데이터의 제일 최신 글보다 최신의 것들만 저장)
        id_cache_max: int = max(self.article_cache[name].keys())
        _new_articles = {n: m for n, m in recent_data.items() if n > id_cache_max}
        result["new"].extend(_new_articles.values())
        self.article_cache[name].update(_new_articles)
        # 기존 게시글 확인
        for article_id, article in self.article_cache[name].items():
            # 삭제된 글 제거 (remove에 추가)
            if article_id not in recent_data:
                result["remove"].append(article)
                continue

            new_article = recent_data[article_id]
            # 메시지 업데이트가 필요한 경우 (품절, 제목 변경)
            if article["is_end"] != new_article["is_end"]:
                # self.logger.debug("Status update detected: {title} ({url}) -> {status}".format(status=new_article["is_end"], **article))
                result["update"].append(article)
            elif article["title"] != new_article["title"]:
                # self.logger.debug("Title update detect: {title} ({url}) -> {new_title}".format(new_title=new_article["title"], **article))
                result["update"].append(article)
            # 게시글 데이터 업데이트 (message 제외)
            new_article["message"] = article.get("message", {})
            article.update(new_article)
        # 삭제된 글 메모리(article_cache)에서 제거
        for article in result["remove"]:
            self.article_cache[name].pop(article["article_id"], None)
        return result

    async def crawling(self) -> Dict[str, List[crawler.BaseArticle]]:
        # 순서대로 메시지 새로 보내기, 기존 메시지 업데이트, 기존 메시지 삭제
        result: Dict[str, List[crawler.BaseArticle]] = {"new": [], "update": [], "remove": []}
        # 크롤러별로 크롤링 후 분류하여 어떤 메시지를 보내고 정리할지 결정
        st = time.time()
        results = await asyncio.gather(*[self._crawling(name, cwr) for name, cwr in self.crawlers.items()])
        for d in results:
            result["new"].extend(d["new"])
            result["update"].extend(d["update"])
            result["remove"].extend(d["remove"])
        # logging
        if result["new"] or result["update"] or result["remove"]:
            self.logger.info(f"Crawling result: {len(result['new'])} / {len(result['update'])} / {len(result['remove'])}")
        for article in result["new"]:
            self.logger.debug("New: {title} ({url})".format(**article))
        for article in result["update"]:
            self.logger.debug("Update: {title} ({url})".format(**article))
        for article in result["remove"]:
            self.logger.debug("Remove: {title} ({url})".format(**article))
        self.logger.info(f"Crawling time: {time.time() - st}")
        return result

    async def send(self, d: Dict[str, List[crawler.BaseArticle]]):
        # 새로 메시지 보내기
        for article in d["new"]:
            for bot_name, bot_instance in self.bots.items():
                if msg := await bot_instance.send(article):
                    article["message"][bot_name] = msg
                else:
                    self.logger.warning("Failed to receive message object: {title} ({url}) -> {bot_name}".format(bot_name=bot_name, **article))
        # 기존 메시지 수정하기
        for article in d["update"]:
            if not article["message"]:
                self.logger.info("Cannot find message reference: {title} ({url})".format(**article))
            for bot_name, msg in article["message"].items():
                await self.bots[bot_name].edit(msg, article)
        # 기존 메시지 삭제하기
        for article in d["remove"]:
            for bot_name, msg in article["message"].items():
                await self.bots[bot_name].delete(msg)

    async def _run(self):
        data = await self.crawling()
        await self.send(data)

    async def run(self):
        self.logger.info("Loop start")
        while True:
            self.logger.debug("Task start")
            await self._run()
            self.logger.debug("Task end, sleep")
            await asyncio.sleep(60)

    async def close(self):
        for k, cwr in self.crawlers.items():
            if not cwr.session.closed:
                await cwr.close()


async def main():
    bot = BotManager()
    await bot.run()
    await bot.close()


if __name__ == "__main__":
    logger_status.info(f"hotdeal bot v{__version__} start!!")
    asyncio.run(main())
