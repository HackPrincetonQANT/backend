USE ROLE BALANCEIQ_ROLE;
USE WAREHOUSE BALANCEIQ_WH;
USE DATABASE BALANCEIQ_DB;
USE SCHEMA CORE;

-- Users & Profile
CREATE OR REPLACE TABLE users (
  user_id            STRING PRIMARY KEY,
  phone_e164         STRING,
  email              STRING,
  created_at         TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE user_profile (
  user_id            STRING PRIMARY KEY,
  display_name       STRING,
  age                NUMBER(3,0),
  location_country   STRING,
  location_region    STRING,
  tz                 STRING DEFAULT 'America/New_York',
  income_bracket     STRING,        -- 'low'|'mid'|'high'
  budgeting_style    STRING,        -- 'strict'|'moderate'|'loose'
  saving_goals_json  VARIANT,       -- [{goal_id,title,target_amount,saved_amount}, ...]
  preferences_json   VARIANT,       -- {"coffee_policy":"always_want", ...}
  updated_at         TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT fk_user_prof FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Category Taxonomy & User Rules
CREATE OR REPLACE TABLE category_taxonomy (
  category           STRING,
  subcategory        STRING,
  default_needwant   STRING,          -- 'need'|'want'
  priority           NUMBER(2,0) DEFAULT 5,  -- lower = more essential
  notes              STRING,
  PRIMARY KEY (category, subcategory)
);

CREATE OR REPLACE TABLE user_category_rules (
  user_id            STRING,
  category           STRING,
  subcategory        STRING,          -- NULL = applies to whole category
  rule               STRING,          -- 'always_need'|'always_want'|'ban'
  reason             STRING,
  updated_at         TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
  PRIMARY KEY (user_id, category, subcategory)
);

-- Purchases (header)
CREATE OR REPLACE TABLE purchases (
  purchase_id        STRING PRIMARY KEY,
  user_id            STRING,
  merchant           STRING,
  ts                 TIMESTAMP_TZ,
  currency           STRING DEFAULT 'USD',
  total_amount       NUMBER(12,2),
  source             STRING,          -- 'KNOTAPI'|'API'|...
  raw_payload        VARIANT,
  CONSTRAINT fk_user_purch FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Purchase Items (line-level – core for classification)
CREATE OR REPLACE TABLE purchase_items (
  item_id            STRING PRIMARY KEY,
  purchase_id        STRING,
  user_id            STRING,
  merchant           STRING,
  ts                 TIMESTAMP_TZ,
  item_name          STRING,
  category           STRING,
  subcategory        STRING,
  price              NUMBER(12,2),
  qty                NUMBER(10,2) DEFAULT 1,
  tax                NUMBER(12,2),
  tip                NUMBER(12,2),
  detected_needwant  STRING,          -- classifier result
  user_needwant      STRING,          -- user answer later
  reason             STRING,          -- explanation for detected_needwant
  confidence         FLOAT,           -- 0..1
  status             STRING DEFAULT 'active',  -- 'active'|'reversed'|'refunded'
  raw_line           VARIANT,
  CONSTRAINT fk_purch_items FOREIGN KEY (purchase_id) REFERENCES purchases(purchase_id)
);

-- Classification Audit
CREATE OR REPLACE TABLE classification_log (
  event_id           STRING PRIMARY KEY,
  user_id            STRING,
  item_id            STRING,
  merchant           STRING,
  ts                 TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
  item_name          STRING,
  category           STRING,
  subcategory        STRING,
  classifier         STRING,          -- 'rules'|'llm'|'manual'
  result_needwant    STRING,          -- 'need'|'want'|'unknown'
  reason             STRING,
  confidence         FLOAT,
  meta               VARIANT
);