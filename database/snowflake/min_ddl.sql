USE ROLE BALANCEIQ_ROLE;
USE WAREHOUSE BALANCEIQ_WH;
USE DATABASE BALANCEIQ_DB;
USE SCHEMA CORE;

-- ========================
-- TABLES
-- ========================
CREATE OR REPLACE TABLE transactions (
  id                      STRING,              -- UUID v4 from backend
  user_id                 STRING,
  transaction_id          STRING,              -- external id from Knot/Bank; nullable for manual
  merchant                STRING,
  amount_cents            NUMBER(12,0),        -- store money as integer cents
  currency                STRING,              -- 'USD', ...
  category                STRING,              -- backend category (e.g., 'Coffee','Groceries')
  need_or_want            STRING,              -- 'need' | 'want' | 'unknown'
  confidence              FLOAT,               -- 0..1
  occurred_at             TIMESTAMP_TZ,        -- when it happened
  created_at              TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_transactions PRIMARY KEY (id)
);

CREATE OR REPLACE TABLE user_replies (
  id                      STRING,              -- UUID v4
  transaction_id          STRING,              -- references transactions.id (soft FK)
  user_id                 STRING,
  user_label              STRING,              -- 'need' | 'want' | 'unknown'
  received_at             TIMESTAMP_TZ,
  created_at              TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_user_replies PRIMARY KEY (id)
);

CREATE OR REPLACE TABLE predictions (
  id                      STRING,              -- UUID v4
  user_id                 STRING,
  category                STRING,
  window_start            TIMESTAMP_TZ,
  window_end              TIMESTAMP_TZ,
  probability             FLOAT,               -- 0..1 (likelihood of purchase in window)
  annual_savings_hint_usd NUMBER(10,2),        -- optional explainer metric
  created_at              TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_predictions PRIMARY KEY (id)
);

-- ========================
-- INDEXES (Snowflake: use cluster keys for big tables; secondary indexes are limited)
-- For dev/early prod, these filters are common:
--   WHERE user_id = ? ORDER BY occurred_at DESC
--   WHERE user_id = ? AND category = ?
-- You can add CLUSTER BY to help pruning when scale grows.
ALTER TABLE transactions CLUSTER BY (user_id, occurred_at);
ALTER TABLE predictions  CLUSTER BY (user_id, category);