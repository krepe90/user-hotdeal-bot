import logging
import logging.handlers
import re
from typing import Any


def escape_markdown(s: str) -> str:
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!])", "\\\\\\1", s)


class TelegramHandler(logging.handlers.HTTPHandler):
    def __init__(self, token: str, target: str, parse_mode: str = "MarkdownV2", emoji=True) -> None:
        super().__init__(host="api.telegram.org", url=f"/bot{token}/sendMessage", method="POST", secure=True)
        self.target = target
        self.parse_mode = parse_mode
        self.emoji = emoji

    def mapLogRecord(self, record: logging.LogRecord) -> dict[str, Any]:
        _emoji_list = {
            "DEBUG": "\U0001F41B ",
            "INFO": "\u270F ",
            "WARNING": "\u26A0 ",
            "ERROR": "\U0001F6AB ",
            "CRITICAL": "\U0001F6A8 "
        }
        if self.formatter is None:
            text = record.msg
        else:
            text = self.formatter.format(record)
        if self.emoji:
            text = _emoji_list.get(record.levelname, "") + text

        return {
            "chat_id": self.target,
            "text": escape_markdown(text),
            "parse_mode": self.parse_mode
        }
