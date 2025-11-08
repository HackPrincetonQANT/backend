-- Backward Compatibility View: TRANSACTIONS
-- This view aggregates purchase_items into transaction-level data
-- Compatible with existing queries.py that reference TRANSACTIONS table
--
-- Purpose: Allows legacy code to work without modification while
--          maintaining purchase_items as the single source of truth

USE DATABASE SNOWFLAKE_LEARNING_DB;
USE SCHEMA BALANCEIQ_CORE;

-- ============================================================================
-- TRANSACTIONS View (Backward Compatibility)
-- ============================================================================
-- Aggregates item-level data from purchase_items into transaction-level
-- This maintains compatibility with existing queries.py code

CREATE OR REPLACE VIEW TRANSACTIONS AS
SELECT
  -- Identity (transaction-level)
  purchase_id AS id,
  user_id,

  -- Purchase Details
  ANY_VALUE(merchant) AS merchant,
  ANY_VALUE(ts) AS occurred_at,

  -- Financial (aggregated from items)
  SUM(price * qty) AS amount_cents,
  ANY_VALUE('USD') AS currency,

  -- Categorization (use most common category in purchase)
  MODE(category) AS category,

  -- Need/Want (prefer user override, fallback to detected)
  MODE(COALESCE(user_needwant, detected_needwant)) AS need_or_want,

  -- AI Metadata (average confidence across items)
  AVG(confidence) AS confidence,

  -- Transaction-level ID (for compatibility)
  purchase_id AS transaction_id,

  -- Audit
  MIN(created_at) AS created_at

FROM purchase_items
WHERE status = 'active'
GROUP BY purchase_id, user_id;

-- Add comment
COMMENT ON VIEW TRANSACTIONS IS 'Backward compatibility view that aggregates purchase_items to transaction-level. Maintains compatibility with queries.py while purchase_items remains the source of truth.';

-- Verify the view
SELECT
  'TRANSACTIONS view created' AS status,
  COUNT(*) AS example_record_count
FROM TRANSACTIONS
LIMIT 1;

-- ============================================================================
-- USER_REPLIES Table (Backward Compatibility)
-- ============================================================================
-- Stores user feedback/corrections on categorizations
-- Referenced by queries.py

CREATE TABLE IF NOT EXISTS USER_REPLIES (
  id                 STRING PRIMARY KEY,
  transaction_id     STRING,              -- Maps to purchase_id
  user_id            STRING,
  user_label         STRING,              -- User's correction/feedback
  received_at        TIMESTAMP_TZ,
  created_at         TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);

COMMENT ON TABLE USER_REPLIES IS 'Stores user feedback and corrections on transaction categorizations. Referenced by queries.py for backward compatibility.';

-- ============================================================================
-- PREDICTIONS Table (Backward Compatibility)
-- ============================================================================
-- Stores ML prediction results for user insights
-- Referenced by queries.py

CREATE TABLE IF NOT EXISTS PREDICTIONS (
  id                 STRING PRIMARY KEY,
  user_id            STRING,
  prediction_type    STRING,              -- 'overspending'|'cancellation'|'savings'
  category           STRING,
  subcategory        STRING,
  merchant           STRING,
  amount_cents       NUMBER(12,2),
  confidence         FLOAT,
  insight_text       STRING,              -- Human-readable insight
  metadata           VARIANT,             -- Additional prediction data
  created_at         TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);

COMMENT ON TABLE PREDICTIONS IS 'Stores ML prediction results and insights. Referenced by queries.py for backward compatibility.';
