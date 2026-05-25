-- Participants
CREATE TABLE IF NOT EXISTS participants (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id       BIGINT UNIQUE NOT NULL,
  username      TEXT,
  full_name     TEXT,
  phone         TEXT,
  age           INTEGER,
  gender        TEXT CHECK (gender IN ('M', 'F')),
  lang          TEXT CHECK (lang IN ('en', 'uk')) DEFAULT 'en',
  status        TEXT CHECK (status IN (
                  'incomplete',
                  'pending_payment',
                  'pending_approval',
                  'approved',
                  'denied'
                )) DEFAULT 'incomplete',
  denial_reason TEXT,
  needs_housing BOOLEAN DEFAULT NULL,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- Payment receipts (Telegram file_id)
CREATE TABLE IF NOT EXISTS receipts (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  participant_id UUID REFERENCES participants(id) ON DELETE CASCADE,
  file_id        TEXT NOT NULL,
  submitted_at   TIMESTAMPTZ DEFAULT now()
);

-- Housing units (admin-managed)
CREATE TABLE IF NOT EXISTS houses (
  id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name     TEXT NOT NULL UNIQUE,
  gender   TEXT CHECK (gender IN ('M', 'F')),
  capacity INTEGER NOT NULL
);

-- One reservation per participant
CREATE TABLE IF NOT EXISTS house_reservations (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  house_id       UUID REFERENCES houses(id) ON DELETE CASCADE,
  participant_id UUID REFERENCES participants(id) ON DELETE CASCADE,
  reserved_at    TIMESTAMPTZ DEFAULT now(),
  UNIQUE (participant_id)
);

-- Q&A submissions
CREATE TABLE IF NOT EXISTS questions (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  participant_id UUID REFERENCES participants(id) ON DELETE CASCADE,
  text           TEXT NOT NULL,
  submitted_at   TIMESTAMPTZ DEFAULT now()
);

-- Coordinator messages
CREATE TABLE IF NOT EXISTS messages (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  participant_id UUID REFERENCES participants(id) ON DELETE CASCADE,
  text           TEXT NOT NULL,
  submitted_at   TIMESTAMPTZ DEFAULT now()
);

-- Bot-wide config (schedule, venue, feature toggles)
CREATE TABLE IF NOT EXISTS bot_settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL DEFAULT ''
);

-- Seed default settings
INSERT INTO bot_settings (key, value) VALUES
  ('schedule_text', ''),
  ('venue_text', ''),
  ('qa_channel_id', ''),
  ('coord_channel_id', ''),
  ('qa_paused', 'false'),
  ('messages_paused', 'false'),
  ('housing_paused', 'false'),
  ('registration_locked', 'false'),
  ('admin_ids', '')
ON CONFLICT (key) DO NOTHING;
