"""ربات تلگرام — با python-telegram-bot اجرا می‌شود.

اجرا:  python bot.py
"""
from __future__ import annotations

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import database
from config import get_proxy, get_token

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("bot")

WELCOME = (
    "سلام {name}! 👋\n\n"
    "به ربات خوش آمدید.\n"
    "هر متنی بفرستید تا پاسخ بگیرید، یا از دکمه‌های زیر استفاده کنید."
)

MAIN_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("ℹ️ درباره ربات", callback_data="about"),
         InlineKeyboardButton("❓ راهنما", callback_data="help")],
        [InlineKeyboardButton("💬 تماس با ادمین", callback_data="contact")],
    ]
)

ABOUT_TEXT = (
    "🤖 *درباره ربات*\n\n"
    "این ربات با `python-telegram-bot` نوشته شده و یک پنل مدیریت "
    "Streamlit هم کنارش دارد."
)
HELP_TEXT = (
    "❓ *راهنما*\n\n"
    "• /start — شروع و نمایش منو\n"
    "• هر متنی بفرستید تا پاسخ بگیرید\n"
    "• با دکمه‌ی «تماس با ادمین» می‌توانید پیام بدهید"
)
CONTACT_TEXT = (
    "📩 پیام خود را همین‌جا بنویسید؛\n"
    "ادمین از پنل مدیریت پاسخ شما را می‌فرستد."
)

# بعد از این که کاربر «تماس با ادمین» را زد، پیام‌هایش دیگر echo نمی‌شود
FLAG_CONTACT = "awaiting_contact"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    database.upsert_user(user.id, user.first_name, user.username)
    database.log_message(user.id, "in", "/start")
    reply = WELCOME.format(name=user.first_name or "دوست من")
    await update.message.reply_text(reply, reply_markup=MAIN_KEYBOARD)
    database.log_message(user.id, "out", reply)


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    database.upsert_user(user.id, user.first_name, user.username)
    database.log_message(user.id, "in", f"[دکمه: {query.data}]")

    texts = {"about": ABOUT_TEXT, "help": HELP_TEXT, "contact": CONTACT_TEXT}
    reply = texts.get(query.data, "گزینه ناشناخته 🙂")
    await query.edit_message_text(reply, parse_mode=ParseMode.MARKDOWN)
    database.log_message(user.id, "out", reply)

    if query.data == "contact":
        context.user_data[FLAG_CONTACT] = True


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = update.message.text or ""
    database.upsert_user(user.id, user.first_name, user.username)
    database.log_message(user.id, "in", text)

    if context.user_data.get(FLAG_CONTACT):
        # پیام کاربر برای ادمین ثبت شده؛ فقط تأیید می‌دهیم
        context.user_data[FLAG_CONTACT] = False
        reply = "✅ پیام شما ثبت شد؛ به‌زودی پاسخ می‌گیرید."
    else:
        reply = f"پیام شما را دریافت کردم: «{text}»\nبرای منو /start را بزنید."

    await update.message.reply_text(reply)
    database.log_message(user.id, "out", reply)


def main() -> None:
    token = get_token()
    if not token:
        raise SystemExit(
            "توکن یافت نشد! TELEGRAM_BOT_TOKEN را در فایل .env یا متغیر محیطی بگذارید."
        )

    database.init_db()
    proxy = get_proxy()
    builder = Application.builder().token(token)
    if proxy:
        log.info("استفاده از پروکسی: %s", proxy)
        builder = builder.proxy(proxy).get_updates_proxy(proxy)
    app = builder.build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("ربات راه‌اندازی شد — برای توقف Ctrl+C")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
