"""پنل مدیریت ربات تلگرام — با Streamlit.

اجرا:  streamlit run app.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

import database
from config import BASE_DIR, PID_PATH, get_proxy, get_token, save_token

st.set_page_config(page_title="پنل مدیریت ربات", page_icon="🤖", layout="wide")


# ---------------------------------------------------------------- کنترل ربات

def bot_pid() -> int | None:
    """PID پروسه‌ی در حال اجرای ربات (اگر باشد)."""
    if not PID_PATH.exists():
        return None
    try:
        return int(PID_PATH.read_text().strip())
    except (FileNotFoundError, ValueError):
        PID_PATH.unlink(missing_ok=True)
        return None


def is_bot_alive(pid: int) -> bool:
    try:
        # tasklist اگر PID وجود نداشته باشد خطای nonzero می‌دهد
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True, text=True,
        ).stdout
        return str(pid) in out
    except Exception:
        return False


def start_bot() -> None:
    proc = subprocess.Popen(
        [sys.executable, str(BASE_DIR / "bot.py")],
        cwd=BASE_DIR,
        stdout=open(BASE_DIR / "bot.log", "ab"),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        | subprocess.DETACHED_PROCESS,
    )
    PID_PATH.write_text(str(proc.pid))


def stop_bot(pid: int) -> None:
    subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"], capture_output=True)
    PID_PATH.unlink(missing_ok=True)


def send_messages(chat_ids: list, text: str) -> list[dict]:
    """ارسال پیام از طریق Telethon — فراخوانی sender.py به صورت زیرپروسه."""
    import json as _json

    proc = subprocess.run(
        [sys.executable, str(BASE_DIR / "sender.py")],
        input=_json.dumps({"chat_ids": chat_ids, "text": text}),
        capture_output=True, text=True, timeout=600,
        cwd=BASE_DIR, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip()[-1000:] or "sender.py failed")
    return _json.loads(proc.stdout)["results"]


# ---------------------------------------------------------------- صفحه

st.title("🤖 پنل مدیریت ربات تلگرام")

# --- تنظیم توکن ---
token = get_token()
with st.sidebar:
    st.header("⚙️ تنظیمات")
    if token:
        st.success(f"توکن تنظیم شده: `{token[:8]}...{token[-4:]}`")
    else:
        st.warning("توکن تنظیم نشده است.")
    proxy = get_proxy()
    if proxy:
        st.info(f"🌐 پروکسی: `{proxy}`")
    else:
        st.caption("🌐 پروکسی تنظیم نشده (در صورت نیاز PROXY_URL را در .env بگذارید)")
    new_token = st.text_input("توکن ربات (از @BotFather)", type="password")
    if st.button("💾 ذخیره توکن", disabled=not new_token.strip()):
        save_token(new_token.strip())
        st.rerun()

    # --- وضعیت و کنترل ربات ---
    st.divider()
    st.header("🚦 وضعیت ربات")
    pid = bot_pid()
    alive = is_bot_alive(pid) if pid else False
    if pid and not alive:
        PID_PATH.unlink(missing_ok=True)
        pid = None

    if alive:
        st.success(f"در حال اجرا (PID {pid})")
    else:
        st.info("متوقف است")

    c1, c2 = st.columns(2)
    if c1.button("▶️ اجرا", disabled=alive or not token, use_container_width=True):
        start_bot()
        st.rerun()
    if c2.button("⏹ توقف", disabled=not alive, use_container_width=True):
        stop_bot(pid)
        st.rerun()

    with st.expander("📄 لاگ ربات"):
        log_file = BASE_DIR / "bot.log"
        st.code(
            log_file.read_text(errors="replace")[-4000:] if log_file.exists()
            else "(خالی)",
            language=None,
        )

# --- آمار ---
if not token:
    st.stop()

stats = database.get_stats()
m1, m2, m3, m4 = st.columns(4)
m1.metric("👥 کاربران", stats["users"])
m2.metric("📥 پیام دریافتی", stats["in"])
m3.metric("📤 پیام ارسالی", stats["out"])
m4.metric("📅 پیام‌های امروز", stats["today"])

tab_users, tab_msgs, tab_send = st.tabs(
    ["👥 کاربران", "💬 پیام‌ها", "📨 ارسال پیام"]
)

with tab_users:
    users = database.get_users()
    if users:
        st.dataframe(
            pd.DataFrame(users).rename(
                columns={
                    "chat_id": "شناسه چت",
                    "first_name": "نام",
                    "username": "یوزرنیم",
                    "joined_at": "تاریخ عضویت",
                    "last_seen": "آخرین فعالیت",
                }
            ),
            use_container_width=True,
        )
    else:
        st.info("هنوز کاربری با ربات کار نکرده است.")

with tab_msgs:
    msgs = database.get_recent_messages()
    if msgs:
        df = pd.DataFrame(msgs).rename(
            columns={
                "id": "#",
                "chat_id": "چت",
                "first_name": "کاربر",
                "direction": "جهت",
                "text": "متن",
                "created_at": "زمان",
            }
        )
        df["جهت"] = df["جهت"].map({"in": "📥 دریافتی", "out": "📤 ارسالی"})
        st.dataframe(df, use_container_width=True, height=420)
    else:
        st.info("پیامی ثبت نشده است.")

with tab_send:
    st.subheader("ارسال پیام به یک کاربر")
    users = database.get_users()
    options = {
        f"{u['first_name'] or u['username'] or u['chat_id']} ({u['chat_id']})": u["chat_id"]
        for u in users
    }
    target = st.selectbox("گیرنده", list(options.keys()))
    text = st.text_area("متن پیام")
    if st.button("📨 ارسال", disabled=not (target and text.strip())):
        try:
            (result,) = send_messages([options[target]], text.strip())
            if result["ok"]:
                st.success("ارسال شد ✅")
            else:
                st.error(f"خطا: {result.get('error')}")
        except Exception as err:
            st.error(f"خطا در ارسال: {err}")

    st.divider()
    st.subheader("ارسال انبوه به همه کاربران")
    bulk = st.text_area("متن پیام انبوه")
    if st.button("📢 ارسال به همه", disabled=not bulk.strip()):
        chat_ids = list(options.values())
        with st.spinner(f"در حال ارسال به {len(chat_ids)} کاربر..."):
            try:
                results = send_messages(chat_ids, bulk.strip())
                ok = sum(1 for r in results if r["ok"])
                st.info(f"✅ {ok} موفق — ❌ {len(results) - ok} ناموفق")
            except Exception as err:
                st.error(f"خطا در ارسال انبوه: {err}")
