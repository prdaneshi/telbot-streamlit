"""تنظیمات مشترک بین ربات و پنل مدیریت."""
from __future__ import annotations

import os
from urllib.parse import parse_qs, urlparse
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


def get_api_credentials() -> tuple[str, str] | tuple[None, None]:
    """api_id و api_hash — برای اتصال MTProto (Telethon) لازم است.

    از my.telegram.org بخش API development tools قابل دریافت است.
    """
    load_env()
    api_id = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    if api_id and api_hash:
        return api_id, api_hash
    return None, None


def get_telethon_proxy() -> dict | None:
    """تبدیل PROXY_URL به دیکشنری پروکسی که Telethon می‌فهمد.

    پشتیبانی از:
      - لینک MTProto تلگرام: https://t.me/proxy?server=..&port=..&secret=..
      - فرمت ساده:             mtproto://server:port/secret
      - پروکسی‌های معمولی:      socks5://.. http://.. (با/بدون user:pass)
    """
    raw = get_proxy()
    if not raw:
        return None

    parsed = urlparse(raw)
    if parsed.scheme in ("https", "tg") and parsed.path == "/proxy":
        q = parse_qs(parsed.query)
        return {
            "scheme": "mtproto",
            "hostname": q["server"][0],
            "port": int(q["port"][0]),
            "secret": q["secret"][0],
        }
    if parsed.scheme == "mtproto":
        return {
            "scheme": "mtproto",
            "hostname": parsed.hostname,
            "port": parsed.port,
            "secret": parsed.path.lstrip("/"),
        }
    # socks5 / socks4 / http — برای python-socks
    return {
        "scheme": parsed.scheme.replace("socks5h", "socks5"),
        "hostname": parsed.hostname,
        "port": parsed.port,
        "username": parsed.username,
        "password": parsed.password,
    }


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
