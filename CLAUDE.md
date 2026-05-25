# WeAre Conference Bot — Project Context

## What This Is
A Telegram bot for managing conference registrations, payment receipt verification, gender-based housing reservations, and participant Q&A. Built for the "WeAre" conference.

## Tech Stack
- **Python 3.11+** with `python-telegram-bot` v20+ (async, webhook mode)
- **Flask** — webhook receiver (sync bridge to PTB's async loop via `run_async`)
- **Supabase** (Postgres) — all persistent state
- **Render** — deployment (web service, auto-deploy from GitHub main branch)

## Architecture
- `bot.py` — Flask app + PTB Application, handler registration, webhook endpoint
- `config.py` — env vars, owner/admin IDs, feature flags, price constants
- `db.py` — all Supabase calls (ORM-like interface)
- `strings.py` — all user-facing text, EN + UK, via `t(lang, key, **kwargs)`
- `utils.py` — validate_age (10–99), format_house_button, get_lang, is_admin
- `handlers/registration.py` — ConversationHandler for registration flow
- `handlers/housing.py` — post-approval house selection
- `handlers/admin.py` — all admin/owner commands + inline approval/deny/hold flow
- `handlers/info.py` — schedule, venue, Q&A, coordinator messages, pre-approval questions

## Registration Flow (ConversationHandler)
LANG → NAME → AGE → GENDER → HOUSING_PREF → [HOUSE_SELECT] → PHONE → RECEIPT → END

States are integers 0–8; `PAYMENT_STEP` (7) is reserved/unused.

- **Welcome message**: shown before language selection — displays conference name and pricing (with/without housing)
- **HOUSING_PREF**: shows price breakdown, records `needs_housing` boolean, and if Yes: immediately shows house list → HOUSE_SELECT
- **HOUSE_SELECT**: creates a *tentative* reservation (status=`tentative`) during registration; confirmed on approval
- **RECEIPT**: accepts photo or document only; text input nudges user to use buttons; has "❓ Have a Question?" inline button
- **On receipt upload**: notifies admin group with photo + Approve / ⏸ On Hold / ❌ Deny inline buttons

### Re-entry paths
- **`denied`**: shows denial reason + re-upload prompt; if `needs_housing` is NULL → HOUSING_PREF; if needs_housing but no reservation → HOUSE_SELECT; else → RECEIPT
- **`on_hold`**: shows hold reason + re-upload prompt → RECEIPT
- **`approved`**: shows main menu, ends conversation

## Housing Flow (post-approval, main menu)
Menu → house list filtered by participant gender and **available capacity** (full houses hidden)
→ select → confirm (capacity double-checked) → reserved

- Approved users with `needs_housing=True` get a house-selection prompt immediately on approval
- Tentative reservations (created during registration) are confirmed on approval, released on denial
- `get_reservation()` only fetches confirmed reservations; tentative ones are internal

**Important**: registration uses `housing_yes`/`housing_no` callbacks; main menu uses
`menu_housing_yes`/`menu_housing_no` — different to avoid ConversationHandler collision.

## Admin Flows

### Approve
1. Admin clicks ✅ Approve (inline) or `/approve <id>`
2. Participant status → `approved`; tentative reservation → confirmed
3. Approved welcome message + main menu sent to user (wrapped in try/except — user may have blocked bot)
4. If `needs_housing=True` and no reservation: house-selection prompt sent to user

### Deny
1. Admin clicks ❌ Deny on receipt notification
2. `cb_admin_deny_start` stores target in `_deny_pending` (memory + Supabase for restart survival)
3. Admin types reason as plain text in group → `handle_setting_input` processes it
4. **Race guard**: status is re-checked before writing — if user was already approved by another admin, deny is cancelled
5. User receives denial notification; tentative reservation released; admin sees updated caption

### On Hold
1. Admin clicks ⏸ On Hold → prompts for reason
2. State stored in `_hold_pending` (memory + Supabase)
3. Participant status → `on_hold`; user notified with "Have a Question?" button
4. **Race guard**: same approve-first guard as deny flow
5. User re-enters via `/start` → on_hold re-entry path → RECEIPT

**Critical**: info.py's `handle_text_input` is registered in PTB group=1, admin's
`handle_setting_input` is in group=0 — this ensures admin text is processed first.
Bot must have privacy mode DISABLED in BotFather to receive plain group messages.

## Pre-Approval Questions
Users in RECEIPT state (or on-hold re-entry) see a "❓ Have a Question?" button.
- Pressing it adds them to `_awaiting_msg` in info.py
- Their next text message is forwarded to the organiser channel with full profile context (name, status, amount due, contact link)
- Handled by `handle_coordinator_pre_approval` (CallbackQueryHandler) + `handle_text_input` (MessageHandler)

## Owners vs Admins
- `OWNER_IDS = {479515546, 426569764}` — both are owners (full access)
- `OWNER_ID = 479515546` — primary, used as fallback notify chat if GROUP_CHAT_ID unset
- `ADMIN_IDS = [479515546, 426569764]` — expandable via `/addadmin` at runtime
- `_require_owner` checks against `OWNER_IDS`; `_require_admin` checks `is_admin()`
- `/help` shows owner-only section only to owners

## Houses
Houses are managed directly in Supabase (no bot commands for add/remove).
Schema: `id, name, gender (M|F), capacity` — address and notes columns removed.

Current houses (added via SQL):
- **Female (Timber Village)**: Hemlock, Madrona, Cedar, Spruce
- **Male (Cascade Village)**: Lassen, Rainier, Hood, Bachelor

## Q&A and Coordinator Messages
Both forward to `coord_channel_id` from `bot_settings` table (set once in Supabase).
Falls back to `GROUP_CHAT_ID` env var if not set.

## Pricing
Set in `config.py` as `PRICE_WITH_HOUSING` and `PRICE_WITHOUT_HOUSING` (integers, e.g. 150 / 100).
Displayed in welcome message, HOUSING_PREF step, payment instructions, and pre-approval org notifications.

## Key Commands
- `/help` — lists all commands (owner section hidden from non-owners)
- `/pending` — show registrations awaiting review
- `/participants` — all participants with status
- `/listhouses` — house occupancy
- `/moveresident <id> <house>` — reassign someone's house
- `/testsetup` — (owner only) deletes caller's own participant record for re-testing
- `/broadcast <msg>` — send to all approved participants
- `/setschedule`, `/setvenue` — set info text
- `/pause`/`/resume` `<housing|qa|messages>` — toggle features

## Supabase Schema Notes
Tables: `participants`, `receipts`, `houses`, `house_reservations`, `questions`, `messages`, `bot_settings`

`participants` key columns: `chat_id`, `username`, `full_name`, `age`, `gender`, `phone`, `lang`, `status`, `needs_housing`, `denial_reason`, `notify_chat_id`, `notify_msg_id`

`house_reservations` has a `status` column (`tentative` | `confirmed`):
- Tentative created during registration; confirmed on approval; released on denial
- `get_reservation()` returns any reservation (used for menu display)
- `confirm_reservation()` upgrades tentative → confirmed
- `release_tentative_reservation()` deletes tentative only (safe to call on denial)

Schema migrations applied:
```sql
ALTER TABLE participants ADD COLUMN IF NOT EXISTS needs_housing BOOLEAN DEFAULT NULL;
ALTER TABLE houses DROP COLUMN IF EXISTS address;
ALTER TABLE houses DROP COLUMN IF EXISTS notes;
-- house_reservations.status column must exist with default 'confirmed'
```

## Deployment
- GitHub: `https://github.com/Yogurt43/weare-conference-bot.git` (main branch)
- Render auto-deploys on push — webhook has been flaky; use Manual Deploy if commit doesn't trigger
- Render env vars: `BOT_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_ANON_KEY`, `WEBHOOK_URL`, `GROUP_CHAT_ID`, `PAYMENT_LINK`

## Known Gotchas
- PTB handler groups: info text handler is group=1, admin text handler is group=0 — do not change this order or deny/hold flow breaks
- ConversationHandler is `persistent=False` — state lost on bot restart; users mid-flow may need to `/start` again
- `validate_age` accepts 10–99 only (2-digit numbers)
- Privacy mode must be OFF in BotFather for bot to receive plain text in groups
- `housing_yes`/`housing_no` callback data is used by ConversationHandler HOUSING_PREF state; main menu uses `menu_housing_yes`/`menu_housing_no` — never reuse the former outside the ConversationHandler
- `_md_escape()` exists in both `registration.py` and `info.py` — use it whenever embedding user-supplied text (name, phone, message body) in a `parse_mode=MARKDOWN` message
- All `send_message` calls targeting user chat_ids are wrapped in `try/except` — a blocked-bot Forbidden error must never prevent DB state from being written
- Full houses are filtered out of the house-selection list in `_show_house_list()` (housing.py) — `handle_house_confirm` still double-checks capacity as a race guard
- Deny/hold `handle_setting_input` re-fetches participant and checks `status == 'approved'` before writing — prevents a race where another admin approved first
