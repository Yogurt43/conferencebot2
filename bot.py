# bot.py
import asyncio
import threading
import logging
import traceback

from flask import Flask, request, abort
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import BOT_TOKEN, WEBHOOK_URL
from persistence import SupabasePersistence
from handlers.registration import build_registration_handler, menu_command, handle_onhold_photo
from handlers.housing import get_housing_handlers
from handlers.info import get_info_handlers
from handlers.admin import get_admin_handlers

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Flask app ────────────────────────────────────────────────────────────────
flask_app = Flask(__name__)

# ─── Async loop in background thread ─────────────────────────────────────────
loop = asyncio.new_event_loop()

def _start_loop(lp):
    asyncio.set_event_loop(lp)
    lp.run_forever()

threading.Thread(target=_start_loop, args=(loop,), daemon=True).start()


def run_async(coro):
    """Submit a coroutine to the background loop and wait for the result."""
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=60)


# ─── PTB Application ──────────────────────────────────────────────────────────
ptb_app = Application.builder().token(BOT_TOKEN).persistence(SupabasePersistence()).build()

# Register handlers
ptb_app.add_handler(build_registration_handler())
ptb_app.add_handler(CommandHandler('menu', menu_command))

for handler in get_housing_handlers():
    ptb_app.add_handler(handler)

for handler in get_info_handlers():
    # Put the free-text catcher in a lower-priority group (1) so the admin
    # deny/setting handler (group 0) always wins for admin text in the group.
    if isinstance(handler, MessageHandler):
        ptb_app.add_handler(handler, group=1)
    else:
        ptb_app.add_handler(handler)

for handler in get_admin_handlers():
    ptb_app.add_handler(handler)

# Group 1: catch photos from on_hold users who haven't re-entered via /start
ptb_app.add_handler(
    MessageHandler(filters.PHOTO | filters.Document.ALL, handle_onhold_photo),
    group=1,
)


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log all exceptions and tell the user to retry the current step."""
    logger.error("Exception in handler:\n%s", traceback.format_exc())
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Something went wrong. Please try again."
        )


ptb_app.add_error_handler(_error_handler)

# Initialize PTB
run_async(ptb_app.initialize())

# Register webhook
WEBHOOK_SECRET = BOT_TOKEN.split(':')[0]  # use token prefix as secret
run_async(ptb_app.bot.set_webhook(
    url=f"{WEBHOOK_URL}/webhook",
    secret_token=WEBHOOK_SECRET,
    allowed_updates=['message', 'callback_query'],
))
logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")


# ─── Webhook endpoint ─────────────────────────────────────────────────────────
@flask_app.route('/webhook', methods=['POST'])
def webhook():
    secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if secret != WEBHOOK_SECRET:
        abort(403)
    data = request.get_json(force=True)
    update = Update.de_json(data, ptb_app.bot)
    run_async(ptb_app.process_update(update))
    return 'ok', 200


@flask_app.route('/health', methods=['GET'])
def health():
    return 'ok', 200


if __name__ == '__main__':
    flask_app.run(host='0.0.0.0', port=8080)
