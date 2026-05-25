import os

# ─── Conference identity ───────────────────────────────────────────────────────
CONF_NAME = "WeAre"

# ─── Telegram ─────────────────────────────────────────────────────────────────
BOT_TOKEN    = os.environ["BOT_TOKEN"]
WEBHOOK_URL  = os.environ["WEBHOOK_URL"]
OWNER_ID     = 479515546                          # primary (used as fallback notify chat)
OWNER_IDS    = {479515546, 426569764}             # all owners
ADMIN_IDS    = [479515546, 426569764]             # expandable via /addadmin at runtime

# ─── Group for admin notifications (receipt alerts, Q&A forwards, etc.) ───────
_group_chat_raw = os.getenv("GROUP_CHAT_ID", "0").strip()
GROUP_CHAT_ID = int(_group_chat_raw) if _group_chat_raw.lstrip('-').isdigit() else 0

# ─── Supabase ─────────────────────────────────────────────────────────────────
SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
SUPABASE_ANON_KEY    = os.environ["SUPABASE_ANON_KEY"]

# ─── Payment ──────────────────────────────────────────────────────────────────
PAYMENT_LINK = os.getenv("PAYMENT_LINK", "PAYMENT_LINK_PLACEHOLDER")

# ─── Registration pricing ──────────────────────────────────────────────────────
PRICE_WITH_HOUSING    = 175   # registration fee with conference housing
PRICE_WITHOUT_HOUSING = 100   # registration fee without housing

# ─── Feature flags (defaults — overridden at runtime via bot_settings) ────────
QA_RATE_LIMIT = 3   # max questions per participant
