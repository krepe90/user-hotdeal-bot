import os
import sys
import json
import time
import signal
import asyncio
import logging
import logging.config
from typing import Any, TypedDict

import aiohttp

import crawler
import bot
import util


__version__ = "2.0.4"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    # "User-Agent": f"user-hotdeal-bot/{__version__} (+https://github.com/krepe90/user-hotdeal-bot)"
}


with open("config_logger.json", "r") as f:
    _config_logger: "logging.config._DictConfigArgs" = json.load(f)
    logging.config.dictConfig(_config_logger)
logger_status = logging.getLogger("status")


class CrawlerConfig(TypedDict):
    url_list: list[str]
    crawler_name: str
    description: str
    enabled: bool


class BotConfig(TypedDict):
    bot_name: str
    description: str
    kwargs: dict[str, Any]
    enabled: bool


class Config(TypedDict):
    crawlers: dict[str, CrawlerConfig]
    bots: dict[str, BotConfig]


class DumpedData(TypedDict):
    version: str
    crawler: dict[str, crawler.ArticleCollection]
    bot: dict[str, bot.SerializedBotData]


class CrawlingResult(TypedDict):
    """크롤링 결과를 담는 데이터 클래스

    Attributes:
        new: 새로 추가된 게시글 목록
        update: 업데이트된 게시글 목록
        remove: 삭제된 게시글 목록
    """
    new: list[crawler.BaseArticle]
    update: list[crawler.BaseArticle]
    remove: list[crawler.BaseArticle]


class BotManager:
    def __init__(self):
        self.logger = logging.getLogger("BotManager")
        self.closed = False

    async def init_session(self):
        self.logger.info("Initializing start")
        timeout = aiohttp.ClientTimeout(total=20)
        self.session = aiohttp.ClientSession(headers=HEADERS, trust_env=True, timeout=timeout)
        self.crawlers: dict[str, crawler.BaseCrawler] = {}
        self.bots: dict[str, bot.BaseBot] = {}
        self.article_cache: dict[str, crawler.ArticleCollection] = {}
        # self.article_cache: dict[str, crawler.ArticleCollection] = {k: crawler.ArticleCollection() for k in self.crawlers.keys()}
        await self.load()

    async def init_crawlers(self, crawlers: dict[str, CrawlerConfig]):
        self.logger.info("Crawler initialize start")
        _crawlers_old = self.crawlers
        self.crawlers = {}
        for crawler_name, crawler_config in crawlers.items():
            # 활성화 여부 확인
            if not crawler_config["enabled"]:
                self.logger.info(f"Crawler disabled: {crawler_name}")
                continue
            if crawler_name in _crawlers_old:
                _cwr = _crawlers_old.pop(crawler_name)
                # 설정이 동일한 경우 재사용
                if (_cwr.url_list == crawler_config["url_list"] and
                    _cwr.cls_name == crawler_config["crawler_name"]):
                    self.crawlers[crawler_name] = _cwr
                    self.logger.info(f"Crawler reused: {crawler_name} ({crawler_config['crawler_name']})")
                    continue
                # 설정이 달라진 경우 새로 생성
                else:
                    self.logger.info(f"Config changed: {crawler_name}")
            crawler_cls_name = crawler_config["crawler_name"]
            crawler_cls = getattr(crawler, crawler_cls_name, None)
            if not issubclass(crawler_cls, crawler.BaseCrawler):
                self.logger.warning(f"Invalid crawler class: {crawler_cls_name}")
                continue
            # 크롤러 객체 생성
            self.crawlers[crawler_name] = crawler_cls(crawler_name, crawler_config["url_list"], self.session)
            self.logger.info(f"Crawler initialized: {crawler_name} ({crawler_cls_name})")
        # 남은 크롤러 객체 목록 출력 (삭제될 크롤러)
        for k, v in _crawlers_old.items():
            # GC가 알아서 할테니 별도 처리는 X (세션은 다 같이 쓰고 있기 떄문에 닫으면 안됨)
            self.logger.info(f"Crawler removed or disabled: {k} ({v.cls_name})")
        self.logger.info(f"{len(self.crawlers)} crawler(s) initialized")

    async def init_bots(self, bots: dict[str, BotConfig]):
        self.logger.info("Bot initialize start")
        _bots_old, self.bots = self.bots, {}
        for bot_name, bot_config in bots.items():
            bot_cls_name = bot_config["bot_name"]
            bot_cls = getattr(bot, bot_cls_name, None)
            if not issubclass(bot_cls, bot.BaseBot):
                self.logger.warning(f"Invalid bot class: {bot_cls_name}")
                continue
            if not bot_config["enabled"]:
                self.logger.info(f"Bot disabled: {bot_name}")
                continue
            if bot_name in _bots_old:
                _bot = _bots_old.pop(bot_name)
                # 설정까지 동일한 경우 재사용
                if (_bot.cls_name == bot_cls_name and
                    _bot.config == bot_config["kwargs"]):
                    self.bots[bot_name] = _bot
                    self.logger.info(f"Bot reused: {bot_name} ({bot_cls_name})")
                    # 봇 consumer task 재시작
                    await _bot.check_consumer(no_warning=True)
                    continue
                # 설정이 바뀐 경우
                else:
                    _bot.close()
                    self.logger.info(f"Config changed: {bot_name}")
            self.bots[bot_name] = bot_cls(name=bot_name, **bot_config["kwargs"])
            self.logger.info(f"Bot initialized: {bot_name} ({bot_cls_name})")
        # 기존 봇 객체들 삭제
        for bot_name, bot_obj in _bots_old.items():
            await bot_obj.close()
            self.logger.info(f"Bot removed or disabled: {bot_name} ({bot_obj.cls_name})")
        self.logger.info(f"{len(self.bots)} bot(s) initialized")

    async def deserialize_articles(self, crawler_data: dict[str, crawler.ArticleCollection]):
        self.logger.info("Article dump data deserialize start")
        # 크롤러가 파싱한 게시글 정보 불러오기
        for crawler_name, crawler_obj in crawler_data.items():
            # 현재 로딩된 크롤러가 아닌 크롤러의 정보가 들어온 경우 경고
            if crawler_name not in self.crawlers.keys():
                self.logger.warning(f"Unknown crawler name in dump file: {crawler_name}")
            # ArticleCollection 객체로 변환 후 self.article_cache 에 저장
            # 변환 시 str 형식으로 되어있던 key들을 자동으로 int 형식으로 변환 (__setitem__ 참고)
            self.article_cache[crawler_name] = crawler.ArticleCollection(crawler_obj)
            # logging
            self.logger.info(f"{crawler_name}: {len(self.article_cache[crawler_name])} article(s) loaded")
            self.logger.debug(f"{crawler_name}: article_id range: [{min(self.article_cache[crawler_name], default=0)}, {max(self.article_cache[crawler_name], default=0)}]")
        self.logger.info("Article dump data deserialize complete")

    async def deserialize_bots(self, bot_data: dict[str, bot.SerializedBotData]):
        # 봇 정보 및 봇이 보냈던/보내야 할 메시지 정보 불러오기
        self.logger.info("Bot dump data deserialize start")
        for bot_name, bot_dump in bot_data.items():
            if bot_name not in self.bots.keys():
                self.logger.warning(f"Unknown bot name in dump file: {bot_name}")
                continue
            # 각 봇에서 구현하는 from_dict 메서드가 각각 수행
            await self.bots[bot_name].from_dict(bot_dump)
            loaded_messages = sum(len(n) for n in self.bots[bot_name].cache)
            self.logger.info(f"{bot_name}: {loaded_messages} message(s) loaded")
            loaded_queue = self.bots[bot_name].queue.qsize()
            self.logger.info(f"{bot_name}: {loaded_queue} message(s) queued")
        self.logger.info("Bot dump data deserialize complete")

    async def load(self, config_file_path: str = "config.json", dump_file_path: str = "dump.json"):
        # 설정 및 데이터 로드
        await self.load_config(config_file_path)
        await self.load_data(dump_file_path)
    
    async def load_config(self, config_file_path: str = "config.json"):
        # config.json 파일 읽기
        if not os.path.isfile(config_file_path):
            self.logger.error("Config file doesn't exists")
            return
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                config: Config = json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error("Config JSON file decode error occured")
            return
        # 크롤러 초기화
        await self.init_crawlers(config["crawlers"])
        # 메신저 봇 초기화
        await self.init_bots(config["bots"])
    
    async def load_data(self, dump_file_path: str = "dump.json"):
        if not os.path.isfile(dump_file_path):
            self.logger.warning("Dump file doesn't exists")
            return
        try:
            with open(dump_file_path, "r", encoding="utf-8") as f:
                data: DumpedData = json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error("Dump JSON file decode error occured")
            return

        self.logger.info(f"App version {__version__}, dump file version {data['version']}")

        # 크롤러가 파싱했던 게시글 정보 불러오기
        await self.deserialize_articles(data["crawler"])
        # 봇 정보 및 봇이 보냈던/보내야 할 메시지 정보 불러오기
        await self.deserialize_bots(data["bot"])
        # article_cache 키 값 추가 설정
        # 크롤러는 등록되어 있으나, 게시글 데이터가 없어 초기화가 필요한 경우 사용
        for crawler_name in self.crawlers.keys():
            if crawler_name not in self.article_cache.keys():
                self.article_cache[crawler_name] = crawler.ArticleCollection()

    async def dump(self, dump_file_path: str = "dump.json"):
        dump = {
            "version": __version__,
            "crawler": self.article_cache,
            "bot": {bot_name: await bot.to_dict() for bot_name, bot in self.bots.items()}
        }
        with open(dump_file_path, "w", encoding="utf-8") as f:
            json.dump(dump, f, ensure_ascii=False, indent=2, default=bot.message_serializer)

    async def _crawling(self, name: str, cwr: crawler.BaseCrawler) -> CrawlingResult:
        result: CrawlingResult = {"new": [], "update": [], "remove": []}
        # 크롤러로부터 글 목록 불러오기
        recent_data: crawler.ArticleCollection = await cwr.get()
        if not recent_data:
            # 글 목록이 비어있는 경우 (파싱에 실패한 경우) 상태 변경 없이 빈 값 반환.
            # self.logger.warning(f"{cwr.__class__.__name__}: Crawling result is empty!!")
            return result
        # 글 번호 최소
        id_min: int = min(recent_data.keys())
        self.logger.debug(f"{cwr.__class__.__name__}: {len(recent_data)} article(s) crawled")
        self.logger.debug(f"{cwr.__class__.__name__}: article_id range: [{id_min}, {max(recent_data.keys())}]")

        # 초기화
        if name not in self.article_cache:
            self.article_cache[name] = crawler.ArticleCollection()
        if not self.article_cache[name]:
            self.article_cache[name].update(recent_data)
            self.logger.info(f"{cwr.__class__.__name__}: Article cache initialized, skip crawling")
            return result

        # 글 목록 페이지 뒤로 넘어가 추적하지 않게 된 게시글들 메모리에서 삭제
        self.article_cache[name].remove_expired(id_min)
        # 봇 메시지 객체들도 비슷한 방식으로 삭제
        for bot_name, bot in self.bots.items():
            await bot.remove_expired_msg_obj(name, id_min)
        # 새로 추가된 글을 result["new"]에 저장 후 메모리 업데이트
        id_cache_max: int = max(self.article_cache[name].keys(), default=0)
        _new_articles = recent_data.get_new(id_cache_max)
        result["new"].extend(_new_articles.values())
        self.article_cache[name].update(_new_articles)
        # 기존 게시글 기준으로 탐색
        for article_id, article in self.article_cache[name].items():
            # 삭제된 글(기존 게시글의 ID가 새 크롤링 결과의 key에 없음)이라면 result["remove"]에 저장
            if article_id not in recent_data:
                result["remove"].append(article)
                continue

            new_article = recent_data[article_id]
            # 메시지 업데이트가 필요한 경우 (품절, 제목 변경, 가격 변경 등)
            if article["is_end"] != new_article["is_end"]:
                # self.logger.debug("Status update detected: {title} ({url}) -> {status}".format(status=new_article["is_end"], **article))
                result["update"].append(article)
            elif article["title"] != new_article["title"]:
                # crawling 메서드의 로깅과 중복돼서 주석 처리
                # self.logger.debug("Title update detect: {title} ({url}) -> {new_title}".format(new_title=new_article["title"], **article))
                result["update"].append(article)
            elif article.get("extra") and article["extra"].get("price") != new_article.get("extra", {}).get("price"):
                result["update"].append(article)
            article.update(new_article)

        # 삭제 확인된 글 객체와 메시지 객체를 메모리에서 제거
        for article in result["remove"]:
            self.article_cache[name].pop(article["article_id"], None)
        return result

    async def crawling(self) -> CrawlingResult:
        # 메시지 새로 보내기, 기존 메시지 업데이트, 기존 메시지 삭제
        result: CrawlingResult = {"new": [], "update": [], "remove": []}
        # 크롤러별로 웹페이지 크롤링 후 합쳐서 어떤 메시지를 새로 보내거나 정리할지 결정
        st = time.time()
        results: list[CrawlingResult] = await asyncio.gather(*[self._crawling(name, cwr) for name, cwr in self.crawlers.items()])
        for d in results:
            result["new"].extend(d["new"])
            result["update"].extend(d["update"])
            result["remove"].extend(d["remove"])
        # logging
        if self.logger.isEnabledFor(logging.DEBUG):
            for article in result["new"]:
                self.logger.debug("New: {title} ({url})".format(**article))
            for article in result["update"]:
                self.logger.debug("Update: {title} ({url})".format(**article))
            for article in result["remove"]:
                self.logger.debug("Remove: {title} ({url})".format(**article))
        crawling_time = time.time() - st
        self.logger.info(f"Result: {crawling_time:.2f}s, {len(result['new'])}/{len(result['update'])}/{len(result['remove'])}")
        if crawling_time > 30:
            self.logger.warning(f"Crawling time took so long: {crawling_time}")
        return result

    async def send(self, d: CrawlingResult):
        # 새 메시지 보내기
        for bot_name, bot_instance in self.bots.items():
            await bot_instance.send_iter(d["new"])
        # 메시지 수정하기
        for bot_name, bot_instance in self.bots.items():
            await bot_instance.edit_iter(d["update"])
        # 메시지 삭제하기
        for bot_name, bot_instance in self.bots.items():
            await bot_instance.delete_iter(d["remove"])

    async def _run(self):
        try:
            # 크롤링
            data = await self.crawling()
            # 메시지 보내기
            await self.send(data)
        except Exception as e:
            self.logger.exception(e)

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
        self.logger.info("session close start")
        # 크롤러 세션 닫기
        for k, cwr in self.crawlers.items():
            self.logger.debug(f"cralwer close: {k}")
            if not cwr.session.closed:
                await cwr.close()
        # 봇 세션 닫기
        for bot_name, bot in self.bots.items():
            self.logger.debug(f"bot close: {bot_name}")
            await bot.close()
        # 데이터 저장
        self.logger.info("data dump start")
        await self.dump()
        self.logger.info("session close / data dump end")

    async def reload(self):
        self.logger.info("Reload start")
        # 데이터 저장
        await self.dump()
        # config.json 파일 다시 읽어서 크롤러, 봇 초기화
        await self.load_config()


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


async def reload(sig: signal.Signals, bot: BotManager):
    logger_status.info(f"Received reload signal {sig.name}")
    await bot.reload()


def main():
    loop = asyncio.new_event_loop()
    bot = BotManager()
    if sys.platform != "win32":
        # shutdown (SIGTERM, SIGINT)
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(shutdown(signal.SIGTERM, bot)))
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(shutdown(signal.SIGINT, bot)))
        # reload (SIGHUP)
        loop.add_signal_handler(signal.SIGHUP, lambda: asyncio.create_task(reload(signal.SIGHUP, bot)))

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
        if not loop.is_closed():
            loop.close()
    logger_status.info(f"hotdeal bot v{__version__} stopped!!")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
