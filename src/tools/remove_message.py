# 중복해서 보내진 메시지를 삭제하기 위한 스크립트
# 사용법: python ./tools/remove_message.py -i dump.json

import argparse
import asyncio
import json

import telegram

import bot


async def remove_all_messages(file_path: str):
    with open("config.json", "r") as f:
        config: dict = json.load(f)
    with open(file_path, "r") as f:
        data: dict = json.load(f)

    bot_data: dict[str, bot.SerializedBotData] = data.get("bot", {})
    bot_data_tg = bot_data.get("telegram", {})

    if not bot_data_tg:
        return

    bot_tg = bot.TelegramBot("telegram", config["bots"]["telegram"]["kwargs"]["token"], config["bots"]["telegram"]["kwargs"]["target"])
    await bot_tg.from_dict(bot_data_tg)

    # Remove all messages
    for crawler_name, chats in bot_tg.cache.items():
        for article_id, msg in chats.items():
            try:
                await msg.delete()
                print(f"Removed message: {msg.id} ({crawler_name}, {article_id})")
            except telegram.error.BadRequest as e:
                print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="dump.json file path")
    args = parser.parse_args()
    asyncio.run(remove_all_messages(args.input))


if __name__ == "__main__":
    main()
