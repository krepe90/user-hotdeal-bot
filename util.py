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
        # formatter
        record.message = record.getMessage()
        if self.formatter is None:
            text = record.message
        else:
            if self.formatter.usesTime():
                record.asctime = self.formatter.formatTime(record, self.formatter.datefmt)
            text = self.formatter.formatMessage(record)
        if self.emoji:
            text = _emoji_list.get(record.levelname, "") + text

        escaped_text = escape_markdown(text)
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatter.formatException(record.exc_info)
            escaped_text += "\n```\n" + record.exc_text + "\n```"

        return {
            "chat_id": self.target,
            "text": escaped_text,
            "parse_mode": self.parse_mode,
            "disable_web_page_preview": True
        }
