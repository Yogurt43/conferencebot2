import os

# ─── Conference identity ───────────────────────────────────────────────────────
CONF_NAME = "CONFERENCE_NAME"   # ← replace this one line to rebrand

# ─── Telegram ─────────────────────────────────────────────────────────────────
BOT_TOKEN    = os.environ["BOT_TOKEN"]
WEBHOOK_URL  = os.environ["WEBHOOK_URL"]
OWNER_ID     = 479515546
ADMIN_IDS    = [479515546, 426569764]   # expandable via /addadmin at runtime

# ─── Group for admin notifications (receipt alerts, Q&A forwards, etc.) ───────
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))

# ─── Supabase ─────────────────────────────────────────────────────────────────
SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
SUPABASE_ANON_KEY    = os.environ["SUPABASE_ANON_KEY"]

# ─── Payment ──────────────────────────────────────────────────────────────────
PAYMENT_LINK = os.getenv("PAYMENT_LINK", "PAYMENT_LINK_PLACEHOLDER")

# ─── Feature flags (defaults — overridden at runtime via bot_settings) ────────
QA_RATE_LIMIT = 3   # max questions per participant
