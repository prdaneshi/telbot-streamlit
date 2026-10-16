"""تنظیمات مشترک بین ربات و پنل مدیریت."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "bot_data.db"
ENV_PATH = BASE_DIR / ".env"
PID_PATH = BASE_DIR / "bot.pid"


def load_env() -> None:
    """خواندن فایل .env بدون وابستگی خارجی (اگر python-dotenv نبود)."""
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def get_token() -> str | None:
    """توکن ربات از متغیر محیطی یا فایل .env."""
    load_env()
    return os.environ.get("TELEGRAM_BOT_TOKEN") or None


def get_proxy() -> str | None:
    """آدرس پروکسی (مثلاً socks5://127.0.0.1:10808) — اختیاری."""
    load_env()
    return os.environ.get("PROXY_URL") or None


def save_token(token: str) -> None:
    """ذخیره توکن در فایل .env."""
    lines = []
    if ENV_PATH.exists():
        lines = [
            l for l in ENV_PATH.read_text(encoding="utf-8").splitlines()
            if not l.strip().startswith("TELEGRAM_BOT_TOKEN")
        ]
    lines.append(f"TELEGRAM_BOT_TOKEN={token.strip()}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ["TELEGRAM_BOT_TOKEN"] = token.strip()
