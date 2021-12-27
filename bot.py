from abc import ABCMeta, abstractmethod
import logging
from typing import Any, Union
import telegram

from crawler.base_crawler import BaseArticle
from util import escape_markdown


class BaseBot(metaclass=ABCMeta):
    def __init__(self) -> None:
        self.logger = logging.getLogger(f"bot.{self.__class__.__name__}")

    @abstractmethod
    async def send(self, data: BaseArticle) -> Union[Any, None]:
        pass

    @abstractmethod
    async def edit(self, msg, data: BaseArticle):
        pass

    @abstractmethod
    async def delete(self, msg):
        pass

    @abstractmethod
    def _make_message(self, d: BaseArticle):
        pass


class TelegramBot(BaseBot):
    def __init__(self, token: str, target: str):
        super().__init__()
        self.bot = telegram.Bot(token)
        self.target = target

    async def send(self, data: BaseArticle) -> Union[telegram.Message, None]:
        kwargs = self._make_message(data)
        try:
            msg = self.bot.send_message(chat_id=self.target, **kwargs)
            self.logger.debug(f"Message send to {self.target} {msg.message_id}")
        except telegram.error.TelegramError:
            self.logger.exception("Send message failed: {title} ({url}) -> {target}".format(target=self.target, **data))
            return
        else:
            return msg

    async def edit(self, msg: telegram.Message, data: BaseArticle):
        try:
            kwargs = self._make_message(data)
            msg.edit_text(**kwargs)
        except telegram.error.BadRequest as e:
            # Message to edit not found (원본메시지 못찾음)
            self.logger.error("Edit message failed (e): {title} ({url}) <- {msg_id}".format(e=e, msg_id=msg.message_id, **data))

    async def delete(self, msg: telegram.Message):
        msg.delete()

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
            "parse_mode": telegram.ParseMode.MARKDOWN_V2
        }
        return result
