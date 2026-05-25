# handlers/admin.py
import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

import db
import utils
from strings import t
from config import OWNER_ID, OWNER_IDS, GROUP_CHAT_ID
from handlers.registration import _send_main_menu_to

logger = logging.getLogger(__name__)

# State for deny flow (keyed by admin USER id, works in groups too)
_deny_pending:  dict[int, int]   = {}  # admin_user_id → target_chat_id
_deny_msg_info: dict[int, tuple] = {}  # admin_user_id → (chat_id, message_id)
# State for setschedule/setvenue
_setting_field: dict[int, str]   = {}  # admin_user_id → field name
# Nuke confirmation steps
_nuke_step: dict[int, int] = {}      # admin_chat_id → step (1 or 2)
_hold_pending:  dict[int, int]   = {}  # admin_user_id → target_chat_id
_hold_msg_info: dict[int, tuple] = {}  # admin_user_id → (chat_id, message_id)


def _require_admin(func):
    """Decorator: block non-admins from commands."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not utils.is_admin(update.effective_user.id):
            await update.message.reply_text(t('en', 'no_permission'))
            return
        return await func(update, context)
    return wrapper


def _require_owner(func):
    """Decorator: block non-owners from commands."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in OWNER_IDS:
            await update.message.reply_text(t('en', 'no_permission'))
            return
        return await func(update, context)
    return wrapper


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _send_housing_prompt_if_needed(bot, participant: dict, lang: str) -> None:
    """If participant needs housing and has no reservation yet, send house-selection buttons."""
    if not participant.get('needs_housing'):
        return
    existing = db.get_reservation(participant['id'])
    if existing:
        return  # already picked a house
    houses = db.get_houses_for_gender(participant.get('gender', 'M'))
    if not houses:
        return  # no houses configured yet
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    from utils import format_house_button
    buttons = []
    for house in houses:
        taken = db.get_house_occupancy(house['id'])
        label = format_house_button(house, taken, lang)
        buttons.append([InlineKeyboardButton(label, callback_data=f"house_{house['id']}")])
    await bot.send_message(
        participant['chat_id'],
        t(lang, 'housing_on_approval'),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown',
    )


# ─── Registration review ───────────────────────────────────────────────────────

@_require_admin
async def cmd_onhold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    held = db.get_participants_by_status('on_hold')
    if not held:
        await update.message.reply_text("⏸ No applications currently on hold.")
        return

    count = len(held)
    await update.message.reply_text(
        f"⏸ *{count} application{'s' if count != 1 else ''} on hold:*",
        parse_mode=ParseMode.MARKDOWN,
    )

    for p in held:
        cid       = p['chat_id']
        name      = p.get('full_name', '?')
        age       = p.get('age', '?')
        gender    = 'M' if p.get('gender') == 'M' else 'F'
        phone     = p.get('phone', '—')
        username  = p.get('username', '')
        uname_str = f"@{username}" if username else f"ID: {cid}"
        reason    = p.get('denial_reason', '—')
        caption = (
            f"⏸ *{name}* | {age}y | {gender}\n"
            f"📱 {uname_str} | ☎️ {phone}\n"
            f"🆔 `{cid}`\n\n"
            f"📝 Hold reason: {reason}"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{cid}"),
            InlineKeyboardButton("❌ Deny",    callback_data=f"admin_deny_{cid}"),
        ]])
        receipt = db.get_latest_receipt(p['id'])
        if receipt:
            try:
                await context.bot.send_photo(
                    update.effective_chat.id,
                    receipt['file_id'],
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard,
                )
            except Exception:
                await update.message.reply_text(
                    caption + "\n\n⚠️ _Receipt photo unavailable_",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard,
                )
        else:
            await update.message.reply_text(
                caption + "\n\n⚠️ _No receipt on file_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )


@_require_admin
async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending = db.get_participants_by_status('pending_approval')
    if not pending:
        await update.message.reply_text(t('en', 'admin_no_pending'))
        return

    count = len(pending)
    await update.message.reply_text(
        f"⏳ *{count} pending registration{'s' if count != 1 else ''}:*",
        parse_mode=ParseMode.MARKDOWN,
    )

    for p in pending:
        cid      = p['chat_id']
        name     = p.get('full_name', '?')
        age      = p.get('age', '?')
        gender   = 'M' if p.get('gender') == 'M' else 'F'
        phone    = p.get('phone', '—')
        username = p.get('username', '')
        uname_str = f"@{username}" if username else f"ID: {cid}"
        caption = (
            f"👤 *{name}* | {age}y | {gender}\n"
            f"📱 {uname_str} | ☎️ {phone}\n"
            f"🆔 `{cid}`"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{cid}"),
            InlineKeyboardButton("❌ Deny",    callback_data=f"admin_deny_{cid}"),
        ]])
        receipt = db.get_latest_receipt(p['id'])
        if receipt:
            await context.bot.send_photo(
                update.effective_chat.id,
                receipt['file_id'],
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )
        else:
            await update.message.reply_text(
                caption + "\n\n⚠️ _No receipt on file_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )


@_require_admin
async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /approve <chat_id>")
        return
    target_id = int(context.args[0])
    participant = db.get_participant(target_id)
    if not participant:
        await update.message.reply_text(t('en', 'admin_user_not_found'))
        return
    db.update_participant(target_id, {'status': 'approved'})
    db.confirm_reservation(participant['id'])
    lang = utils.get_lang(participant)
    try:
        await context.bot.send_message(target_id, t(lang, 'approved_welcome'), parse_mode=ParseMode.MARKDOWN)
        await _send_main_menu_to(context.bot, target_id, lang)
    except Exception:
        pass  # user may have blocked the bot; DB state already updated
    await update.message.reply_text(t('en', 'admin_approved', name=participant.get('full_name', str(target_id))))


@_require_admin
async def cmd_deny(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /deny <chat_id> <reason>")
        return
    target_id = int(context.args[0])
    reason = ' '.join(context.args[1:])
    participant = db.get_participant(target_id)
    if not participant:
        await update.message.reply_text(t('en', 'admin_user_not_found'))
        return
    db.update_participant(target_id, {'status': 'denied', 'denial_reason': reason})
    db.release_tentative_reservation(participant['id'])  # release tentative house reservation
    lang = utils.get_lang(participant)
    try:
        await context.bot.send_message(
            target_id,
            t(lang, 'denied_notification', reason=reason),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        pass  # user may have blocked the bot; DB state already updated
    await update.message.reply_text(t('en', 'admin_denied', name=participant.get('full_name', str(target_id))))


@_require_admin
async def cmd_viewreceipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /viewreceipt <chat_id>")
        return
    target_id = int(context.args[0])
    participant = db.get_participant(target_id)
    if not participant:
        await update.message.reply_text(t('en', 'admin_user_not_found'))
        return
    receipt = db.get_latest_receipt(participant['id'])
    if not receipt:
        await update.message.reply_text("No receipt found for this user.")
        return
    await context.bot.send_photo(update.effective_chat.id, receipt['file_id'],
                                  caption=f"Receipt for {participant.get('full_name', target_id)}")


async def cb_admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ Approve button on a registration notification."""
    query = update.callback_query
    admin_user_id = update.effective_user.id
    if not utils.is_admin(admin_user_id):
        await query.answer("No permission.", show_alert=True)
        return
    await query.answer()

    target_id   = int(query.data.split('_')[-1])
    participant = db.get_participant(target_id)
    if not participant:
        await query.answer("User not found.", show_alert=True)
        return
    if participant.get('status') == 'approved':
        await query.answer("Already approved.", show_alert=True)
        return

    db.update_participant(target_id, {'status': 'approved'})
    db.confirm_reservation(participant['id'])
    lang = utils.get_lang(participant)
    try:
        await context.bot.send_message(target_id, t(lang, 'approved_welcome'), parse_mode=ParseMode.MARKDOWN)
        await _send_main_menu_to(context.bot, target_id, lang)
    except Exception:
        pass  # user may have blocked the bot; DB state already updated

    admin_name = update.effective_user.first_name or "Admin"
    name = participant.get('full_name', str(target_id))
    try:
        await query.edit_message_caption(
            f"✅ *Approved* — {name}\n_by {admin_name}_",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        pass


async def cb_admin_deny_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """❌ Deny button — prompt admin for a reason."""
    query = update.callback_query
    admin_user_id = update.effective_user.id
    if not utils.is_admin(admin_user_id):
        await query.answer("No permission.", show_alert=True)
        return
    await query.answer()

    target_id   = int(query.data.split('_')[-1])
    participant = db.get_participant(target_id)
    if not participant:
        await query.answer("User not found.", show_alert=True)
        return
    if participant.get('status') == 'denied':
        await query.answer("Already denied.", show_alert=True)
        return

    _deny_pending[admin_user_id]  = target_id
    _deny_msg_info[admin_user_id] = (query.message.chat_id, query.message.message_id)
    # Persist to DB so state survives bot restarts/deploys
    db.set_setting(f'deny_pending_{admin_user_id}', str(target_id))
    db.set_setting(f'deny_msg_{admin_user_id}', f'{query.message.chat_id}:{query.message.message_id}')

    name = participant.get('full_name', str(target_id))
    try:
        await context.bot.send_message(
            query.message.chat_id,
            f"✏️ Type the denial reason for *{name}*:",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        pass


async def cb_admin_hold_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⏸ On Hold button — prompt admin for a reason."""
    query = update.callback_query
    admin_user_id = update.effective_user.id
    if not utils.is_admin(admin_user_id):
        await query.answer("No permission.", show_alert=True)
        return
    await query.answer()

    target_id   = int(query.data.split('_')[-1])
    participant = db.get_participant(target_id)
    if not participant:
        await query.answer("User not found.", show_alert=True)
        return
    if participant.get('status') == 'on_hold':
        await query.answer("Already on hold.", show_alert=True)
        return

    _hold_pending[admin_user_id]  = target_id
    _hold_msg_info[admin_user_id] = (query.message.chat_id, query.message.message_id)
    db.set_setting(f'hold_pending_{admin_user_id}', str(target_id))
    db.set_setting(f'hold_msg_{admin_user_id}', f'{query.message.chat_id}:{query.message.message_id}')

    name = participant.get('full_name', str(target_id))
    await context.bot.send_message(
        query.message.chat_id,
        t('en', 'admin_hold_prompt', name=name),
        parse_mode=ParseMode.MARKDOWN,
    )


@_require_admin
async def cmd_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_p = db.get_all_participants()
    if not all_p:
        await update.message.reply_text(t('en', 'admin_no_participants'))
        return
    lines = []
    for p in all_p:
        status = p.get('status', '')
        icon = {'approved': '✅', 'pending_approval': '⏳', 'pending_payment': '💳',
                'denied': '❌', 'incomplete': '🔘'}.get(status, '❓')
        name = p.get('full_name', '?')
        uname = f"@{p['username']}" if p.get('username') else f"ID:{p['chat_id']}"
        lines.append(f"{icon} {name} ({uname})")
    await update.message.reply_text('\n'.join(lines))


# ─── Housing management ────────────────────────────────────────────────────────

@_require_admin
async def cmd_listhouses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    houses = db.get_all_houses()
    if not houses:
        await update.message.reply_text("No houses configured.")
        return
    lines = []
    for h in houses:
        taken = db.get_house_occupancy(h['id'])
        gender_label = '♂️' if h['gender'] == 'M' else '♀️'
        lines.append(f"{gender_label} *{h['name']}* — {taken}/{h['capacity']}")
    await update.message.reply_text(
        t('en', 'admin_houses_list', list='\n'.join(lines)),
        parse_mode=ParseMode.MARKDOWN
    )


@_require_admin
async def cmd_moveresident(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /moveresident <chat_id> <house_name>
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /moveresident <chat_id> <house_name>")
        return
    target_id = int(context.args[0])
    house_name = ' '.join(context.args[1:])

    participant = db.get_participant(target_id)
    if not participant:
        await update.message.reply_text(t('en', 'admin_user_not_found'))
        return

    house = db.get_house_by_name(house_name)
    if not house:
        await update.message.reply_text(t('en', 'admin_house_not_found', name=house_name), parse_mode=ParseMode.MARKDOWN)
        return

    existing = db.get_reservation(participant['id'])
    if existing:
        db.move_reservation(participant['id'], house['id'])
    else:
        db.create_reservation(house['id'], participant['id'])

    name = participant.get('full_name', str(target_id))
    await update.message.reply_text(
        t('en', 'admin_resident_moved', user=name, house=house_name),
        parse_mode=ParseMode.MARKDOWN
    )


# ─── Bot management ────────────────────────────────────────────────────────────

@_require_admin
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    text = ' '.join(context.args)
    approved = db.get_participants_by_status('approved')
    count = 0
    for p in approved:
        try:
            await context.bot.send_message(p['chat_id'], text)
            count += 1
        except Exception:
            pass
    await update.message.reply_text(t('en', 'admin_broadcast_sent', count=count))


@_require_admin
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    counts = db.count_participants_by_status()
    housed = db.count_housed_participants()
    await update.message.reply_text(
        t('en', 'admin_status',
          total=counts['total'],
          approved=counts['approved'],
          pending=counts['pending'],
          denied=counts['denied'],
          housed=housed),
        parse_mode=ParseMode.MARKDOWN
    )


def _pause_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Housing",   callback_data='pause_housing'),
        InlineKeyboardButton("❓ Q&A",       callback_data='pause_qa'),
        InlineKeyboardButton("📨 Messages",  callback_data='pause_messages'),
    ]])


def _resume_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Housing",   callback_data='resume_housing'),
        InlineKeyboardButton("❓ Q&A",       callback_data='resume_qa'),
        InlineKeyboardButton("📨 Messages",  callback_data='resume_messages'),
    ]])


@_require_admin
async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏸ Select a feature to pause:", reply_markup=_pause_keyboard())


@_require_admin
async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("▶️ Select a feature to resume:", reply_markup=_resume_keyboard())


async def cb_pause_feature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not utils.is_admin(update.effective_user.id):
        await query.answer("No permission.", show_alert=True)
        return
    await query.answer()
    feature = query.data.replace('pause_', '')
    db.set_setting(f'{feature}_paused', 'true')
    labels = {'housing': '🏠 Housing', 'qa': '❓ Q&A', 'messages': '📨 Messages'}
    await query.edit_message_text(f"⏸ *{labels.get(feature, feature)}* is now paused.", parse_mode=ParseMode.MARKDOWN)


async def cb_resume_feature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not utils.is_admin(update.effective_user.id):
        await query.answer("No permission.", show_alert=True)
        return
    await query.answer()
    feature = query.data.replace('resume_', '')
    db.set_setting(f'{feature}_paused', 'false')
    labels = {'housing': '🏠 Housing', 'qa': '❓ Q&A', 'messages': '📨 Messages'}
    await query.edit_message_text(f"▶️ *{labels.get(feature, feature)}* is now active.", parse_mode=ParseMode.MARKDOWN)


@_require_admin
async def cmd_setschedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _setting_field[update.effective_user.id] = 'schedule'
    await update.message.reply_text(t('en', 'admin_set_prompt', field='schedule'))



async def handle_setting_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id

    # ── On Hold flow ──────────────────────────────────────────────────────────
    hold_target = _hold_pending.pop(admin_id, None)
    if hold_target is None:
        stored = db.get_setting(f'hold_pending_{admin_id}')
        if stored:
            hold_target = int(stored)

    if hold_target is not None:
        reason   = update.message.text
        msg_info = _hold_msg_info.pop(admin_id, None)
        if msg_info is None:
            stored_msg = db.get_setting(f'hold_msg_{admin_id}')
            if stored_msg and ':' in stored_msg:
                chat_part, msg_part = stored_msg.split(':', 1)
                msg_info = (int(chat_part), int(msg_part))

        # Clear pending state — best-effort, don't let a DB failure block the flow
        try:
            db.set_setting(f'hold_pending_{admin_id}', '')
            db.set_setting(f'hold_msg_{admin_id}', '')
        except Exception:
            logger.exception('Failed to clear hold_pending DB state for admin %s', admin_id)

        try:
            participant = db.get_participant(hold_target)
            if participant:
                # Guard: abort if user was already approved by another admin
                if participant.get('status') == 'approved':
                    await update.message.reply_text('⚠️ This user was approved — hold cancelled.')
                    return
                db.update_participant(hold_target, {'status': 'on_hold', 'denial_reason': reason})
                lang = utils.get_lang(participant)
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton(t(lang, 'btn_have_question'), callback_data='pre_approval_question')
                ]])
                try:
                    await context.bot.send_message(
                        hold_target,
                        t(lang, 'on_hold_notification', reason=reason),
                        reply_markup=keyboard,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception:
                    pass  # user may have blocked the bot; DB state already updated
                name = participant.get('full_name', str(hold_target))
                if msg_info:
                    try:
                        await context.bot.edit_message_caption(
                            chat_id=msg_info[0],
                            message_id=msg_info[1],
                            caption=f"⏸ *On Hold* — {name}\n_{reason}_",
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    except Exception:
                        pass
                await update.message.reply_text(t('en', 'admin_held', name=name))
        except Exception:
            logger.exception('Hold flow failed for target %s', hold_target)
            try:
                await update.message.reply_text('⚠️ Something went wrong applying the hold. Check logs and retry.')
            except Exception:
                pass
        return

    # ── Deny reason flow ─────────────────────────────────────────────────────
    target_id = _deny_pending.pop(admin_id, None)

    # Fall back to DB if memory was wiped by a restart/deploy
    if target_id is None:
        stored = db.get_setting(f'deny_pending_{admin_id}')
        if stored:
            target_id = int(stored)

    if target_id is not None:
        reason   = update.message.text
        msg_info = _deny_msg_info.pop(admin_id, None)

        # Fall back to DB for the notification message coordinates
        if msg_info is None:
            stored_msg = db.get_setting(f'deny_msg_{admin_id}')
            if stored_msg and ':' in stored_msg:
                chat_part, msg_part = stored_msg.split(':', 1)
                msg_info = (int(chat_part), int(msg_part))

        # Clear DB entries — best-effort, don't let a failure block the flow
        try:
            db.set_setting(f'deny_pending_{admin_id}', '')
            db.set_setting(f'deny_msg_{admin_id}', '')
        except Exception:
            logger.exception('Failed to clear deny_pending DB state for admin %s', admin_id)

        try:
            participant = db.get_participant(target_id)
            if participant:
                # Guard: abort if user was already approved by another admin
                if participant.get('status') == 'approved':
                    await update.message.reply_text('⚠️ This user was approved by another admin — deny cancelled.')
                    return
                db.update_participant(target_id, {'status': 'denied', 'denial_reason': reason})
                db.release_tentative_reservation(participant['id'])
                lang = utils.get_lang(participant)
                try:
                    await context.bot.send_message(
                        target_id,
                        t(lang, 'denied_notification', reason=reason),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception:
                    pass  # user may have blocked the bot; DB state already updated
                name = participant.get('full_name', str(target_id))
                if msg_info:
                    try:
                        await context.bot.edit_message_caption(
                            chat_id=msg_info[0],
                            message_id=msg_info[1],
                            caption=f"❌ *Denied* — {name}\nReason: {reason}",
                            parse_mode=ParseMode.MARKDOWN,
                        )
                    except Exception:
                        pass
                await update.message.reply_text(t('en', 'admin_denied', name=name))
        except Exception:
            logger.exception('Deny flow failed for target %s', target_id)
            try:
                await update.message.reply_text('⚠️ Something went wrong applying the denial. Check logs and retry.')
            except Exception:
                pass
        return

    # ── Schedule / venue setting flow ─────────────────────────────────────────
    field = _setting_field.pop(admin_id, None)
    if not field:
        return  # not in any admin flow
    text = update.message.text
    if field == 'schedule':
        db.set_setting('schedule_text', text)
        await update.message.reply_text(t('en', 'admin_schedule_set'))


@_require_owner
async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /addadmin <chat_id>")
        return
    new_id = int(context.args[0])
    existing = db.get_admin_ids_from_db()
    if new_id not in existing:
        existing.append(new_id)
        db.set_setting('admin_ids', ','.join(str(x) for x in existing))
    await update.message.reply_text(t('en', 'admin_added', chat_id=new_id))


@_require_owner
async def cmd_removeuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /removeuser <chat_id>")
        return
    target_id = int(context.args[0])
    db.delete_participant(target_id)
    await update.message.reply_text(t('en', 'admin_user_removed'))


@_require_admin
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_owner = update.effective_user.id in OWNER_IDS
    text = (
        "*Admin commands:*\n\n"
        "📋 *Registration*\n"
        "/pending — list pending registrations\n"
        "/onhold — list applications on hold\n"
        "/approve `<id>` — approve a user\n"
        "/deny `<id>` `<reason>` — deny a user\n"
        "/viewreceipt `<id>` — view a user's receipt\n"
        "/participants — list all participants\n\n"
        "🏠 *Housing*\n"
        "/listhouses — list all houses and occupancy\n"
        "/moveresident `<id>` `<house>` — move a user to a house\n\n"
        "📢 *Broadcast*\n"
        "/broadcast `<message>` — send message to all approved users\n\n"
        "⚙️ *Settings*\n"
        "/setschedule — set schedule text\n"
        "/pause — pause a feature\n"
        "/resume — resume a feature\n"
        "/status — show bot stats"
    )
    if is_owner:
        text += (
            "\n\n👑 *Owner only*\n"
            "/addadmin `<id>` — add an admin\n"
            "/removeuser `<id>` — delete a participant\n"
            "/testsetup — reset your own registration for testing"
        )
    await update.message.reply_text(text, parse_mode='Markdown')


@_require_owner
async def cmd_testsetup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete the caller's own participant record so they can re-test registration."""
    chat_id = update.effective_chat.id
    db.delete_participant(chat_id)
    await update.message.reply_text("🧪 Your participant record has been deleted. Send /start to re-register.")


@_require_owner
async def cmd_nuke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _nuke_step[update.effective_chat.id] = 1
    await update.message.reply_text(t('en', 'admin_nuke_confirm1'))


@_require_owner
async def cmd_nuke2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _nuke_step.get(update.effective_chat.id) != 1:
        return
    _nuke_step[update.effective_chat.id] = 2
    await update.message.reply_text(t('en', 'admin_nuke_confirm2'))


@_require_owner
async def cmd_nuke3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _nuke_step.get(update.effective_chat.id) != 2:
        return
    _nuke_step.pop(update.effective_chat.id, None)
    db.delete_all_participants()
    await update.message.reply_text(t('en', 'admin_nuked'))


def get_admin_handlers() -> list:
    return [
        CallbackQueryHandler(cb_admin_approve,    pattern='^admin_approve_'),
        CallbackQueryHandler(cb_admin_hold_start, pattern='^admin_hold_'),
        CallbackQueryHandler(cb_admin_deny_start, pattern='^admin_deny_'),
        CallbackQueryHandler(cb_pause_feature,    pattern='^pause_'),
        CallbackQueryHandler(cb_resume_feature,   pattern='^resume_'),
        CommandHandler('help',          cmd_help),
        CommandHandler('onhold',        cmd_onhold),
        CommandHandler('pending',       cmd_pending),
        CommandHandler('approve',       cmd_approve),
        CommandHandler('deny',          cmd_deny),
        CommandHandler('viewreceipt',   cmd_viewreceipt),
        CommandHandler('participants',  cmd_participants),
        CommandHandler('listhouses',    cmd_listhouses),
        CommandHandler('moveresident',  cmd_moveresident),
        CommandHandler('broadcast',     cmd_broadcast),
        CommandHandler('status',        cmd_status),
        CommandHandler('pause',         cmd_pause),
        CommandHandler('resume',        cmd_resume),
        CommandHandler('setschedule',   cmd_setschedule),
        CommandHandler('addadmin',      cmd_addadmin),
        CommandHandler('removeuser',    cmd_removeuser),
        CommandHandler('testsetup',     cmd_testsetup),
        CommandHandler('nuke',          cmd_nuke),
        CommandHandler('nuke2',         cmd_nuke2),
        CommandHandler('nuke3',         cmd_nuke3),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_setting_input),
    ]
