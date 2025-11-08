PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS transactions (
  id                      TEXT PRIMARY KEY,
  user_id                 TEXT NOT NULL,
  transaction_id          TEXT,
  merchant                TEXT,
  amount_cents            INTEGER NOT NULL,
  currency                TEXT,
  category                TEXT,
  need_or_want            TEXT,
  confidence              REAL,
  occurred_at             TEXT,        -- ISO8601
  created_at              TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tx_user_date ON transactions (user_id, occurred_at);

CREATE TABLE IF NOT EXISTS user_replies (
  id                      TEXT PRIMARY KEY,
  transaction_id          TEXT NOT NULL,  -- soft FK to transactions.id
  user_id                 TEXT NOT NULL,
  user_label              TEXT,
  received_at             TEXT,
  created_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS predictions (
  id                      TEXT PRIMARY KEY,
  user_id                 TEXT NOT NULL,
  category                TEXT NOT NULL,
  window_start            TEXT,
  window_end              TEXT,
  probability             REAL,
  annual_savings_hint_usd REAL,
  created_at              TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pred_user_cat ON predictions (user_id, category);