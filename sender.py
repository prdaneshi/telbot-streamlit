"""ارسال پیام از پنل — از طریق Telethon (MTProto).

پنل این اسکریپت را به صورت زیرپروسه صدا می‌زند و JSON را از stdin می‌گیرد:
    {"chat_ids": [123, 456], "text": "سلام"}

خروجی (stdout):  {"results": [{"chat_id": 123, "ok": true}, ...]}
"""
from __future__ import annotations

import json
import sys

from telethon import TelegramClient
from telethon.errors import RPCError

import database
from config import get_token
from tg_client import make_client

# سشن جدا از ربات تا قفل فایل bot_session تداخل نکند
client = make_client("panel_session")
client.flood_sleep_threshold = 60


def main() -> None:
    payload = json.loads(sys.stdin.read())
    chat_ids = payload["chat_ids"]
    text = payload["text"]

    results = []
    with client:
        client.start(bot_token=get_token())
        for chat_id in chat_ids:
            try:
                client.send_message(chat_id, text)
                database.log_message(chat_id, "out", text)
                results.append({"chat_id": chat_id, "ok": True})
            except RPCError as err:
                results.append(
                    {"chat_id": chat_id, "ok": False, "error": str(err)}
                )
    print(json.dumps({"results": results}, ensure_ascii=False))


if __name__ == "__main__":
    main()
