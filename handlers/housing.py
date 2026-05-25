# handlers/housing.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

import db
import utils
from strings import t


async def handle_housing_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    participant = db.get_participant(chat_id)
    lang = utils.get_lang(participant)

    if db.is_paused('housing'):
        await query.edit_message_text(t(lang, 'housing_paused'))
        return

    # Check if already reserved
    reservation = db.get_reservation(participant['id'])
    if reservation:
        house = reservation['houses']
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(t(lang, 'btn_cancel_reservation'), callback_data='housing_cancel')]
        ])
        await query.edit_message_text(
            t(lang, 'current_reservation', name=house['name']),
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, 'btn_housing_yes'), callback_data='housing_yes')],
        [InlineKeyboardButton(t(lang, 'btn_housing_no'), callback_data='housing_no')],
    ])
    await query.edit_message_text(t(lang, 'housing_prompt'), reply_markup=keyboard)


async def handle_housing_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    participant = db.get_participant(update.effective_chat.id)
    lang = utils.get_lang(participant)
    await query.edit_message_text(t(lang, 'no_housing_needed'))


async def handle_housing_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    participant = db.get_participant(chat_id)
    lang = utils.get_lang(participant)
    gender = participant.get('gender', 'M')

    houses = db.get_houses_for_gender(gender)
    if not houses:
        await query.edit_message_text(t(lang, 'no_houses_available'))
        return

    buttons = []
    for house in houses:
        taken = db.get_house_occupancy(house['id'])
        label = utils.format_house_button(house, taken, lang)
        buttons.append([InlineKeyboardButton(label, callback_data=f"house_{house['id']}")])

    await query.edit_message_text(
        t(lang, 'housing_list_header'),
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_house_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    participant = db.get_participant(chat_id)
    lang = utils.get_lang(participant)

    house_id = query.data.replace('house_', '')
    house = db.get_house_by_id(house_id)
    if not house:
        await query.edit_message_text(t(lang, 'error_generic'))
        return

    taken = db.get_house_occupancy(house_id)
    if taken >= house['capacity']:
        await query.edit_message_text(t(lang, 'house_full_msg'))
        return

    context.user_data['pending_house_id'] = house_id

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, 'btn_confirm_yes'), callback_data=f'houseconfirm_{house_id}')],
        [InlineKeyboardButton(t(lang, 'btn_confirm_no'), callback_data='menu_housing')],
    ])
    await query.edit_message_text(
        t(lang, 'house_confirm', name=house['name']),
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_house_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    participant = db.get_participant(chat_id)
    lang = utils.get_lang(participant)

    house_id = query.data.replace('houseconfirm_', '')
    house = db.get_house_by_id(house_id)

    # Double-check capacity (race condition guard)
    taken = db.get_house_occupancy(house_id)
    if taken >= house['capacity']:
        await query.edit_message_text(t(lang, 'house_full_msg'))
        return

    db.create_reservation(house_id, participant['id'])
    await query.edit_message_text(
        t(lang, 'house_reserved', name=house['name']),
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_cancel_reservation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    participant = db.get_participant(update.effective_chat.id)
    lang = utils.get_lang(participant)

    db.delete_reservation(participant['id'])
    await query.edit_message_text(t(lang, 'reservation_cancelled'))


def get_housing_handlers() -> list:
    return [
        CallbackQueryHandler(handle_housing_menu,      pattern='^menu_housing$'),
        CallbackQueryHandler(handle_housing_no,        pattern='^housing_no$'),
        CallbackQueryHandler(handle_housing_yes,       pattern='^housing_yes$'),
        CallbackQueryHandler(handle_house_select,      pattern='^house_[0-9a-f-]+$'),
        CallbackQueryHandler(handle_house_confirm,     pattern='^houseconfirm_[0-9a-f-]+$'),
        CallbackQueryHandler(handle_cancel_reservation,pattern='^housing_cancel$'),
    ]
