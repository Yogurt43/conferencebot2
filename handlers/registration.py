# handlers/registration.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode

import db
import utils
from strings import t
from config import PAYMENT_LINK, GROUP_CHAT_ID

# Conversation states
LANG, NAME, AGE, GENDER, PHONE, PAYMENT_STEP, RECEIPT = range(7)


def _lang_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en'),
         InlineKeyboardButton("🇺🇦 Українська", callback_data='lang_uk')]
    ])


def _gender_keyboard(lang: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, 'btn_male'), callback_data='gender_M'),
         InlineKeyboardButton(t(lang, 'btn_female'), callback_data='gender_F')]
    ])


def _phone_keyboard(lang: str):
    btn = KeyboardButton(t(lang, 'btn_share_phone'), request_contact=True)
    return ReplyKeyboardMarkup([[btn]], one_time_keyboard=True, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    participant = db.get_participant(chat_id)

    if participant:
        lang = utils.get_lang(participant)
        status = participant['status']

        if status == 'approved':
            await _show_main_menu(update, lang)
            return ConversationHandler.END

        if status in ('pending_payment', 'pending_approval'):
            await update.message.reply_text(t(lang, 'already_pending'))
            return ConversationHandler.END

        if status == 'denied':
            await update.message.reply_text(
                t(lang, 'denied_resubmit', reason=participant.get('denial_reason', '—')),
                parse_mode=ParseMode.MARKDOWN
            )
            # Jump straight to receipt upload — they don't redo the whole form
            db.update_participant(chat_id, {'status': 'pending_payment'})
            return RECEIPT

    # New user — start language selection
    await update.message.reply_text(
        t('en', 'choose_lang'),
        reply_markup=_lang_keyboard()
    )
    return LANG


async def handle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = query.data.replace('lang_', '')
    chat_id = update.effective_chat.id
    username = update.effective_user.username or ''

    db.upsert_participant({'chat_id': chat_id, 'username': username, 'lang': lang, 'status': 'incomplete'})
    context.user_data['lang'] = lang

    await query.edit_message_text(t(lang, 'welcome_new'), parse_mode=ParseMode.MARKDOWN)
    await query.message.reply_text(t(lang, 'enter_name'), parse_mode=ParseMode.MARKDOWN)
    return NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _get_lang(update, context)
    name = update.message.text.strip()
    context.user_data['full_name'] = name
    db.update_participant(update.effective_chat.id, {'full_name': name})

    await update.message.reply_text(t(lang, 'enter_age'), parse_mode=ParseMode.MARKDOWN)
    return AGE


async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _get_lang(update, context)
    age = utils.validate_age(update.message.text)

    if age is None:
        await update.message.reply_text(t(lang, 'invalid_age'))
        return AGE

    context.user_data['age'] = age
    db.update_participant(update.effective_chat.id, {'age': age})

    await update.message.reply_text(t(lang, 'choose_gender'), reply_markup=_gender_keyboard(lang))
    return GENDER


async def handle_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = _get_lang(update, context)
    gender = query.data.replace('gender_', '')
    context.user_data['gender'] = gender

    db.update_participant(update.effective_chat.id, {'gender': gender})

    await query.edit_message_text(t(lang, 'choose_gender') + f" ✅")
    await query.message.reply_text(
        t(lang, 'share_phone'),
        reply_markup=_phone_keyboard(lang)
    )
    return PHONE


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _get_lang(update, context)

    if not update.message.contact:
        await update.message.reply_text(t(lang, 'share_phone'), reply_markup=_phone_keyboard(lang))
        return PHONE

    phone = update.message.contact.phone_number
    db.update_participant(update.effective_chat.id, {'phone': phone, 'status': 'pending_payment'})

    await update.message.reply_text(
        t(lang, 'payment_instructions', payment_link=PAYMENT_LINK),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN
    )
    await update.message.reply_text(t(lang, 'upload_receipt'), parse_mode=ParseMode.MARKDOWN)
    return RECEIPT


async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _get_lang(update, context)
    chat_id = update.effective_chat.id

    # Accept photo or document
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text(t(lang, 'upload_receipt'), parse_mode=ParseMode.MARKDOWN)
        return RECEIPT

    participant = db.get_participant(chat_id)
    db.save_receipt(participant['id'], file_id)
    db.update_participant(chat_id, {'status': 'pending_approval'})

    await update.message.reply_text(t(lang, 'receipt_submitted'))

    # Notify admin group
    if GROUP_CHAT_ID:
        name = participant.get('full_name', 'Unknown')
        age = participant.get('age', '?')
        gender = participant.get('gender', '?')
        username = participant.get('username', '')
        uname_str = f"@{username}" if username else f"ID: {chat_id}"
        admin_text = (
            f"📥 *New registration pending review*\n\n"
            f"👤 {name} | {age}y | {gender}\n"
            f"📱 {uname_str}\n"
            f"🆔 `{chat_id}`\n\n"
            f"Use `/approve {chat_id}` or `/deny {chat_id} <reason>`\n"
            f"Use `/viewreceipt {chat_id}` to see the receipt."
        )
        await context.bot.send_message(GROUP_CHAT_ID, admin_text, parse_mode=ParseMode.MARKDOWN)

    return ConversationHandler.END


def _get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Get lang from user_data cache or DB."""
    lang = context.user_data.get('lang')
    if not lang:
        p = db.get_participant(update.effective_chat.id)
        lang = utils.get_lang(p)
        context.user_data['lang'] = lang
    return lang


async def _show_main_menu(update: Update, lang: str):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, 'btn_housing'), callback_data='menu_housing')],
        [InlineKeyboardButton(t(lang, 'btn_schedule'), callback_data='menu_schedule'),
         InlineKeyboardButton(t(lang, 'btn_venue'), callback_data='menu_venue')],
        [InlineKeyboardButton(t(lang, 'btn_qa'), callback_data='menu_qa')],
        [InlineKeyboardButton(t(lang, 'btn_coordinator'), callback_data='menu_coordinator')],
    ])
    await update.message.reply_text(
        t(lang, 'main_menu'),
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu to approved participants."""
    chat_id = update.effective_chat.id
    participant = db.get_participant(chat_id)
    if not participant or participant['status'] != 'approved':
        lang = utils.get_lang(participant)
        await update.message.reply_text(t(lang, 'not_approved'))
        return
    lang = utils.get_lang(participant)
    await _show_main_menu(update, lang)


def build_registration_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANG:         [CallbackQueryHandler(handle_lang, pattern='^lang_')],
            NAME:         [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            AGE:          [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age)],
            GENDER:       [CallbackQueryHandler(handle_gender, pattern='^gender_')],
            PHONE:        [MessageHandler(filters.CONTACT, handle_phone)],
            PAYMENT_STEP: [],  # user just reads the message and sends receipt
            RECEIPT:      [MessageHandler(filters.PHOTO | filters.Document.ALL, handle_receipt)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True,
        name='registration',
        persistent=False,
        per_message=False,
    )
