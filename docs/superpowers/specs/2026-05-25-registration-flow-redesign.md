# Registration Flow Redesign — Design Spec
_Date: 2026-05-25_

## Overview

Three coordinated improvements to the registration and admin review experience:

1. **Welcome message + housing integrated into registration** — users see pricing upfront, pick their house during registration, and see the correct payment amount before submitting
2. **Admin "On Hold" button + contact info** — third review action for wrong-payment cases, with direct Telegram contact links
3. **"Message Organizers" during receipt step** — users waiting to submit payment can reach organizers without being approved yet

---

## 1. Welcome Message

A new introductory message is sent before language selection when a new user opens the bot (`/start`). Content:

> 👋 **Welcome to WeAre Conference!**
>
> We're happy you're here. To join the conference, please complete a short registration form and send us your payment receipt.
>
> **Registration fee:**
> 🏠 With housing — 175
> 🚗 Without housing (own arrangement) — 100
>
> After your receipt is reviewed and confirmed by our team, you'll get access to the schedule, venue info, and everything else you need.
>
> Let's get started! 👇

This message is sent once, before the language selection buttons appear. It is only shown to new users (no existing participant record).

Both language variants are needed in `strings.py`. The prices (175, 100) are added as `PRICE_WITH_HOUSING = 175` and `PRICE_WITHOUT_HOUSING = 100` constants in `config.py` so they can be changed in one place.

---

## 2. Registration Flow Changes

### Updated state sequence

```
LANG → NAME → AGE → GENDER → HOUSING_PREF → [HOUSE_SELECT if yes] → PHONE → PAYMENT_STEP → RECEIPT → END
```

New state: `HOUSE_SELECT` (integer constant). The `range(8)` at the top of `registration.py` becomes `range(9)` with `HOUSE_SELECT` inserted after `HOUSING_PREF`.

### HOUSING_PREF step
- Prompt now includes the price difference: "🏠 With housing (175) · 🚗 Without (100)"
- "Yes" → proceeds to `HOUSE_SELECT`
- "No" → proceeds to `PHONE` (unchanged)

### HOUSE_SELECT step (new)
- Shows the house list filtered by the gender already recorded in this session
- Same rendering as the existing `_show_house_list` helper in `housing.py`
- User picks a house → **tentative reservation** is created in `house_reservations` with `status = 'tentative'`
- Confirmation message: "🏠 Spot held at *{name}*. You can change this later."
- Proceeds to `PHONE`

### PAYMENT_STEP / payment instructions
- `payment_instructions` string gains an `{amount}` placeholder
- `handle_phone` looks up `needs_housing` from `context.user_data` (set in `HOUSING_PREF`) and passes `amount=175` or `amount=100`

### Approval — what changes
- `cb_admin_approve` and `cmd_approve`: remove the call to `_send_housing_prompt_if_needed`
- On approval: confirm the tentative reservation (`UPDATE house_reservations SET status = 'confirmed' WHERE participant_id = ? AND status = 'tentative'`)
- Send `approved_welcome` message (unchanged text)
- Send the main menu immediately after (call a new `_send_main_menu_to(bot, chat_id, lang)` helper)

### Denial — what changes
- On denial: release any tentative reservation (`DELETE FROM house_reservations WHERE participant_id = ? AND status = 'tentative'`)

### Edge cases
- User re-enters after denial: if they go through `HOUSE_SELECT` again and a tentative reservation already exists for them, delete it first then create a new one
- Capacity check at `HOUSE_SELECT` counts all reservations (tentative + confirmed) to prevent double-booking

---

## 3. DB Schema Changes

### `house_reservations` table
Add a `status` column:
```sql
ALTER TABLE house_reservations ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'confirmed';
```
Existing rows stay as `'confirmed'`. New tentative rows use `'tentative'`.

### `participants` table
Add columns to track the original admin notification message (needed for re-submission threading):
```sql
ALTER TABLE participants ADD COLUMN IF NOT EXISTS notify_chat_id BIGINT;
ALTER TABLE participants ADD COLUMN IF NOT EXISTS notify_msg_id  BIGINT;
```

These are written when the receipt notification is sent to the admin group, and read when a re-submission arrives (to reply to the original thread).

---

## 4. Admin "On Hold" Button

### New participant status: `on_hold`

Added alongside `pending_payment`, `pending_approval`, `approved`, `denied`.

### Admin notification — updated buttons
Three-button layout on every receipt notification:
```
[ ✅ Approve ]  [ ⏸ On Hold ]  [ ❌ Deny ]
```
Callback data: `admin_approve_{chat_id}`, `admin_hold_{chat_id}`, `admin_deny_{chat_id}`.

### On Hold flow (mirrors existing deny flow)
1. Admin clicks ⏸ On Hold
2. Bot prompts in the group: *"Type a message for {name} — explain what needs fixing:"*
3. Admin types reason
4. User receives: *"⏸ Your registration is on hold.\n\n{reason}\n\nPlease re-upload your payment receipt when ready."*
5. Caption updates to: `⏸ On Hold — {name}\n_{reason}_`
6. Participant status → `on_hold`

State management: uses the same `_deny_pending` / `_deny_msg_info` pattern, with parallel `_hold_pending` / `_hold_msg_info` dicts (and DB keys `hold_pending_{admin_id}`, `hold_msg_{admin_id}`). `handle_setting_input` checks `_hold_pending` before `_deny_pending` and before the schedule/venue field check — same priority ordering as deny.

### Re-submission after on_hold
- `start()` re-entry logic: `on_hold` status → send `on_hold_resubmit` string (shows stored `denial_reason` field, reused for hold reason) + prompt to re-upload → enter `RECEIPT` state
- `handle_receipt`: when current status is `on_hold`, send the new receipt notification as a **reply** to `notify_msg_id` stored on the participant
- Re-submission caption: `🔄 Re-submission — {name}\nUpdated receipt after on-hold`
- All three buttons appear again on the re-submission notification

### Contact info in caption
Current format uses `@username` or `ID: {chat_id}`. Updated:
- With username: `[@username](https://t.me/username)` — clickable in Telegram captions
- Without username: `☎️ {phone} · [Open chat](tg://user?id={chat_id})` — deep link works without a public username

---

## 5. "Message Organizers" During Receipt Step

### Where it appears
- On the `upload_receipt` message — as an inline button: **❓ Have a Question?**
- On the on-hold message sent to the user — same button

### Flow
1. User clicks "❓ Have a Question?"
2. A **new message** is sent (does not replace or edit the receipt prompt): *"❓ Type your question and we'll pass it to the organizers.\n\nTo submit your payment, send a photo or screenshot above — not here."*
3. Chat ID added to `_awaiting_msg` (existing set in `info.py`)
4. User types message → caught by `handle_text_input` (falls through RECEIPT ConversationHandler state since only photo/doc are handled there)
5. Bot confirms: *"✅ Your question has been sent! The organizers will reach out to you directly. To submit your payment, send a photo or screenshot above 👆"*
6. Organizer channel receives:

```
📨 Message from pending registrant

👤 {name} · status: ⏳ Pending payment
💳 Amount due: 175 (with housing)           ← or 100 (no housing)
[@username](https://t.me/username)          ← if username exists
☎️ {phone} · [Open chat](tg://user?id=...)  ← if no username

"{message text}"
```

`needs_housing` is already on the participant record; the handler looks it up and picks `PRICE_WITH_HOUSING` or `PRICE_WITHOUT_HOUSING` from `config.py` to format the amount line.

### Technical note
The `handle_coordinator_start` callback currently calls `query.edit_message_text`. A new variant is needed for the pre-approval context that sends a **new message** instead of editing. The coordinator channel notification is enhanced with name, status, and contact link.

---

## What does NOT change
- Post-approval housing selection via `/menu` → Housing still works as a fallback (users reassigned by admin, edge cases)
- `handle_cancel_reservation` — users can still cancel and re-pick from the main menu
- Q&A rate limiting, pause/resume admin controls
- All existing callback data strings — no renames, no collision risk

---

## Files affected
- `strings.py` — new keys: `welcome_message`, `housing_pref_with_price`, `house_selected_tentative`, `payment_instructions` (add `{amount}`), `on_hold_notification`, `on_hold_resubmit`, `btn_have_question`, `question_prompt_pre_approval`, `question_sent_pre_approval`, new UK translations for all
- `config.py` — add `PRICE_WITH_HOUSING = 175` and `PRICE_WITHOUT_HOUSING = 100`
- `handlers/registration.py` — welcome message in `start()`, new `HOUSE_SELECT` state and handler, update `handle_housing_pref`, `handle_phone` (amount), re-entry for `on_hold`, `upload_receipt` button, new `_send_main_menu_to(bot, chat_id, lang)` helper (async, takes bot + chat_id instead of Update so it can be called from admin.py)
- `handlers/admin.py` — three-button notification, `cb_admin_hold_start`, `_hold_pending`/`_hold_msg_info` state, updated `handle_setting_input`, release reservation on denial, confirm reservation on approval, send main menu on approval
- `handlers/housing.py` — `create_tentative_reservation` path (or new `db` function)
- `handlers/info.py` — enhanced coordinator notification (name, status, contact link), new `handle_coordinator_pre_approval` callback
- `db.py` — `create_tentative_reservation(house_id, participant_id)`, `confirm_reservation(participant_id)`, `release_tentative_reservation(participant_id)`, updated `get_house_occupancy` (count all statuses), store/read `notify_chat_id`/`notify_msg_id`
- `bot.py` — register new `admin_hold_*` callback handler
