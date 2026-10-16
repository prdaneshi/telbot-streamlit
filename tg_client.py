"""ساخت کلاینت مشترک Telethon — استفاده مشترک بین bot.py و sender.py."""
from __future__ import annotations

import logging

from telethon import TelegramClient

import database
from config import get_api_credentials, get_telethon_proxy, get_token

log = logging.getLogger(__name__)


def check_credentials() -> None:
    """خطای واضح اگر توکن یا api credentials تنظیم نشده باشند."""
    if not get_token():
        raise SystemExit(
            "توکن یافت نشد! TELEGRAM_BOT_TOKEN را در فایل .env یا متغیر محیطی بگذارید."
        )
    api_id, api_hash = get_api_credentials()
    if not api_id:
        raise SystemExit(
            "API_ID و API_HASH یافت نشد! از my.telegram.org (بخش API development "
            "tools) بگیرید و در فایل .env بگذارید."
        )


def make_client(session: str) -> TelegramClient:
    """کلاینت Telethon با تنظیمات .env (توکن، api credentials، پروکسی)."""
    check_credentials()
    api_id, api_hash = get_api_credentials()

    proxy = get_telethon_proxy()
    if proxy:
        log.info("استفاده از پروکسی: %s", proxy)

    database.init_db()
    return TelegramClient(session, int(api_id), api_hash, proxy=proxy)
