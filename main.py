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

from telegram import Update, ChatPermissions
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
logger = logging.getLogger(__name__)

# Global lock for state file operations (prevents race conditions)
_state_lock = asyncio.Lock()

# =========================
# STATE STORAGE (with lock and error handling)
# =========================
async def load_state():
    """Load state from JSON file with error handling."""
    async with _state_lock:
        default_state = {
            "last_message_id": None,
            "sent_at": None,
            "locked": False,
            "checked": False
        }
        if not os.path.exists(STATE_FILE):
            return default_state

        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                # Ensure all keys exist (in case of old/corrupt state)
                for key in default_state:
                    if key not in data:
                        data[key] = default_state[key]
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load state file: {e}. Using default state.")
            return default_state


async def save_state(state):
    """Save state to JSON file atomically."""
    async with _state_lock:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)


# =========================
# HELPERS
# =========================
async def lock_group(context: ContextTypes.DEFAULT_TYPE):
    """Lock group (set read-only). Only updates state if API call succeeds."""
    try:
        await context.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions=ChatPermissions(can_send_messages=False)
        )
        # Only update state after successful API call
        state = await load_state()
        state["locked"] = True
        await save_state(state)

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="⚠️ Group locked because daily check was not seen in 24h."
        )
        logger.info("Group locked due to missed check.")

    except Exception as e:
        logger.error(f"Failed to lock group: {e}")


async def unlock_group(context: ContextTypes.DEFAULT_TYPE):
    """Unlock group (allow sending messages). Only updates state if API call succeeds."""
    try:
        await context.bot.set_chat_permissions(
            chat_id=GROUP_ID,
            permissions=ChatPermissions(can_send_messages=True)
        )
        # Only update state after successful API call
        state = await load_state()
        state["locked"] = False
        await save_state(state)
        logger.info("Group unlocked.")

    except Exception as e:
        logger.error(f"Failed to unlock group: {e}")


# =========================
# DAILY JOB
# =========================
async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    """Run every day at CHECK_HOUR:CHECK_MINUTE.
    - Locks group if previous day's message was not confirmed.
    - Sends a new check-in message.
    """
    state = await load_state()

    # 1. Check if the previous day's message was not confirmed
    if state["sent_at"] and not state["checked"]:
        logger.info("Previous daily check not confirmed. Locking group...")
        await lock_group(context)
        # Reload state because lock_group may have updated it
        state = await load_state()

    # 2. Send new daily check message
    try:
        msg = await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="✅ **New Daily Check.**\nPlease send /seen within 24 hours.",
            parse_mode="Markdown"
        )
        # 3. Update state for the new check
        state["last_message_id"] = msg.message_id
        state["sent_at"] = datetime.utcnow().isoformat()
        state["checked"] = False
        await save_state(state)
        logger.info("New daily check message sent.")
    except Exception as e:
        logger.error(f"Failed to send daily check message: {e}")


# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("Bot running.")


async def seen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to confirm they've seen the daily check."""
    if update.effective_user.id != ADMIN_ID:
        return

    state = await load_state()
    state["checked"] = True
    state["sent_at"] = None          # Clear old timestamp
    state["last_message_id"] = None  # Clear old message ID
    await save_state(state)

    await update.message.reply_text("✅ Daily check confirmed.")
    logger.info("Admin confirmed daily check.")


async def reopen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to manually unlock the group and reset the check state."""
    if update.effective_user.id != ADMIN_ID:
        return

    # Unlock group (this updates state["locked"] = False on success)
    await unlock_group(context)

    # Additionally reset the check state so that the next daily_job doesn't lock again
    state = await load_state()
    state["checked"] = True        # Mark as confirmed
    state["sent_at"] = None        # Clear pending check
    state["last_message_id"] = None
    await save_state(state)

    await update.message.reply_text("✅ Group reopened and check state reset.")


# =========================
# PERMISSION CHECK ON STARTUP
# =========================
async def check_permissions(app: Application):
    """Verify the bot has admin rights in the group and can message the admin."""
    try:
        # Check group permissions
        chat_member = await app.bot.get_chat_member(GROUP_ID, app.bot.id)
        if chat_member.status not in ["administrator", "creator"]:
            logger.error(f"Bot is not an admin in group {GROUP_ID}. Cannot lock/unlock.")
        else:
            logger.info("Bot has admin rights in group.")

        # Test ability to message admin (try sending a startup notification)
        await app.bot.send_message(
            ADMIN_ID,
            "Bot started. Daily check-in active."
        )
        logger.info("Startup notification sent to admin.")
    except Forbidden:
        logger.error(f"Bot cannot send message to admin {ADMIN_ID}. Please start a chat with the bot first.")
    except Exception as e:
        logger.error(f"Permission check failed: {e}")


# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("seen", seen))
    app.add_handler(CommandHandler("reopen", reopen))

    # Schedule daily job
    app.job_queue.run_daily(
        daily_job,
        time=time(hour=CHECK_HOUR, minute=CHECK_MINUTE)
    )

    # Run permission checks before starting polling
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_permissions(app))

    logger.info("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()