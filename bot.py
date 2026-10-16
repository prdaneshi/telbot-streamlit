"""ربات تلگرام — با Telethon (پروتکل MTProto) اجرا می‌شود.

مزیت: پشتیبانی از پروکسی‌های MTProto (لینک‌های t.me/proxy) که
Bot API آن‌ها را نمی‌فهمد.

اجرا:  python bot.py
"""
from __future__ import annotations

import logging
import sys

from telethon import TelegramClient, events
from telethon.tl.custom import Button

import database
from config import get_token
from tg_client import make_client

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
log = logging.getLogger("bot")

WELCOME = (
    "سلام {name}! 👋\n\n"
    "به ربات خوش آمدید.\n"
    "هر متنی بفرستید تا پاسخ بگیرید، یا از دکمه‌های زیر استفاده کنید."
)

MAIN_KEYBOARD = [
    [
        Button.inline("ℹ️ درباره ربات", b"about"),
        Button.inline("❓ راهنما", b"help"),
    ],
    [Button.inline("💬 تماس با ادمین", b"contact")],
]

ABOUT_TEXT = (
    "🤖 **درباره ربات**\n\n"
    "این ربات با `Telethon` نوشته شده و یک پنل مدیریت "
    "Streamlit هم کنارش دارد."
)
HELP_TEXT = (
    "❓ **راهنما**\n\n"
    "• /start — شروع و نمایش منو\n"
    "• هر متنی بفرستید تا پاسخ بگیرید\n"
    "• با دکمه‌ی «تماس با ادمین» می‌توانید پیام بدهید"
)
CONTACT_TEXT = (
    "📩 پیام خود را همین‌جا بنویسید؛\n"
    "ادمین از پنل مدیریت پاسخ شما را می‌فرستد."
)

# بعد از «تماس با ادمین»، پیام بعدی کاربر دیگر echo نمی‌شود
awaiting_contact: set[int] = set()

client = make_client("bot_session")


@client.on(events.NewMessage(pattern=r"^/start"))
async def start(event: events.NewMessage.Event) -> None:
    sender = await event.get_sender()
    database.upsert_user(event.chat_id, sender.first_name, sender.username)
    database.log_message(event.chat_id, "in", "/start")
    reply = WELCOME.format(name=sender.first_name or "دوست من")
    await event.respond(reply, buttons=MAIN_KEYBOARD)
    database.log_message(event.chat_id, "out", reply)
    raise events.StopPropagation  # تا دسترسِ on_text نیفتد


@client.on(events.CallbackQuery)
async def on_button(event: events.CallbackQuery.Event) -> None:
    sender = await event.get_sender()
    data = event.data.decode() if event.data else ""
    database.upsert_user(event.chat_id, sender.first_name, sender.username)
    database.log_message(event.chat_id, "in", f"[دکمه: {data}]")
    await event.answer()

    texts = {"about": ABOUT_TEXT, "help": HELP_TEXT, "contact": CONTACT_TEXT}
    reply = texts.get(data, "گزینه ناشناخته 🙂")
    await event.edit(reply, parse_mode="md")
    database.log_message(event.chat_id, "out", reply)

    if data == "contact":
        awaiting_contact.add(event.chat_id)


@client.on(events.NewMessage(incoming=True))
async def on_text(event: events.NewMessage.Event) -> None:
    text = event.message.message or ""
    sender = await event.get_sender()
    database.upsert_user(event.chat_id, sender.first_name, sender.username)
    database.log_message(event.chat_id, "in", text)

    if event.chat_id in awaiting_contact:
        # پیام کاربر برای ادمین ثبت شده؛ فقط تأیید می‌دهیم
        awaiting_contact.discard(event.chat_id)
        reply = "✅ پیام شما ثبت شد؛ به‌زودی پاسخ می‌گیرید."
    else:
        reply = f"پیام شما را دریافت کردم: «{text}»\nبرای منو /start را بزنید."

    await event.respond(reply)
    database.log_message(event.chat_id, "out", reply)


def main() -> None:
    log.info("ربات راه‌اندازی شد — برای توقف Ctrl+C")
    client.start(bot_token=get_token())
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
