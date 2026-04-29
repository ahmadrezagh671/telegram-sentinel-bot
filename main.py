# main.py
# Telegram bot:
# - Sends a daily check-in message to ONE admin at a specific time
# - If admin does not read it within 24h -> group becomes read-only
# - Admin can reopen with /reopen
# - Only works for the configured admin ID

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta, time

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from telegram.error import Forbidden, BadRequest

# =========================
# CONFIG FROM ENV VARIABLES
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GROUP_ID = int(os.getenv("GROUP_ID"))
CHECK_HOUR = int(os.getenv("CHECK_HOUR", "21"))      # 21:00
CHECK_MINUTE = int(os.getenv("CHECK_MINUTE", "0"))

STATE_FILE = "state.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# =========================
# STATE STORAGE
# =========================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "last_message_id": None,
            "sent_at": None,
            "locked": False,
            "checked": False
        }

    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


state = load_state()


# =========================
# HELPERS
# =========================
async def lock_group(context: ContextTypes.DEFAULT_TYPE):
    global state

    try:
        await context.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions={
                "can_send_messages": False
            }
        )
        state["locked"] = True
        save_state(state)

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="⚠️ Group locked because daily check was not seen in 24h."
        )

    except Exception as e:
        print("Lock error:", e)


async def unlock_group(context: ContextTypes.DEFAULT_TYPE):
    global state

    try:
        await context.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions={
                "can_send_messages": True
            }
        )
        state["locked"] = False
        save_state(state)

    except Exception as e:
        print("Unlock error:", e)


# =========================
# DAILY MESSAGE
# =========================
async def send_daily_check(context: ContextTypes.DEFAULT_TYPE):
    global state

    msg = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text="✅ Daily check.\nPlease read this message within 24 hours."
    )

    state["last_message_id"] = msg.message_id
    state["sent_at"] = datetime.utcnow().isoformat()
    state["checked"] = False
    save_state(state)


# =========================
# VERIFY AFTER 24 HOURS
# =========================
async def verify_seen(context: ContextTypes.DEFAULT_TYPE):
    global state

    if not state["sent_at"]:
        return

    sent_time = datetime.fromisoformat(state["sent_at"])
    now = datetime.utcnow()

    if now < sent_time + timedelta(hours=24):
        return

    if state["checked"]:
        return

    # Telegram bots cannot truly detect "seen/read receipts" in private chats.
    # So we use admin activity with /seen command or any command.
    await lock_group(context)


# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text("Bot running.")


async def seen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global state

    if update.effective_user.id != ADMIN_ID:
        return

    state["checked"] = True
    save_state(state)

    await update.message.reply_text("✅ Daily check confirmed.")


async def reopen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global state

    if update.effective_user.id != ADMIN_ID:
        return

    await unlock_group(context)
    await update.message.reply_text("✅ Group reopened.")


# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("seen", seen))
    app.add_handler(CommandHandler("reopen", reopen))

    # daily message every day
    app.job_queue.run_daily(
        send_daily_check,
        time=time(hour=CHECK_HOUR, minute=CHECK_MINUTE)
    )

    # check every hour
    app.job_queue.run_repeating(
        verify_seen,
        interval=3600,
        first=60
    )

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()