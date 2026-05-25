# handlers/registration.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.constants import ParseMode

import db
import utils
from strings import t
from config import PAYMENT_LINK, GROUP_CHAT_ID, OWNER_ID, PRICE_WITH_HOUSING, PRICE_WITHOUT_HOUSING


def _md_escape(s: str) -> str:
    return s.replace('_', r'\_').replace('*', r'\*').replace('`', r'\`').replace('[', r'\[')


# Conversation states
LANG, NAME, AGE, GENDER, HOUSING_PREF, HOUSE_SELECT, PHONE, PAYMENT_STEP, RECEIPT = range(9)


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


def _housing_keyboard(lang: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, 'btn_housing_yes'), callback_data='housing_yes'),
         InlineKeyboardButton(t(lang, 'btn_housing_no'),  callback_data='housing_no')]
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
            db.update_participant(chat_id, {'status': 'pending_payment'})
            # Housing question is mandatory — ask it if not yet answered
            if participant.get('needs_housing') is None:
                await update.message.reply_text(
                    t(lang, 'housing_pref_with_price',
                      price_housing=PRICE_WITH_HOUSING,
                      price_no_housing=PRICE_WITHOUT_HOUSING),
                    reply_markup=_housing_keyboard(lang),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return HOUSING_PREF
            # Needs housing but tentative was released on denial — re-select
            if participant.get('needs_housing') and not db.get_reservation(participant['id']):
                gender = participant.get('gender', 'M')
                houses = db.get_houses_for_gender(gender)
                if houses:
                    buttons = [
                        [InlineKeyboardButton(
                            utils.format_house_button(h, db.get_house_occupancy(h['id']), lang),
                            callback_data=f"reg_house_{h['id']}"
                        )]
                        for h in houses
                    ]
                    await update.message.reply_text(
                        t(lang, 'housing_list_header'),
                        reply_markup=InlineKeyboardMarkup(buttons),
                    )
                    return HOUSE_SELECT
            # Straight to receipt
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'btn_have_question'), callback_data='pre_approval_question')
            ]])
            await update.message.reply_text(
                t(lang, 'upload_receipt'),
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
            )
            return RECEIPT

        if status == 'on_hold':
            reason = participant.get('denial_reason', '—')
            await update.message.reply_text(
                t(lang, 'on_hold_resubmit', reason=reason),
                parse_mode=ParseMode.MARKDOWN,
            )
            db.update_participant(chat_id, {'status': 'pending_payment'})
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'btn_have_question'), callback_data='pre_approval_question')
            ]])
            await update.message.reply_text(
                t(lang, 'upload_receipt'),
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
            )
            return RECEIPT

    # New user — language selection
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
    lang  = _get_lang(update, context)
    words = update.message.text.strip().split()

    if len(words) < 2:
        await update.message.reply_text(t(lang, 'invalid_name'))
        return NAME

    # Auto-capitalize each word (e.g. "john smith" → "John Smith")
    name = ' '.join(word.capitalize() for word in words)
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

    await query.edit_message_text(t(lang, 'choose_gender') + " ✅")
    await query.message.reply_text(
        t(lang, 'housing_pref_with_price',
          price_housing=PRICE_WITH_HOUSING,
          price_no_housing=PRICE_WITHOUT_HOUSING),
        reply_markup=_housing_keyboard(lang),
        parse_mode=ParseMode.MARKDOWN,
    )
    return HOUSING_PREF


async def handle_housing_pref(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = _get_lang(update, context)
    needs_housing = query.data == 'housing_yes'
    context.user_data['needs_housing'] = needs_housing
    db.update_participant(update.effective_chat.id, {'needs_housing': needs_housing})

    if needs_housing:
        await query.edit_message_text(
            t(lang, 'housing_pref_with_price',
              price_housing=PRICE_WITH_HOUSING,
              price_no_housing=PRICE_WITHOUT_HOUSING)
            + f"\n\n{t(lang, 'btn_housing_yes')}",
            parse_mode=ParseMode.MARKDOWN,
        )
        # Show the house list inline
        participant = db.get_participant(update.effective_chat.id)
        gender = context.user_data.get('gender') or participant.get('gender', 'M')
        houses = db.get_houses_for_gender(gender)
        if not houses:
            await query.message.reply_text(
                t(lang, 'no_houses_available'),
                parse_mode=ParseMode.MARKDOWN,
            )
            # No houses yet — skip to phone; housing can be picked from menu later
            await query.message.reply_text(
                t(lang, 'share_phone'),
                reply_markup=_phone_keyboard(lang),
            )
            return PHONE
        buttons = [
            [InlineKeyboardButton(
                utils.format_house_button(h, db.get_house_occupancy(h['id']), lang),
                callback_data=f"reg_house_{h['id']}"
            )]
            for h in houses
        ]
        await query.message.reply_text(
            t(lang, 'housing_list_header'),
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return HOUSE_SELECT
    else:
        await query.edit_message_text(
            t(lang, 'housing_pref_with_price',
              price_housing=PRICE_WITH_HOUSING,
              price_no_housing=PRICE_WITHOUT_HOUSING)
            + f"\n\n{t(lang, 'btn_housing_no')}",
            parse_mode=ParseMode.MARKDOWN,
        )
        await query.message.reply_text(
            t(lang, 'share_phone'),
            reply_markup=_phone_keyboard(lang),
        )
        return PHONE


async def handle_house_select_reg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """House selection during registration — creates a tentative reservation."""
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    lang = _get_lang(update, context)

    house_id = query.data.replace('reg_house_', '')
    house = db.get_house_by_id(house_id)
    if not house:
        await query.edit_message_text(t(lang, 'error_generic'))
        return HOUSE_SELECT

    taken = db.get_house_occupancy(house_id)
    if taken >= house['capacity']:
        # House filled up while user was looking — re-render the list
        participant = db.get_participant(chat_id)
        gender = context.user_data.get('gender') or participant.get('gender', 'M')
        houses = db.get_houses_for_gender(gender)
        if not houses:
            await query.edit_message_text(
                t(lang, 'no_houses_available'),
                parse_mode=ParseMode.MARKDOWN,
            )
            await query.message.reply_text(
                t(lang, 'share_phone'),
                reply_markup=_phone_keyboard(lang),
            )
            return PHONE
        buttons = [
            [InlineKeyboardButton(
                utils.format_house_button(h, db.get_house_occupancy(h['id']), lang),
                callback_data=f"reg_house_{h['id']}"
            )]
            for h in houses
        ]
        await query.edit_message_text(
            t(lang, 'house_full_msg') + '\n\n' + t(lang, 'housing_list_header'),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )
        return HOUSE_SELECT

    participant = db.get_participant(chat_id)
    if not participant:
        raise RuntimeError(f"handle_house_select_reg: participant not found for chat_id={chat_id}")
    # Release any prior tentative reservation (re-entry case)
    db.release_tentative_reservation(participant['id'])
    db.create_tentative_reservation(house_id, participant['id'])

    await query.edit_message_text(
        t(lang, 'house_selected_tentative', name=house['name']),
        parse_mode=ParseMode.MARKDOWN,
    )
    await query.message.reply_text(
        t(lang, 'share_phone'),
        reply_markup=_phone_keyboard(lang),
    )
    return PHONE


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _get_lang(update, context)

    if not update.message.contact:
        await update.message.reply_text(t(lang, 'share_phone'), reply_markup=_phone_keyboard(lang))
        return PHONE

    phone = update.message.contact.phone_number
    db.update_participant(update.effective_chat.id, {'phone': phone, 'status': 'pending_payment'})

    needs_housing = context.user_data.get('needs_housing')
    if needs_housing is None:
        participant = db.get_participant(update.effective_chat.id)
        needs_housing = participant.get('needs_housing', False)
    amount = PRICE_WITH_HOUSING if needs_housing else PRICE_WITHOUT_HOUSING

    await update.message.reply_text(
        t(lang, 'payment_instructions', payment_link=PAYMENT_LINK, amount=amount),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang, 'btn_have_question'), callback_data='pre_approval_question')
    ]])
    await update.message.reply_text(
        t(lang, 'upload_receipt'),
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )
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
    if not participant:
        raise RuntimeError(f"handle_receipt: participant not found for chat_id={chat_id}")
    db.save_receipt(participant['id'], file_id)

    await update.message.reply_text(t(lang, 'receipt_submitted'))

    notify_chat = GROUP_CHAT_ID or OWNER_ID
    name        = participant.get('full_name', 'Unknown')
    age         = participant.get('age', '?')
    gender      = 'M' if participant.get('gender') == 'M' else 'F'
    phone_val   = participant.get('phone', '—')
    username    = participant.get('username', '')
    housing_raw = participant.get('needs_housing')
    if housing_raw:
        reservation = db.get_reservation(participant['id'])
        if reservation and reservation.get('houses'):
            housing_str = f"🏠 Needs housing · {reservation['houses']['name']}"
        else:
            housing_str = '🏠 Needs housing · No house selected'
    else:
        housing_str = '🏡 Has own housing'

    name_safe     = _md_escape(name)
    phone_safe    = _md_escape(str(phone_val))

    # Clickable contact: @username deep-link, or phone + tg://user fallback
    if username:
        contact_str = f"[@{username}](https://t.me/{username})"
    else:
        contact_str = f"☎️ {phone_safe} · [Open chat](tg://user?id={chat_id})"

    is_resubmit = bool(participant.get('notify_chat_id'))

    if is_resubmit:
        caption = (
            f"🔄 *Re-submission* — {name_safe}\n"
            f"Previous submission already reviewed\n\n"
            f"👤 *{name_safe}* | {age}y | {gender}\n"
            f"{contact_str}\n"
            f"{housing_str}\n"
            f"🆔 `{chat_id}`"
        )
    else:
        caption = (
            f"📥 *New registration pending review*\n\n"
            f"👤 *{name_safe}* | {age}y | {gender}\n"
            f"{contact_str}\n"
            f"{housing_str}\n"
            f"🆔 `{chat_id}`"
        )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{chat_id}"),
        InlineKeyboardButton("⏸ On Hold",  callback_data=f"admin_hold_{chat_id}"),
        InlineKeyboardButton("❌ Deny",    callback_data=f"admin_deny_{chat_id}"),
    ]])

    # Re-submissions reply to the original thread
    reply_to = participant.get('notify_msg_id') if is_resubmit else None
    notify_chat_id = participant.get('notify_chat_id') or notify_chat

    try:
        result = await context.bot.send_photo(
            notify_chat_id,
            file_id,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            reply_to_message_id=reply_to,
        )
    except Exception:
        # Original message may have been deleted — send without threading
        result = await context.bot.send_photo(
            notify_chat_id,
            file_id,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )

    # Store notification coordinates so re-submissions can thread correctly
    if not is_resubmit:
        db.update_participant(chat_id, {
            'notify_chat_id': notify_chat_id,
            'notify_msg_id':  result.message_id,
        })

    # Update status to pending_approval
    db.update_participant(chat_id, {'status': 'pending_approval'})

    return ConversationHandler.END


async def _prompt_use_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User typed text when an inline button response was expected — nudge them."""
    lang = _get_lang(update, context)
    await update.message.reply_text(t(lang, 'use_buttons'))
    # Return None → ConversationHandler keeps the current state


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


async def _send_main_menu_to(bot, chat_id: int, lang: str) -> None:
    """Send the main menu as a new message. Used by admin approval (no Update object)."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, 'btn_housing'), callback_data='menu_housing')],
        [InlineKeyboardButton(t(lang, 'btn_schedule'), callback_data='menu_schedule'),
         InlineKeyboardButton(t(lang, 'btn_venue'), callback_data='menu_venue')],
        [InlineKeyboardButton(t(lang, 'btn_qa'), callback_data='menu_qa')],
        [InlineKeyboardButton(t(lang, 'btn_coordinator'), callback_data='menu_coordinator')],
    ])
    await bot.send_message(
        chat_id,
        t(lang, 'main_menu'),
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
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
            LANG:         [CallbackQueryHandler(handle_lang, pattern='^lang_'),
                           MessageHandler(filters.TEXT & ~filters.COMMAND, _prompt_use_buttons)],
            NAME:         [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            AGE:          [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age)],
            GENDER:       [CallbackQueryHandler(handle_gender, pattern='^gender_'),
                           MessageHandler(filters.TEXT & ~filters.COMMAND, _prompt_use_buttons)],
            HOUSING_PREF: [CallbackQueryHandler(handle_housing_pref, pattern='^housing_'),
                           MessageHandler(filters.TEXT & ~filters.COMMAND, _prompt_use_buttons)],
            HOUSE_SELECT: [CallbackQueryHandler(handle_house_select_reg, pattern='^reg_house_[0-9a-f-]+$'),
                           MessageHandler(filters.TEXT & ~filters.COMMAND, _prompt_use_buttons)],
            PHONE:        [MessageHandler(filters.CONTACT, handle_phone)],
            PAYMENT_STEP: [],
            RECEIPT:      [MessageHandler(filters.PHOTO | filters.Document.ALL, handle_receipt),
                           MessageHandler(filters.TEXT & ~filters.COMMAND, _prompt_use_buttons)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True,
        name='registration',
        persistent=False,
        per_message=False,
    )
