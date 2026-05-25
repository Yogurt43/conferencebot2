# Registration Flow Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate housing selection and pricing into registration, add an admin "On Hold" review action with improved contact info, and let pre-approval users ask questions.

**Architecture:** Changes flow through six files in dependency order: `config.py` → `strings.py` → `db.py` → `handlers/registration.py` → `handlers/admin.py` → `handlers/info.py`, with `bot.py` wiring last. Each task is independently testable.

**Tech Stack:** Python 3.11+, python-telegram-bot v20+, Supabase (Postgres), pytest + unittest.mock

---

## Task 1: Run DB Migrations in Supabase

**Files:**
- No code files changed — run SQL in the Supabase dashboard SQL editor

- [ ] **Step 1: Add `status` column to `house_reservations`**

Go to Supabase dashboard → SQL Editor and run:
```sql
ALTER TABLE house_reservations
  ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'confirmed';
```
Existing rows automatically get `status = 'confirmed'`. New tentative reservations will be inserted with `status = 'tentative'`.

- [ ] **Step 2: Add notification tracking columns to `participants`**

```sql
ALTER TABLE participants
  ADD COLUMN IF NOT EXISTS notify_chat_id BIGINT;
ALTER TABLE participants
  ADD COLUMN IF NOT EXISTS notify_msg_id  BIGINT;
```
These store where the original receipt notification was sent so re-submissions can be threaded as replies.

- [ ] **Step 3: Verify**

Run in SQL Editor:
```sql
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name IN ('house_reservations', 'participants')
  AND column_name IN ('status', 'notify_chat_id', 'notify_msg_id');
```
Expected: 3 rows returned.

---

## Task 2: Add Price Constants to `config.py`

**Files:**
- Modify: `config.py`
- Test: `tests/test_config.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_config.py`:
```python
# tests/test_config.py
import config

def test_price_constants_exist():
    assert hasattr(config, 'PRICE_WITH_HOUSING')
    assert hasattr(config, 'PRICE_WITHOUT_HOUSING')

def test_price_values():
    assert config.PRICE_WITH_HOUSING == 175
    assert config.PRICE_WITHOUT_HOUSING == 100

def test_prices_are_integers():
    assert isinstance(config.PRICE_WITH_HOUSING, int)
    assert isinstance(config.PRICE_WITHOUT_HOUSING, int)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/ludwig/Projects/weare-conference-bot
pytest tests/test_config.py -v
```
Expected: FAILED — `AttributeError: module 'config' has no attribute 'PRICE_WITH_HOUSING'`

- [ ] **Step 3: Add constants to `config.py`**

Add after the `PAYMENT_LINK` line:
```python
# ─── Registration pricing ──────────────────────────────────────────────────────
PRICE_WITH_HOUSING    = 175   # registration fee with conference housing
PRICE_WITHOUT_HOUSING = 100   # registration fee without housing
```

- [ ] **Step 4: Run tests to verify passing**

```bash
pytest tests/test_config.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add registration price constants to config"
```

---

## Task 3: Add New Strings to `strings.py`

**Files:**
- Modify: `strings.py`

> The existing `test_all_keys_in_both_languages` test in `tests/test_strings.py` automatically catches any key added to EN but missing from UK. Run it after each group of additions to catch mistakes early.

- [ ] **Step 1: Add new EN strings**

In `strings.py`, add the following to the `'en'` dict. Insert each group under its relevant comment section:

Under `# ── Registration ─────`:
```python
'welcome_message':      (
    f'👋 *Welcome to {CONF_NAME}!*\n\n'
    'We\'re happy you\'re here. To join the conference, please complete a short '
    'registration form and send us your payment receipt.\n\n'
    '*Registration fee:*\n'
    '🏠 With housing — {price_housing}\n'
    '🚗 Without housing (own arrangement) — {price_no_housing}\n\n'
    'After your receipt is reviewed and confirmed by our team, you\'ll get access '
    'to the schedule, venue info, and everything else you need.\n\n'
    'Let\'s get started! 👇'
),
'housing_pref_with_price': (
    '🏡 Do you need local housing for the conference?\n\n'
    '🏠 With housing — {price_housing}\n'
    '🚗 Without housing (own arrangement) — {price_no_housing}'
),
'house_selected_tentative': '🏠 Spot held at *{name}*. You can change this from the Housing menu once you\'re approved.',
'on_hold_notification': (
    '⏸ *Your registration is on hold.*\n\n'
    '{reason}\n\n'
    'Please re-upload your payment receipt when ready.'
),
'on_hold_resubmit': (
    '⏸ Your registration was put on hold.\n\n'
    '*Reason:* {reason}\n\n'
    'Please upload a new payment receipt to continue.'
),
```

Replace the existing `'payment_instructions'` key in EN with:
```python
'payment_instructions': (
    f'💳 *Payment*\n\n'
    f'Amount due: *{{amount}}*\n\n'
    f'Please complete your registration payment at the link below:\n\n'
    f'{{payment_link}}\n\n'
    f'Once you\'ve paid, come back and send your *payment receipt* (photo or screenshot).'
),
```

Under `# ── Coordinator messages ─────`:
```python
'btn_have_question':        '❓ Have a Question?',
'question_prompt_pre_approval': (
    '❓ Type your question and we\'ll pass it to the organizers.\n\n'
    '_To submit your payment, send a photo or screenshot above — not here._'
),
'question_sent_pre_approval': (
    '✅ Your question has been sent! The organizers will reach out to you directly.\n\n'
    'To submit your payment, send a photo or screenshot above 👆'
),
```

Under `# ── Admin ─────`:
```python
'admin_hold_prompt':    'Type a message for *{name}* — explain what needs fixing:',
'admin_held':           '⏸ {name} has been put on hold and notified.',
```

- [ ] **Step 2: Add matching UK strings**

Add the same keys to the `'uk'` dict:

Under `# ── Registration ─────`:
```python
'welcome_message':      (
    f'👋 *Ласкаво просимо до {CONF_NAME}!*\n\n'
    'Ми раді, що ви тут. Щоб приєднатися до конференції, будь ласка, заповніть коротку '
    'форму реєстрації та надішліть квитанцію про оплату.\n\n'
    '*Реєстраційний внесок:*\n'
    '🏠 З проживанням — {price_housing}\n'
    '🚗 Без проживання (власні умови) — {price_no_housing}\n\n'
    'Після того як наша команда перевірить та підтвердить вашу квитанцію, '
    'ви отримаєте доступ до розкладу, інформації про місце та всього іншого.\n\n'
    'Починаємо! 👇'
),
'housing_pref_with_price': (
    '🏡 Чи потребуєте ви місцевого проживання під час конференції?\n\n'
    '🏠 З проживанням — {price_housing}\n'
    '🚗 Без проживання (власні умови) — {price_no_housing}'
),
'house_selected_tentative': '🏠 Місце заброньоване в *{name}*. Ви можете змінити це через меню Житло після схвалення.',
'on_hold_notification': (
    '⏸ *Вашу реєстрацію призупинено.*\n\n'
    '{reason}\n\n'
    'Будь ласка, повторно завантажте квитанцію про оплату, коли будете готові.'
),
'on_hold_resubmit': (
    '⏸ Вашу реєстрацію було призупинено.\n\n'
    '*Причина:* {reason}\n\n'
    'Будь ласка, завантажте нову квитанцію про оплату для продовження.'
),
```

Replace the existing `'payment_instructions'` key in UK with:
```python
'payment_instructions': (
    f'💳 *Оплата*\n\n'
    f'Сума до сплати: *{{amount}}*\n\n'
    f'Будь ласка, здійсніть оплату за посиланням нижче:\n\n'
    f'{{payment_link}}\n\n'
    f'Після оплати поверніться сюди та надішліть *квитанцію про оплату* (фото або скриншот).'
),
```

Under `# ── Coordinator messages ─────`:
```python
'btn_have_question':        '❓ Маєте питання?',
'question_prompt_pre_approval': (
    '❓ Введіть ваше питання і ми передамо його організаторам.\n\n'
    '_Щоб надіслати оплату, надішліть фото або скриншот вище — не тут._'
),
'question_sent_pre_approval': (
    '✅ Ваше питання надіслано! Організатори зв\'яжуться з вами напряму.\n\n'
    'Щоб надіслати оплату, надішліть фото або скриншот вище 👆'
),
```

Under `# ── Admin ─────`:
```python
'admin_hold_prompt':    'Напишіть повідомлення для *{name}* — поясніть що потрібно виправити:',
'admin_held':           '⏸ {name} призупинено та повідомлено.',
```

- [ ] **Step 3: Run string tests**

```bash
pytest tests/test_strings.py -v
```
Expected: all PASSED — specifically `test_all_keys_in_both_languages` validates EN/UK parity.

- [ ] **Step 4: Commit**

```bash
git add strings.py
git commit -m "feat: add strings for welcome message, housing pricing, on-hold, and pre-approval questions"
```

---

## Task 4: Add New DB Functions

**Files:**
- Modify: `db.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: Write failing tests**

Add to the end of `tests/test_db.py`:
```python
def test_create_tentative_reservation(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value.data = [
        {'id': 'res-1', 'house_id': 'h1', 'participant_id': 'p1', 'status': 'tentative'}
    ]
    result = db.create_tentative_reservation('h1', 'p1')
    assert result['status'] == 'tentative'
    # Verify the insert was called with status='tentative'
    call_args = mock_sb.table.return_value.insert.call_args[0][0]
    assert call_args['status'] == 'tentative'
    assert call_args['house_id'] == 'h1'
    assert call_args['participant_id'] == 'p1'

def test_confirm_reservation(mock_sb):
    mock_sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    db.confirm_reservation('p1')
    update_call = mock_sb.table.return_value.update.call_args[0][0]
    assert update_call == {'status': 'confirmed'}

def test_release_tentative_reservation(mock_sb):
    mock_sb.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    db.release_tentative_reservation('p1')
    # Verify delete was called (not update)
    mock_sb.table.return_value.delete.assert_called_once()
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_db.py::test_create_tentative_reservation tests/test_db.py::test_confirm_reservation tests/test_db.py::test_release_tentative_reservation -v
```
Expected: FAILED — `AttributeError: module 'db' has no attribute 'create_tentative_reservation'`

- [ ] **Step 3: Add functions to `db.py`**

Add after `create_reservation` (around line 117):
```python
def create_tentative_reservation(house_id: str, participant_id: str) -> dict:
    """Create a tentative reservation during registration. Confirmed on approval."""
    res = sb.table('house_reservations').insert({
        'house_id': house_id,
        'participant_id': participant_id,
        'status': 'tentative',
    }).execute()
    return res.data[0] if res.data else {}

def confirm_reservation(participant_id: str) -> None:
    """Upgrade a tentative reservation to confirmed on participant approval."""
    sb.table('house_reservations').update({'status': 'confirmed'}).eq(
        'participant_id', participant_id
    ).eq('status', 'tentative').execute()

def release_tentative_reservation(participant_id: str) -> None:
    """Delete any tentative reservation for a participant (on denial or re-entry)."""
    sb.table('house_reservations').delete().eq(
        'participant_id', participant_id
    ).eq('status', 'tentative').execute()
```

Note: `get_house_occupancy` already counts all rows regardless of status — no change needed. Both tentative and confirmed spots count toward capacity to prevent double-booking.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_db.py -v
```
Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: add tentative reservation DB functions"
```

---

## Task 5: Registration — Welcome Message + HOUSE_SELECT State

**Files:**
- Modify: `handlers/registration.py`

- [ ] **Step 1: Update state constants and imports**

At the top of `handlers/registration.py`, replace:
```python
LANG, NAME, AGE, GENDER, HOUSING_PREF, PHONE, PAYMENT_STEP, RECEIPT = range(8)
```
With:
```python
LANG, NAME, AGE, GENDER, HOUSING_PREF, HOUSE_SELECT, PHONE, PAYMENT_STEP, RECEIPT = range(9)
```

Add to imports at the top:
```python
from config import PAYMENT_LINK, GROUP_CHAT_ID, OWNER_ID, PRICE_WITH_HOUSING, PRICE_WITHOUT_HOUSING
```

- [ ] **Step 2: Add welcome message to `start()` for new users**

In `start()`, find the block at the bottom that handles new users:
```python
    # New user — start language selection
    await update.message.reply_text(
        t('en', 'choose_lang'),
        reply_markup=_lang_keyboard()
    )
    return LANG
```

Replace with:
```python
    # New user — welcome message first, then language selection
    await update.message.reply_text(
        t('en', 'welcome_message',
          price_housing=PRICE_WITH_HOUSING,
          price_no_housing=PRICE_WITHOUT_HOUSING),
        parse_mode=ParseMode.MARKDOWN
    )
    await update.message.reply_text(
        t('en', 'choose_lang'),
        reply_markup=_lang_keyboard()
    )
    return LANG
```

- [ ] **Step 3: Add `_send_main_menu_to` helper**

After `_show_main_menu`, add:
```python
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
```

Update `_show_main_menu` to delegate to it (avoids duplicating the keyboard layout):
```python
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
```
(Keep as-is — `_send_main_menu_to` is the new version for bot-only calls.)

- [ ] **Step 4: Update `handle_housing_pref` to branch into HOUSE_SELECT**

Replace the entire `handle_housing_pref` function:
```python
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
            + f"\n\n✅ {t(lang, 'btn_housing_yes')}",
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
            + f"\n\n✅ {t(lang, 'btn_housing_no')}",
            parse_mode=ParseMode.MARKDOWN,
        )
        await query.message.reply_text(
            t(lang, 'share_phone'),
            reply_markup=_phone_keyboard(lang),
        )
        return PHONE
```

- [ ] **Step 5: Add `handle_house_select_reg` handler**

Add after `handle_housing_pref`:
```python
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
```

- [ ] **Step 6: Register HOUSE_SELECT state in `build_registration_handler`**

In `build_registration_handler`, add `HOUSE_SELECT` to the `states` dict:
```python
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
    RECEIPT:      [MessageHandler(filters.PHOTO | filters.Document.ALL, handle_receipt)],
},
```

- [ ] **Step 7: Commit**

```bash
git add handlers/registration.py
git commit -m "feat: add welcome message and HOUSE_SELECT state to registration flow"
```

---

## Task 6: Registration — Payment Amount, Receipt Button, On Hold Re-entry

**Files:**
- Modify: `handlers/registration.py`

- [ ] **Step 1: Update `handle_housing_pref` housing prompt to include price**

Also update the housing question sent from `handle_gender`. Find:
```python
    await query.edit_message_text(t(lang, 'choose_gender') + " ✅")
    await query.message.reply_text(
        t(lang, 'housing_prompt'),
        reply_markup=_housing_keyboard(lang),
    )
    return HOUSING_PREF
```
Replace with:
```python
    await query.edit_message_text(t(lang, 'choose_gender') + " ✅")
    await query.message.reply_text(
        t(lang, 'housing_pref_with_price',
          price_housing=PRICE_WITH_HOUSING,
          price_no_housing=PRICE_WITHOUT_HOUSING),
        reply_markup=_housing_keyboard(lang),
        parse_mode=ParseMode.MARKDOWN,
    )
    return HOUSING_PREF
```

- [ ] **Step 2: Update `handle_phone` to pass amount to payment instructions**

Replace the body of `handle_phone` after the contact check:
```python
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
```

- [ ] **Step 3: Update `handle_receipt` to save notify info and thread re-submissions**

Replace everything in `handle_receipt` after the `file_id` extraction block (i.e. from `participant = db.get_participant(chat_id)` to `return ConversationHandler.END`) with the following. This replaces both the early `db.save_receipt` / `db.update_participant` calls and the notification block — do not leave the old status-update line in place:
```python
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
    housing_str = '🏠 Needs housing' if housing_raw else '🏡 Has own housing'

    # Clickable contact: @username deep-link, or phone + tg://user fallback
    if username:
        contact_str = f"[@{username}](https://t.me/{username})"
    else:
        contact_str = f"☎️ {phone_val} · [Open chat](tg://user?id={chat_id})"

    is_resubmit = participant.get('status') == 'on_hold'

    if is_resubmit:
        caption = (
            f"🔄 *Re-submission* — {name}\n"
            f"Updated receipt after on-hold\n\n"
            f"👤 *{name}* | {age}y | {gender}\n"
            f"{contact_str}\n"
            f"{housing_str}\n"
            f"🆔 `{chat_id}`"
        )
    else:
        caption = (
            f"📥 *New registration pending review*\n\n"
            f"👤 *{name}* | {age}y | {gender}\n"
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

    result = await context.bot.send_photo(
        notify_chat_id,
        file_id,
        caption=caption,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
        reply_to_message_id=reply_to,
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
```

- [ ] **Step 4: Add `on_hold` re-entry to `start()`**

In `start()`, add the `on_hold` case after the `denied` block (before the new-user block at the bottom):
```python
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
```

- [ ] **Step 5: Update `denied` re-entry to re-show house selection if reservation was released**

Replace the existing `denied` block in `start()`:
```python
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
```

- [ ] **Step 6: Export `_send_main_menu_to` and `HOUSE_SELECT` from the module**

At the bottom of `handlers/registration.py`, update the `build_registration_handler` import in `bot.py` will also need `_send_main_menu_to`. Make sure it's accessible — since Python modules expose all top-level names, no extra export needed.

- [ ] **Step 7: Commit**

```bash
git add handlers/registration.py
git commit -m "feat: add payment amount, receipt question button, on-hold re-entry"
```

---

## Task 7: Admin — Three-Button Notification + Contact Info + Remove Housing Prompt

**Files:**
- Modify: `handlers/admin.py`

- [ ] **Step 1: Add import for `_send_main_menu_to`**

At the top of `handlers/admin.py`, add:
```python
from handlers.registration import _send_main_menu_to
```

- [ ] **Step 2: Add `_hold_pending` and `_hold_msg_info` state dicts**

After the existing `_deny_pending` / `_deny_msg_info` lines:
```python
_hold_pending:  dict[int, int]   = {}  # admin_user_id → target_chat_id
_hold_msg_info: dict[int, tuple] = {}  # admin_user_id → (chat_id, message_id)
```

- [ ] **Step 3: Update `cb_admin_approve` — confirm reservation, send main menu, remove housing prompt**

Replace `cb_admin_approve`:
```python
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
    await context.bot.send_message(target_id, t(lang, 'approved_welcome'), parse_mode=ParseMode.MARKDOWN)
    await _send_main_menu_to(context.bot, target_id, lang)

    admin_name = update.effective_user.first_name or "Admin"
    name = participant.get('full_name', str(target_id))
    try:
        await query.edit_message_caption(
            f"✅ *Approved* — {name}\n_by {admin_name}_",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        pass
```

- [ ] **Step 4: Update `cmd_approve` — same changes**

Replace `cmd_approve`:
```python
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
    await context.bot.send_message(target_id, t(lang, 'approved_welcome'), parse_mode=ParseMode.MARKDOWN)
    await _send_main_menu_to(context.bot, target_id, lang)
    await update.message.reply_text(t('en', 'admin_approved', name=participant.get('full_name', str(target_id))))
```

- [ ] **Step 5: Commit**

```bash
git add handlers/admin.py
git commit -m "feat: admin approve confirms reservation and sends main menu"
```

---

## Task 8: Admin — On Hold Flow + Release Reservation on Deny

**Files:**
- Modify: `handlers/admin.py`
- Modify: `bot.py`

- [ ] **Step 1: Add `cb_admin_hold_start` handler**

Add after `cb_admin_deny_start`:
```python
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
```

- [ ] **Step 2: Add hold flow to `handle_setting_input`**

In `handle_setting_input`, add the hold check BEFORE the deny check. Find the block that starts `target_id = _deny_pending.pop(admin_id, None)` and insert before it:

```python
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

        db.set_setting(f'hold_pending_{admin_id}', '')
        db.set_setting(f'hold_msg_{admin_id}', '')

        participant = db.get_participant(hold_target)
        if participant:
            db.update_participant(hold_target, {'status': 'on_hold', 'denial_reason': reason})
            lang = utils.get_lang(participant)
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang, 'btn_have_question'), callback_data='pre_approval_question')
            ]])
            await context.bot.send_message(
                hold_target,
                t(lang, 'on_hold_notification', reason=reason),
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
            )
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
        return
```

- [ ] **Step 3: Add `release_tentative_reservation` to the deny flow in `handle_setting_input` AND `cmd_deny`**

In `handle_setting_input`, deny branch, find:
```python
        if participant:
            db.update_participant(target_id, {'status': 'denied', 'denial_reason': reason})
```
Replace with:
```python
        if participant:
            db.update_participant(target_id, {'status': 'denied', 'denial_reason': reason})
            db.release_tentative_reservation(participant['id'])
```

Also in `cmd_deny`, find the `db.update_participant` line that sets `status: denied` and add the release call immediately after:
```python
    db.update_participant(target_id, {'status': 'denied', 'denial_reason': ' '.join(context.args[1:])})
    db.release_tentative_reservation(participant['id'])  # release tentative house reservation
```

- [ ] **Step 4: Register `cb_admin_hold_start` in `get_admin_handlers`**

Find `get_admin_handlers` and add the hold callback:
```python
def get_admin_handlers() -> list:
    return [
        CallbackQueryHandler(cb_admin_approve,    pattern='^admin_approve_'),
        CallbackQueryHandler(cb_admin_hold_start, pattern='^admin_hold_'),
        CallbackQueryHandler(cb_admin_deny_start, pattern='^admin_deny_'),
        # ... rest of existing handlers unchanged
    ]
```

- [ ] **Step 5: Commit**

```bash
git add handlers/admin.py
git commit -m "feat: add on-hold admin flow and release reservation on denial"
```

---

## Task 9: Info Handler — Pre-Approval Question Flow

**Files:**
- Modify: `handlers/info.py`
- Modify: `bot.py`

- [ ] **Step 1: Add import for price constants**

At the top of `handlers/info.py`:
```python
from config import QA_RATE_LIMIT, GROUP_CHAT_ID, PRICE_WITH_HOUSING, PRICE_WITHOUT_HOUSING
```

- [ ] **Step 2: Add `handle_coordinator_pre_approval` callback handler**

Add after `handle_coordinator_start`:
```python
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
```

- [ ] **Step 3: Update `handle_text_input` to send enhanced notification for pre-approval users**

Replace the `if chat_id in _awaiting_msg:` block:
```python
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

            if target:
                await context.bot.send_message(
                    target,
                    f"📨 *Message from pending registrant*\n\n"
                    f"👤 *{name}* · status: {status_str}\n"
                    f"💳 Amount due: *{amount}* ({housing_label})\n"
                    f"{contact_line}\n\n"
                    f"_{text}_",
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
                await context.bot.send_message(
                    target,
                    f"📨 *Message from {name}*\n\n{text}",
                    parse_mode=ParseMode.MARKDOWN,
                )
        return
```

- [ ] **Step 4: Add `handle_coordinator_pre_approval` to `get_info_handlers`**

```python
def get_info_handlers() -> list:
    return [
        CallbackQueryHandler(handle_schedule,                pattern='^menu_schedule$'),
        CallbackQueryHandler(handle_venue,                   pattern='^menu_venue$'),
        CallbackQueryHandler(handle_qa_start,                pattern='^menu_qa$'),
        CallbackQueryHandler(handle_coordinator_start,       pattern='^menu_coordinator$'),
        CallbackQueryHandler(handle_coordinator_pre_approval, pattern='^pre_approval_question$'),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input),
    ]
```

- [ ] **Step 5: Commit**

```bash
git add handlers/info.py
git commit -m "feat: add pre-approval question flow with enhanced organizer notification"
```

---

## Task 10: Wire Everything in `bot.py` + Smoke Test

**Files:**
- Modify: `bot.py`

- [ ] **Step 1: Verify imports in `bot.py` are still correct**

The `bot.py` already imports `menu_command` from `handlers/registration`. No changes needed there — the new `_send_main_menu_to` and `HOUSE_SELECT` are used internally by the handlers themselves.

The new `admin_hold_*` callback is registered inside `get_admin_handlers()` (done in Task 8). The `pre_approval_question` callback is registered inside `get_info_handlers()` (done in Task 9). So `bot.py` needs no changes.

- [ ] **Step 2: Run the full test suite**

```bash
cd /Users/ludwig/Projects/weare-conference-bot
pytest tests/ -v
```
Expected: all tests PASS. Any failures in `test_strings.py::test_all_keys_in_both_languages` mean a UK translation is missing — fix it in `strings.py` before continuing.

- [ ] **Step 3: Smoke test — push to Render and run manual checks**

Push to GitHub to trigger a Render deploy (or use Manual Deploy if webhook is flaky):
```bash
git push origin main
```

Manual checks to run in the bot:
1. **New user `/start`** → should see welcome message with prices, then language buttons
2. **Register with housing=Yes** → should see house list after gender selection, pick a house
3. **Register with housing=No** → should skip house list, go straight to phone
4. **Submit receipt** → admin group should see 3 buttons (Approve / On Hold / Deny) and a clickable `@username` or `Open chat` link
5. **Admin clicks ⏸ On Hold** → type a reason → user should receive on-hold message with ❓ button
6. **User clicks ❓ Have a Question?** (from receipt step) → type a question → organizer channel should show name + amount due + contact link
7. **Admin approves a user** → user should receive welcome message + main menu immediately (no housing prompt)
8. **Admin denies a user** → user re-registers → if they had housing=Yes, should see house list again

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "chore: verify full integration — registration redesign complete"
```

---

## Quick Reference — New Callback Data Strings

| Callback data | Handler | Where registered |
|---|---|---|
| `reg_house_{uuid}` | `handle_house_select_reg` | ConversationHandler HOUSE_SELECT state |
| `admin_hold_{chat_id}` | `cb_admin_hold_start` | `get_admin_handlers()` |
| `pre_approval_question` | `handle_coordinator_pre_approval` | `get_info_handlers()` |

## Quick Reference — New DB Functions

| Function | Purpose |
|---|---|
| `db.create_tentative_reservation(house_id, participant_id)` | Creates reservation with `status='tentative'` |
| `db.confirm_reservation(participant_id)` | Upgrades tentative → confirmed on approval |
| `db.release_tentative_reservation(participant_id)` | Deletes tentative reservation on denial |

## Quick Reference — New Participant Statuses

| Status | Meaning | Re-entry via `/start` |
|---|---|---|
| `on_hold` | Admin flagged for correction | Shows hold reason + receipt upload + ❓ button |
