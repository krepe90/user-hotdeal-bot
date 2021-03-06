import os
import sys
import time
from typing import Any, Dict, List, cast
import asyncio
import json
import logging
import logging.config
import signal

import aiohttp

import crawler
import bot
import util


__version__ = "1.1.11a"


URL_RULIWEB_USER_HOTDEAL = [
    "https://bbs.ruliweb.com/market/board/1020?view=thumbnail&page=1",
    # "https://bbs.ruliweb.com/market/board/1020?view=thumbnail&page=2"
]
URL_PPOMPPU = ["https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu"]
URL_PPOMPPU_RSS = ["http://www.ppomppu.co.kr/rss.php?id=ppomppu"]
URL_PPOMPPU_FOREIGN = ["https://www.ppomppu.co.kr/zboard/zboard.php?id=ppomppu4"]
URL_CLIEN_JIRUM = ["https://www.clien.net/service/board/jirum"]
URL_COOLENJOY_JIRUM_RSS = ["https://coolenjoy.net/rss?bo_table=jirum"]
URL_QUASARZONE_SALEINFO = ["https://quasarzone.com/bbs/qb_saleinfo"]
# URL_QUASARZONE_SALEINFO_MOBILE = ["https://quasarzone.com/bbs/qb_saleinfo?device=mobile"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
}


with open("config_logger.json", "r") as f:
    _config_logger: "logging.config._DictConfigArgs" = json.load(f)
    logging.config.dictConfig(_config_logger)
with open("config.json", "r") as f:
    _config = json.load(f)
logger_status = logging.getLogger("status")


class BotManager:
    def __init__(self):
        self.logger = logging.getLogger("BotManager")
        self.closed = False

    async def init_session(self):
        self.logger.info("Initializing start")
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(headers=HEADERS, trust_env=True, timeout=timeout)
        self.crawlers: Dict[str, crawler.BaseCrawler] = {
            "ruliweb_user_hotdeal": crawler.RuliwebCrawler(URL_RULIWEB_USER_HOTDEAL, self.session),
            "ppomppu_board": crawler.PpomppuCrawler(URL_PPOMPPU, self.session),
            "ppomppu_foreign": crawler.PpomppuCrawler(URL_PPOMPPU_FOREIGN, self.session),
            "clien_jirum": crawler.ClienCrawler(URL_CLIEN_JIRUM, self.session),
            "coolenjoy_jirum_rss": crawler.CoolenjoyRSSCrawler(URL_COOLENJOY_JIRUM_RSS, self.session),
            "quasarzone_saleinfo": crawler.QuasarzoneCrawler(URL_QUASARZONE_SALEINFO, self.session)
        }
        self.logger.info(f"{len(self.crawlers)} crawler(s) initialized")
        self.bots: Dict[str, bot.BaseBot] = {
            "telegram": bot.TelegramBot(**_config["telegram"])
        }
        self.logger.info(f"{len(self.bots)} bot(s) initialized")
        self.article_cache: Dict[str, Dict[int, crawler.BaseArticle]] = {k: {} for k in self.crawlers.keys()}
        self.load()

    def load(self, filepath: str = "dump.json"):
        if not os.path.isfile(filepath):
            self.logger.warning("Dump file doesn't exists")
            return
        kwargs = {
            "telegram": {"bot": cast(bot.TelegramBot, self.bots["telegram"]).bot}
        }
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data: Dict[str, Dict[str, crawler.BaseArticle]] = json.load(f)
        except json.JSONDecodeError as e:
            self.logger.warning("Dump JSON file decode error occured")
            return

        self.logger.info("Article dump data deserialize start")
        for crawler_name, cwr in data.items():
            if not self.article_cache.get(crawler_name):
                self.article_cache[crawler_name] = {}
            for a_id, a_data in cwr.items():
                # article_id, article_data
                new_messages: Dict[str, Any] = {}
                for msg_type, msg_data in a_data.get("message", {}).items():
                    if msg_type == "telegram":
                        new_messages["telegram"] = bot.telegram.Message.de_json(msg_data, **kwargs["telegram"])
                    else:
                        continue
                a_data["message"] = new_messages
                self.article_cache[crawler_name][int(a_id)] = a_data
            self.logger.debug(f"{crawler_name}: {len(self.article_cache[crawler_name])} article(s) loaded")
            self.logger.debug(f"{crawler_name}: article_id range: [{min(self.article_cache[crawler_name], default=0)}, {max(self.article_cache[crawler_name], default=0)}]")
        self.logger.info("Article dump data deserialize complete")

    def dump(self, filepath: str = "dump.json"):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.article_cache, f, ensure_ascii=False, indent=2, default=bot.message_serializer)

    async def _crawling(self, name: str, cwr: crawler.BaseCrawler) -> Dict[str, List[crawler.BaseArticle]]:
        result: Dict[str, List[crawler.BaseArticle]] = {"new": [], "update": [], "remove": []}
        # ?????????????????? ??? ?????? ????????????
        recent_data: Dict[int, crawler.BaseArticle] = await cwr.get()
        if not recent_data:
            # self.logger.warning(f"{cwr.__class__.__name__}: Crawling result is empty!!")
            return result
        # ??? ?????? ??????
        id_min: int = min(recent_data.keys())
        self.logger.debug(f"{cwr.__class__.__name__}: {len(recent_data)} article(s) crawled")
        self.logger.debug(f"{cwr.__class__.__name__}: article_id range: [{id_min}, {max(recent_data.keys())}]")

        # ?????????
        if not self.article_cache[name]:
            self.article_cache[name].update(recent_data)
            self.logger.info(f"{cwr.__class__.__name__}: Article cache initialized, skip crawling")
            return result

        # ??? ?????? ????????? ?????? ????????? ???????????? ??????????????? ????????? (????????? ?????????)
        self.article_cache[name] = {n: m for n, m in self.article_cache[name].items() if n >= id_min}
        # ?????? ????????? ??? ???????????? (????????? ???????????? ?????? ?????? ????????? ????????? ????????? ??????)
        id_cache_max: int = max(self.article_cache[name].keys(), default=0)
        _new_articles = {n: m for n, m in recent_data.items() if n > id_cache_max}
        result["new"].extend(_new_articles.values())
        self.article_cache[name].update(_new_articles)
        # ?????? ????????? ??????
        for article_id, article in self.article_cache[name].items():
            # ????????? ??? ?????? (remove??? ??????)
            if article_id not in recent_data:
                result["remove"].append(article)
                continue

            new_article = recent_data[article_id]
            # ????????? ??????????????? ????????? ?????? (??????, ?????? ??????)
            if article["is_end"] != new_article["is_end"]:
                # self.logger.debug("Status update detected: {title} ({url}) -> {status}".format(status=new_article["is_end"], **article))
                result["update"].append(article)
            elif article["title"] != new_article["title"]:
                # self.logger.debug("Title update detect: {title} ({url}) -> {new_title}".format(new_title=new_article["title"], **article))
                result["update"].append(article)
            # ????????? ????????? ???????????? (message ??????)
            new_article["message"] = article.get("message", {})
            article.update(new_article)
        # ????????? ??? ?????????(article_cache)?????? ??????
        for article in result["remove"]:
            self.article_cache[name].pop(article["article_id"], None)
        return result

    async def crawling(self) -> Dict[str, List[crawler.BaseArticle]]:
        # ???????????? ????????? ?????? ?????????, ?????? ????????? ????????????, ?????? ????????? ??????
        result: Dict[str, List[crawler.BaseArticle]] = {"new": [], "update": [], "remove": []}
        # ??????????????? ????????? ??? ???????????? ?????? ???????????? ????????? ???????????? ??????
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
        crawling_time = time.time() - st
        self.logger.info(f"Crawling time: {crawling_time}")
        if crawling_time > 30:
            self.logger.warning(f"Crawling time is too long: {crawling_time}")
        return result

    async def send(self, d: Dict[str, List[crawler.BaseArticle]]):
        # ?????? ????????? ?????????
        for article in d["new"]:
            for bot_name, bot_instance in self.bots.items():
                if msg := await bot_instance.send(article):
                    article["message"][bot_name] = msg
                else:
                    self.logger.warning("Failed to receive message object: {title} ({url}) -> {bot_name}".format(bot_name=bot_name, **article))
        # ?????? ????????? ????????????
        for article in d["update"]:
            if not article["message"]:
                self.logger.info("Cannot find message reference: {title} ({url})".format(**article))
            for bot_name, msg in article["message"].items():
                await self.bots[bot_name].edit(msg, article)
        # ?????? ????????? ????????????
        for article in d["remove"]:
            for bot_name, msg in article["message"].items():
                await self.bots[bot_name].delete(msg)

    async def _run(self):
        data = await self.crawling()
        await self.send(data)

    async def run(self):
        await self.init_session()
        self.logger.info("Loop start")
        loop = asyncio.get_running_loop()
        while not self.closed:
            self.logger.debug("Task start")
            loop.create_task(self._run())
            self.logger.debug("Task end, sleep")
            await asyncio.sleep(60)
        self.logger.debug("Loop stop (bot closed)")

    async def close(self):
        if self.closed:
            self.logger.info("session already closed")
            return
        self.closed = True
        self.logger.info("session close / data dump start")
        for k, cwr in self.crawlers.items():
            if not cwr.session.closed:
                await cwr.close()
        self.dump()
        self.logger.info("session close / data dump end")


async def shutdown(sig: signal.Signals, bot: BotManager):
    logger_status.info(f"Received exit signal {sig.name}")
    loop = asyncio.get_running_loop()
    # cloasing bot
    await bot.close()
    # stop all tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks)
    loop.stop()


def main():
    loop = asyncio.get_event_loop()
    bot = BotManager()
    if sys.platform != "darwin" and sys.platform != "win32":
        signals = (signal.SIGTERM, signal.SIGINT)
        for sig in signals:
            loop.add_signal_handler(sig, lambda sig=sig: asyncio.create_task(shutdown(sig, bot)))

    logger_status.info(f"hotdeal bot v{__version__} start!! (PID: {os.getpid()})")
    try:
        loop.run_until_complete(bot.run())
    except KeyboardInterrupt:
        print("keyboard interrupt")
    except asyncio.CancelledError:
        pass
    finally:
        if sys.platform == "win32":
            try:
                loop.run_until_complete(shutdown(signal.SIGINT, bot))
            except asyncio.CancelledError:
                pass
        loop.close()
    logger_status.info(f"hotdeal bot v{__version__} stopped!!")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
