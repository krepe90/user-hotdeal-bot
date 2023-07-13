import asyncio
import logging
from abc import ABCMeta, abstractmethod
from typing import Any, Iterable, Literal, TypedDict, Union, TypeVar, Generic, Awaitable

import telegram

from crawler.base_crawler import BaseArticle
from util import escape_markdown


MessageType = TypeVar("MessageType")


def message_serializer(obj: Any) -> Any:
    """메시지 객체를 직렬화할 때 사용하는 함수
    """
    if isinstance(obj, telegram.Message):
        return obj.to_dict()
    else:
        raise TypeError


class SerializedBotData(TypedDict, Generic[MessageType]):
    """봇 객체의 직렬화된 데이터

    queue: 봇이 아직 처리하지 않은 메시지들의 큐
    cache: 봇 객체에서 저장중인 메시지 객체 목록. {crawler_name(str): {id(int): (MessageType)}} 형태
    """
    queue: list[tuple[str, BaseArticle]]
    cache: dict[str, dict[int, MessageType]]


class BaseBot(Generic[MessageType], metaclass=ABCMeta):
    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = logging.getLogger(f"bot.{self.__class__.__name__}")
        self.cache: dict[str, dict[int, MessageType]] = dict()
        self.queue: asyncio.Queue[tuple[Literal["send", "edit", "delete"], BaseArticle]] = asyncio.Queue()
        self.is_running = True
        self.consumer_task: Union[asyncio.Task, None] = asyncio.create_task(self.consumer())

    async def get_msg_obj(self, data: BaseArticle) -> Union[MessageType, None]:
        """게시글 객체를 받아서 메시지 객체를 반환.

        Args:
            data: 게시글 객체
        Returns:
            msg_obj: 메시지 객체
        """
        if data["crawler_name"] not in self.cache:
            return None
        return self.cache[data["crawler_name"]].get(data["article_id"])

    async def set_msg_obj(self, data: BaseArticle, msg_obj: MessageType):
        """메시지 객체를 저장.

        Args:
            data: 게시글 객체
            msg_obj: 메시지 객체
        """
        crawler_name = data["crawler_name"]
        if crawler_name not in self.cache:
            self.cache[crawler_name] = {}
        self.cache[crawler_name][data["article_id"]] = msg_obj

    async def remove_msg_obj(self, crawler_name: str, article_id: int):
        """메시지 객체를 삭제.

        Args:
            crawler_name: 크롤러 이름
            article_id: 삭제할 메시지 객체의 게시글 id
        """
        if crawler_name not in self.cache:
            return
        self.cache[crawler_name].pop(article_id)

    async def remove_expired_msg_obj(self, crawler_name: str, id_min: int):
        """id_min보다 작은 id를 가진 메시지 객체들을 삭제. 특정 시점 이전의 메시지 객체를 지울 때 사용.

        Args:
            crawler_name: 크롤러 이름
            id_min: 삭제할 메시지 객체의 id의 최솟값
        """
        if crawler_name not in self.cache:
            return
        messages = self.cache[crawler_name]
        remove_list = [i for i in messages.keys() if i < id_min]
        for article_id in remove_list:
            messages.pop(article_id)
            self.logger.debug(f"Removed message object ({article_id})")

    async def consumer(self):
        item = None
        try:
            while self.is_running:
                if self.queue.empty():
                    # self.logger.debug("Consumer task waiting for item")
                    await asyncio.sleep(1)
                    continue
                item = await self.queue.get()
                self.logger.debug(f"Consumer task got item: <{item[1]['crawler_name']}.{item[0]}> {item[1]['title']}")
                try:
                    match item[0]:
                        case "send":
                            await self._send(item[1])
                        case "edit":
                            await self._edit(item[1])
                        case "delete":
                            await self._delete(item[1])
                except Exception as e:
                    self.logger.exception(e)
                item = None
        except asyncio.CancelledError:
            # 작업이 취소됐다면 남아있는 아이템을 큐에 다시 넣어준 다음 consumer task 종료.
            self.logger.info("Consumer task cancelled")
            if item is not None:
                await self.queue.put(item)
            return

    async def run_consumer(self):
        self.is_running = True
        self.consumer_task = asyncio.create_task(self.consumer())

    async def stop_consumer(self):
        self.is_running = False
        if self.consumer_task is None:
            return
        if self.consumer_task.done():
            return
        try:
            await asyncio.wait_for(self.consumer_task, timeout=5)
        except asyncio.TimeoutError:
            self.logger.warning("Consumer task is not finished in 5 secs")
            self.consumer_task.cancel()

    async def check_consumer(self):
        if self.consumer_task is None or self.consumer_task.done():
            self.logger.warning("Consumer task stopped. Restarting...")
            await self.run_consumer()

    @abstractmethod
    async def _send(self, data: BaseArticle) -> Union[MessageType, None]:
        """메시지 전송 구현 추상 메서드"""
        pass

    @abstractmethod
    async def _edit(self, data: BaseArticle):
        """메시지 수정 구현 추상 메서드"""
        pass

    @abstractmethod
    async def _delete(self, data: BaseArticle):
        """메시지 삭제 구현 추상 메서드"""
        pass

    async def send(self, data: BaseArticle) -> None:
        await self.check_consumer()
        await self.queue.put(("send", data))

    async def edit(self, data: BaseArticle) -> None:
        await self.check_consumer()
        await self.queue.put(("edit", data))

    async def delete(self, data: BaseArticle) -> None:
        await self.check_consumer()
        await self.queue.put(("delete", data))

    async def send_iter(self, data_iter: Iterable[BaseArticle]) -> None:
        await self.check_consumer()
        for data in data_iter:
            await self.queue.put(("send", data))

    async def edit_iter(self, data_iter: Iterable[BaseArticle]) -> None:
        await self.check_consumer()
        for data in data_iter:
            await self.queue.put(("edit", data))

    async def delete_iter(self, data_iter: Iterable[BaseArticle]) -> None:
        await self.check_consumer()
        for data in data_iter:
            await self.queue.put(("delete", data))

    @abstractmethod
    def _make_message(self, d: BaseArticle):
        pass

    async def to_dict(self) -> SerializedBotData:
        """메시지 목록 및 작업 큐 직렬화. 만약 메시지 객체의 직렬화 및 역직렬화가 불가능하다면 value가 비어있는 딕셔너리를 반환하도록 오버라이드 할 것.
        """
        # WARNING: This method consumes all objects in queue.
        # Must call after consumer task is stopped.
        await self.stop_consumer()
        _queue = []
        while not self.queue.empty():
            _queue.append(await self.queue.get())
        return {
            "queue": _queue,
            "cache": self.cache,
        }

    @abstractmethod
    async def from_dict(self, data: SerializedBotData) -> None:
        """"""
        pass

    async def close(self):
        # wait until self.queue is empty, and close consumer
        # 메시지를 다 전송하지 못한 상황이면 해당 데이터들을 따로 직렬화를 해야할 것 같다.
        await self.stop_consumer()


class TelegramBot(BaseBot[telegram.Message]):
    def __init__(self, name: str, token: str, target: str):
        super().__init__(name)
        self.bot = telegram.Bot(token)
        self.target = target

    async def _send(self, data: BaseArticle, retry: bool = False) -> Union[telegram.Message, None]:
        kwargs = self._make_message(data)
        msg = None
        try:
            msg = await self.bot.send_message(chat_id=self.target, **kwargs)
            self.logger.debug(f"Message send to {self.target} {msg.message_id}")
        except telegram.error.RetryAfter as e:
            self.logger.warning("Retry send message after {t} secs: ({e}): {title} ({url}) -> {target}".format(e=e, t=e.retry_after, target=self.target, **data))
            await asyncio.sleep(e.retry_after)
            msg = await self._send(data, retry=False)
        except telegram.error.TelegramError as e:
            self.logger.error("Send message failed: {e.__name__} ({e}): {title} ({url}) -> {target}".format(e=e, target=self.target, **data))
        finally:
            if msg is None and retry:
                msg = await self._send(data, retry=False)
            if msg is not None:
                await self.set_msg_obj(data, msg)

    async def _edit(self, data: BaseArticle, retry: bool = False):
        msg = await self.get_msg_obj(data)
        if msg is None:
            self.logger.warning("Message not found: {title} ({url})".format(**data))
            return
        try:
            kwargs = self._make_message(data)
            await msg.edit_text(**kwargs)
        except telegram.error.RetryAfter as e:
            self.logger.warning("Retry edit message after {t} secs: ({e}): {title} ({url}) <- {msg_id}".format(e=e, t=e.retry_after, msg_id=msg.message_id, **data))
            await asyncio.sleep(e.retry_after)
            await self._edit(data, retry=False)
        except telegram.error.BadRequest as e:
            self.logger.error("Edit message failed ({e}): {title} ({url}) <- {msg_id}".format(e=e, msg_id=msg.message_id, **data))

    async def _delete(self, data: BaseArticle):
        """메시지 객체를 찾은 다음, 텔레그램 채널의 메시지를 삭제"""
        msg = await self.get_msg_obj(data)
        if msg is None:
            self.logger.warning("Message not found: {title} ({url})".format(**data))
            return
        else:
            await msg.delete()

    async def from_dict(self, data: SerializedBotData) -> None:
        """메시지 목록 및 작업 큐 역직렬화

        Args:
            data (SerializedBotData): 직렬화된 메시지 목록 및 작업 큐
        """
        # cache
        for crawler_name, msg_data in data["cache"].items():
            if crawler_name not in self.cache:
                self.cache[crawler_name]: dict[int, MessageType] = {}
            for msg_id, msg in msg_data.items():
                self.cache[crawler_name][int(msg_id)] = telegram.Message.de_json(msg, self.bot)
        # queue
        for job in data["queue"]:
            await self.queue.put(job)

    def _make_message(self, d: BaseArticle) -> dict:
        if d["category"]:
            md = escape_markdown("[{category}] {title}".format(**d))
        else:
            md = escape_markdown("{title}".format(**d))
        if d["extra"].get("price") and d["extra"].get("delivery"):
            md += escape_markdown(f"\n{d['extra']['price']} / {' / '.join(d['extra']['delivery'])}")
        if d["is_end"]:
            md = f"~{md}~"
        btn = [
            [telegram.InlineKeyboardButton("자세히 보기 ({site_name} {board_name})".format(**d), d["url"])]
        ]
        result = {
            "text": md,
            "reply_markup": telegram.InlineKeyboardMarkup(btn),
            "parse_mode": telegram.constants.ParseMode.MARKDOWN_V2
        }
        return result
