# handlers/info.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

import db
import utils
from strings import t
from config import QA_RATE_LIMIT, GROUP_CHAT_ID, PRICE_WITH_HOUSING, PRICE_WITHOUT_HOUSING

# Reply-keyboard button texts for both languages.
# The schedule/venue/qa/coordinator buttons are caught by their own MessageHandlers
# in group 1 (before the catch-all), so only housing needs to be guarded here.
_HOUSING_TEXTS = {t('en', 'btn_housing'), t('uk', 'btn_housing')}

# All menu button texts used to build MessageHandler filters (schedule, venue, qa, coord)
_SCHEDULE_TEXTS = [t('en', 'btn_schedule'), t('uk', 'btn_schedule')]
_QA_TEXTS       = [t('en', 'btn_qa'),       t('uk', 'btn_qa')]
_COORD_TEXTS    = [t('en', 'btn_coordinator'), t('uk', 'btn_coordinator')]


def _md_escape(s: str) -> str:
    return s.replace('_', r'\_').replace('*', r'\*').replace('`', r'\`').replace('[', r'\[')


def _contact_line(participant: dict) -> str:
    """Return a Markdown contact line for admin notifications.

    Preference order:
      1. @username  → clickable Telegram profile link
      2. phone + tg://user deep link
      3. tg://user deep link only
    """
    username = participant.get('username', '')
    phone    = participant.get('phone', '')
    chat_id  = participant.get('chat_id', '')

    if username:
        return f"[@{username}](https://t.me/{username})"
    if phone:
        return f"☎️ {phone} · [Open chat](tg://user?id={chat_id})"
    return f"[Open chat](tg://user?id={chat_id})"


# In-memory state for "expecting message" (keyed by chat_id)
_awaiting_qa: set[int] = set()
_awaiting_msg: set[int] = set()


async def handle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    participant = db.get_participant(update.effective_chat.id)
    if not participant or participant.get('status') != 'approved':
        return
    lang = utils.get_lang(participant)
    text = db.get_setting('schedule_text')
    await update.message.reply_text(text or t(lang, 'no_schedule'), parse_mode=ParseMode.MARKDOWN)



async def handle_qa_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    participant = db.get_participant(chat_id)
    if not participant or participant.get('status') != 'approved':
        return
    lang = utils.get_lang(participant)

    if db.is_paused('qa'):
        await update.message.reply_text(t(lang, 'qa_paused'))
        return

    count = db.count_questions_by_participant(participant['id'])
    if count >= QA_RATE_LIMIT:
        await update.message.reply_text(t(lang, 'qa_rate_limited', limit=QA_RATE_LIMIT))
        return

    _awaiting_qa.add(chat_id)
    await update.message.reply_text(t(lang, 'qa_prompt'))


async def handle_coordinator_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    participant = db.get_participant(chat_id)
    if not participant or participant.get('status') != 'approved':
        return
    lang = utils.get_lang(participant)

    if db.is_paused('messages'):
        await update.message.reply_text(t(lang, 'messages_paused'))
        return

    _awaiting_msg.add(chat_id)
    await update.message.reply_text(t(lang, 'coordinator_prompt'))


async def handle_coordinator_pre_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """❓ Have a Question? button — available during registration (receipt step and on-hold)."""
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    participant = db.get_participant(chat_id)
    lang = utils.get_lang(participant)

    _awaiting_msg.add(chat_id)
    # Send a NEW message — never edit the receipt/on-hold message so it stays usable
    await context.bot.send_message(
        chat_id,
        t(lang, 'question_prompt_pre_approval'),
        parse_mode=ParseMode.MARKDOWN,
    )


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches free-text from users who are in QA or coordinator message flow."""
    chat_id = update.effective_chat.id

    # Housing button is caught by its own MessageHandler in group 0, but group 1
    # still fires afterwards — ignore it here so it isn't treated as user input.
    if update.message.text.strip() in _HOUSING_TEXTS:
        return

    # Early-exit: skip DB calls entirely if this chat isn't waiting for input.
    # This prevents spurious Supabase errors from surfacing as "Something went wrong"
    # on admin hold/deny messages (which are handled in group 0, but group 1 still fires).
    if chat_id not in _awaiting_qa and chat_id not in _awaiting_msg:
        # If the user is approved and typing random text, remind them to use the menu.
        participant = db.get_participant(chat_id)
        if participant and participant.get('status') == 'approved':
            lang = utils.get_lang(participant)
            await update.message.reply_text(t(lang, 'use_menu_buttons'))
        return

    participant = db.get_participant(chat_id)
    lang = utils.get_lang(participant)
    text = update.message.text.strip()

    # Resolve the organiser channel once — used by both Q&A and messages
    def _org_channel():
        stored = db.get_setting('coord_channel_id')
        return int(stored) if stored else GROUP_CHAT_ID

    if chat_id in _awaiting_qa:
        _awaiting_qa.discard(chat_id)
        db.save_question(participant['id'], text)
        await update.message.reply_text(t(lang, 'qa_submitted'))
        target = _org_channel()
        if target:
            name = participant.get('full_name', 'Unknown')
            name_safe = _md_escape(name)
            text_safe = _md_escape(text)
            await context.bot.send_message(
                target,
                f"❓ *Question from {name_safe}*\n"
                f"{_contact_line(participant)}\n\n"
                f"{text_safe}",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    if chat_id in _awaiting_msg:
        _awaiting_msg.discard(chat_id)

        status = participant.get('status', '') if participant else ''
        is_pre_approval = status in ('pending_payment', 'pending_approval', 'on_hold')

        target = _org_channel()

        if is_pre_approval and participant:
            # Enhanced notification with amount due and contact info
            amount = PRICE_WITH_HOUSING if participant.get('needs_housing') else PRICE_WITHOUT_HOUSING
            housing_label = 'with housing' if participant.get('needs_housing') else 'no housing'
            p_username = participant.get('username', '')
            p_phone    = participant.get('phone', '—')
            p_chat_id  = participant.get('chat_id', chat_id)

            if p_username:
                contact_line = f"[@{p_username}](https://t.me/{p_username})"
            else:
                contact_line = f"☎️ {p_phone} · [Open chat](tg://user?id={p_chat_id})"

            status_labels = {
                'pending_payment':  '⏳ Pending payment',
                'pending_approval': '⏳ Pending review',
                'on_hold':          '⏸ On Hold',
            }
            status_str = status_labels.get(status, '⏳ Pending')
            name = participant.get('full_name', 'Unknown')
            name_safe = _md_escape(name)
            text_safe = _md_escape(text)

            if target:
                await context.bot.send_message(
                    target,
                    f"📨 *Message from pending registrant*\n\n"
                    f"👤 *{name_safe}* · status: {status_str}\n"
                    f"💳 Amount due: *{amount}* ({housing_label})\n"
                    f"{contact_line}\n\n"
                    f"_{text_safe}_",
                    parse_mode=ParseMode.MARKDOWN,
                )
            await update.message.reply_text(
                t(lang, 'question_sent_pre_approval'),
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            # Post-approval: existing coordinator message flow
            if participant:
                db.save_message(participant['id'], text)
            await update.message.reply_text(t(lang, 'coordinator_submitted'))
            if target:
                name = participant.get('full_name', 'Unknown') if participant else 'Unknown'
                name_safe = _md_escape(name)
                text_safe = _md_escape(text)
                contact = _contact_line(participant) if participant else ''
                await context.bot.send_message(
                    target,
                    f"📨 *Message from {name_safe}*\n"
                    f"{contact}\n\n"
                    f"_{text_safe}_",
                    parse_mode=ParseMode.MARKDOWN,
                )
        return


def get_info_handlers() -> list:
    return [
        # Reply-keyboard menu buttons — specific text matches must come BEFORE
        # the catch-all text handler so they win within group 1.
        MessageHandler(filters.Text(_SCHEDULE_TEXTS), handle_schedule),
        MessageHandler(filters.Text(_QA_TEXTS),       handle_qa_start),
        MessageHandler(filters.Text(_COORD_TEXTS),    handle_coordinator_start),
        # Pre-approval "Have a question?" — still an inline button during registration
        CallbackQueryHandler(handle_coordinator_pre_approval,  pattern='^pre_approval_question$'),
        # Catch-all free-text (Q&A answers, coordinator messages)
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input),
    ]
