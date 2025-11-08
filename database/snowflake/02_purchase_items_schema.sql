-- Unified Schema for Categorization + ML Predictions
-- This schema supports both detailed item categorization AND prediction model needs

USE DATABASE SNOWFLAKE_LEARNING_DB;
USE SCHEMA BALANCEIQ_CORE;

-- ============================================================================
-- Main Table: purchase_items (Single Source of Truth)
-- ============================================================================
-- Stores individual purchase items with AI categorization and embeddings
-- Serves both categorization tracking AND ML prediction needs

CREATE OR REPLACE TABLE purchase_items (
  -- Identity
  item_id            STRING PRIMARY KEY,
  purchase_id        STRING,              -- Groups items from same purchase
  user_id            STRING,

  -- Purchase Details
  merchant           STRING,
  ts                 TIMESTAMP_TZ,        -- When purchased

  -- Item Information
  item_name          STRING,              -- Original item name
  item_text          STRING,              -- Normalized text for ML: "merchant · category · item_name"

  -- AI Categorization (from Dedalus)
  category           STRING,              -- Main category (e.g., "Groceries", "Electronics")
  subcategory        STRING,              -- Optional subcategory for detail

  -- Financial
  price              NUMBER(12,2),        -- Item price
  qty                NUMBER(10,2) DEFAULT 1,
  tax                NUMBER(12,2),
  tip                NUMBER(12,2),

  -- Need/Want Classification
  detected_needwant  STRING,              -- AI prediction: 'need' | 'want' | NULL
  user_needwant      STRING,              -- User override: 'need' | 'want' | NULL

  -- AI Metadata
  reason             STRING,              -- Why this category (from Dedalus)
  confidence         FLOAT,               -- Categorization confidence (0..1)

  -- ML/Embeddings (for semantic search & predictions)
  item_embed         VECTOR(FLOAT, 768),  -- Snowflake Cortex embedding

  -- Status
  status             STRING DEFAULT 'active',  -- 'active' | 'refunded' | 'reversed'
  raw_line           VARIANT,             -- Original JSON data

  -- Audit
  created_at         TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);

-- Indexes for common query patterns
ALTER TABLE purchase_items CLUSTER BY (user_id, ts);

-- ============================================================================
-- Helper View: transactions_for_predictions
-- ============================================================================
-- Aggregates item-level data into transaction-level for prediction model
-- Compatible with existing prediction code structure

CREATE OR REPLACE VIEW transactions_for_predictions AS
SELECT
  purchase_id AS id,
  user_id,
  ANY_VALUE(merchant) AS merchant,

  -- Aggregate financials
  SUM(price * qty) AS amount_cents,
  ANY_VALUE('USD') AS currency,

  -- Use most common category in purchase
  MODE(category) AS category,

  -- Aggregate need/want (prefer user override, fallback to detected)
  MODE(COALESCE(user_needwant, detected_needwant)) AS need_or_want,

  -- Average confidence across items
  AVG(confidence) AS confidence,

  -- Purchase timestamp
  ANY_VALUE(ts) AS occurred_at,

  -- Concatenated item text for semantic search
  LISTAGG(item_name, ' · ') WITHIN GROUP (ORDER BY item_id) AS item_text,

  -- Use first item's embedding as purchase embedding (can be refined later)
  ANY_VALUE(item_embed) AS item_embed,

  -- Audit
  MIN(created_at) AS created_at

FROM purchase_items
WHERE status = 'active'
GROUP BY purchase_id, user_id;

-- ============================================================================
-- Helper View: category_spending_summary
-- ============================================================================
-- Pre-aggregated spending by category for fast prediction queries
-- Supports twice-weekly analysis

CREATE OR REPLACE VIEW category_spending_summary AS
SELECT
  user_id,
  category,
  subcategory,

  -- Time windows
  DATE_TRUNC('week', ts) AS week_start,
  DATE_TRUNC('month', ts) AS month_start,

  -- Aggregates
  COUNT(DISTINCT purchase_id) AS purchase_count,
  COUNT(item_id) AS item_count,
  SUM(price * qty) AS total_spend,
  AVG(price * qty) AS avg_item_spend,

  -- Need/Want breakdown
  SUM(CASE WHEN COALESCE(user_needwant, detected_needwant) = 'need' THEN price * qty ELSE 0 END) AS need_spend,
  SUM(CASE WHEN COALESCE(user_needwant, detected_needwant) = 'want' THEN price * qty ELSE 0 END) AS want_spend,

  -- Quality metrics
  AVG(confidence) AS avg_confidence,
  COUNT(CASE WHEN user_needwant IS NOT NULL THEN 1 END) AS user_labeled_count

FROM purchase_items
WHERE status = 'active'
GROUP BY user_id, category, subcategory, week_start, month_start;

COMMENT ON TABLE purchase_items IS 'Single source of truth for categorized purchase items. Supports both detailed tracking and ML predictions.';
COMMENT ON VIEW transactions_for_predictions IS 'Transaction-level aggregation for prediction model. Compatible with existing TRANSACTIONS table structure.';
COMMENT ON VIEW category_spending_summary IS 'Pre-aggregated spending by category for twice-weekly prediction analysis.';
