import os
import json


def v1_to_v2(dump_file_path: str):
    with open(dump_file_path, "r") as f:
        old: dict[str, dict[str, dict]] = json.load(f)
    _crawler = {}
    _bot = {}
    for c_name, c_msgs in old.items():
        for msg_id, msg in c_msgs.items():
            msg_obj: dict = msg.pop("message")
            if c_name not in _crawler:
                _crawler[c_name] = {}
            _crawler[c_name][msg_id] = msg
            _crawler[c_name][msg_id]["crawler_name"] = c_name
            for bot_name, bot_chat in msg_obj.items():
                if bot_name not in _bot:
                    _bot[bot_name] = {"queue": [], "cache": {}}
                if c_name not in _bot[bot_name]:
                    _bot[bot_name]["cache"][c_name] = {}
                _bot[bot_name]["cache"][c_name][msg_id] = bot_chat

    new = {
        "version": "v2.0.0",
        "crawler": _crawler,
        "bot": _bot
    }

    with open(dump_file_path, "w") as f:
        json.dump(new, f, ensure_ascii=False, indent=2)
    return new


if __name__ == "__main__":
    # copy
    os.system("cp dump.json dump.json")
    v1_to_v2("dump.json")
