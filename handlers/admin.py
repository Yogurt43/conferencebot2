# handlers/admin.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

import db
import utils
from strings import t
from config import OWNER_ID, GROUP_CHAT_ID

# State for deny flow (keyed by admin USER id, works in groups too)
_deny_pending:  dict[int, int]   = {}  # admin_user_id → target_chat_id
_deny_msg_info: dict[int, tuple] = {}  # admin_user_id → (chat_id, message_id)
# State for setschedule/setvenue
_setting_field: dict[int, str]   = {}  # admin_user_id → field name
# Nuke confirmation steps
_nuke_step: dict[int, int] = {}      # admin_chat_id → step (1 or 2)
# Confirmremove pending
_remove_pending: dict[int, str] = {} # admin_chat_id → house_name


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
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text(t('en', 'no_permission'))
            return
        return await func(update, context)
    return wrapper


# ─── Registration review ───────────────────────────────────────────────────────

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
    lang = utils.get_lang(participant)
    await context.bot.send_message(target_id, t(lang, 'approved_welcome'), parse_mode=ParseMode.MARKDOWN)
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
    lang = utils.get_lang(participant)
    await context.bot.send_message(
        target_id,
        t(lang, 'denied_notification', reason=reason),
        parse_mode=ParseMode.MARKDOWN
    )
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
    lang = utils.get_lang(participant)
    await context.bot.send_message(target_id, t(lang, 'approved_welcome'), parse_mode=ParseMode.MARKDOWN)

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

    name = participant.get('full_name', str(target_id))
    await context.bot.send_message(
        query.message.chat_id,
        f"✏️ Type the denial reason for *{name}*:",
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
async def cmd_addhouse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /addhouse <name> <M|F> <capacity> [address]
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Usage: /addhouse <name> <M|F> <capacity> [address]")
        return
    name = args[0]
    gender = args[1].upper()
    if gender not in ('M', 'F'):
        await update.message.reply_text("Gender must be M or F.")
        return
    try:
        capacity = int(args[2])
    except ValueError:
        await update.message.reply_text("Capacity must be a number.")
        return
    address = ' '.join(args[3:]) if len(args) > 3 else ''

    if db.get_house_by_name(name):
        await update.message.reply_text(t('en', 'admin_house_exists', name=name), parse_mode=ParseMode.MARKDOWN)
        return

    db.add_house(name, gender, capacity, address)
    await update.message.reply_text(
        t('en', 'admin_house_added', name=name, gender=gender, capacity=capacity),
        parse_mode=ParseMode.MARKDOWN
    )


@_require_admin
async def cmd_removehouse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /removehouse <name>")
        return
    name = ' '.join(context.args)
    house = db.get_house_by_name(name)
    if not house:
        await update.message.reply_text(t('en', 'admin_house_not_found', name=name), parse_mode=ParseMode.MARKDOWN)
        return
    count = db.get_house_reservation_count(house['id'])
    if count > 0:
        _remove_pending[update.effective_chat.id] = name
        await update.message.reply_text(
            t('en', 'admin_house_occupied', name=name, count=count),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    db.remove_house(house['id'])
    await update.message.reply_text(t('en', 'admin_house_removed', name=name), parse_mode=ParseMode.MARKDOWN)


@_require_admin
async def cmd_confirmremove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_chat.id
    name = _remove_pending.pop(admin_id, None)
    if not name:
        await update.message.reply_text("No pending house removal.")
        return
    house = db.get_house_by_name(name)
    if house:
        db.remove_house(house['id'])
    await update.message.reply_text(t('en', 'admin_house_removed', name=name), parse_mode=ParseMode.MARKDOWN)


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
        lines.append(f"{gender_label} *{h['name']}* — {taken}/{h['capacity']} | {h.get('address', '—')}")
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


@_require_admin
async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /pause <housing|qa|messages>")
        return
    feature = context.args[0]
    db.set_setting(f'{feature}_paused', 'true')
    await update.message.reply_text(t('en', 'admin_feature_paused', feature=feature))


@_require_admin
async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /resume <housing|qa|messages>")
        return
    feature = context.args[0]
    db.set_setting(f'{feature}_paused', 'false')
    await update.message.reply_text(t('en', 'admin_feature_resumed', feature=feature))


@_require_admin
async def cmd_setschedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _setting_field[update.effective_user.id] = 'schedule'
    await update.message.reply_text(t('en', 'admin_set_prompt', field='schedule'))


@_require_admin
async def cmd_setvenue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _setting_field[update.effective_user.id] = 'venue'
    await update.message.reply_text(t('en', 'admin_set_prompt', field='venue'))


async def handle_setting_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id

    # ── Deny reason flow ─────────────────────────────────────────────────────
    target_id = _deny_pending.pop(admin_id, None)
    if target_id is not None:
        reason    = update.message.text
        msg_info  = _deny_msg_info.pop(admin_id, None)
        participant = db.get_participant(target_id)
        if participant:
            db.update_participant(target_id, {'status': 'denied', 'denial_reason': reason})
            lang = utils.get_lang(participant)
            await context.bot.send_message(
                target_id,
                t(lang, 'denied_notification', reason=reason),
                parse_mode=ParseMode.MARKDOWN,
            )
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
        return

    # ── Schedule / venue setting flow ─────────────────────────────────────────
    field = _setting_field.pop(admin_id, None)
    if not field:
        return  # not in any admin flow
    text = update.message.text
    if field == 'schedule':
        db.set_setting('schedule_text', text)
        await update.message.reply_text(t('en', 'admin_schedule_set'))
    elif field == 'venue':
        db.set_setting('venue_text', text)
        await update.message.reply_text(t('en', 'admin_venue_set'))


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
        CallbackQueryHandler(cb_admin_deny_start, pattern='^admin_deny_'),
        CommandHandler('pending',       cmd_pending),
        CommandHandler('approve',       cmd_approve),
        CommandHandler('deny',          cmd_deny),
        CommandHandler('viewreceipt',   cmd_viewreceipt),
        CommandHandler('participants',  cmd_participants),
        CommandHandler('addhouse',      cmd_addhouse),
        CommandHandler('removehouse',   cmd_removehouse),
        CommandHandler('confirmremove', cmd_confirmremove),
        CommandHandler('listhouses',    cmd_listhouses),
        CommandHandler('moveresident',  cmd_moveresident),
        CommandHandler('broadcast',     cmd_broadcast),
        CommandHandler('status',        cmd_status),
        CommandHandler('pause',         cmd_pause),
        CommandHandler('resume',        cmd_resume),
        CommandHandler('setschedule',   cmd_setschedule),
        CommandHandler('setvenue',      cmd_setvenue),
        CommandHandler('addadmin',      cmd_addadmin),
        CommandHandler('removeuser',    cmd_removeuser),
        CommandHandler('nuke',          cmd_nuke),
        CommandHandler('nuke2',         cmd_nuke2),
        CommandHandler('nuke3',         cmd_nuke3),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_setting_input),
    ]
