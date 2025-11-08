-- Create test table for categorization testing
-- Unified schema matching production purchase_items
-- Supports both categorization AND ML predictions

USE DATABASE SNOWFLAKE_LEARNING_DB;
USE SCHEMA BALANCEIQ_CORE;

CREATE OR REPLACE TABLE purchase_items_test (
  -- Identity
  item_id            STRING PRIMARY KEY,
  purchase_id        STRING,
  user_id            STRING,

  -- Purchase Details
  merchant           STRING,
  ts                 TIMESTAMP_TZ,

  -- Item Information
  item_name          STRING,
  item_text          STRING,              -- For ML: "merchant · category · item_name"

  -- AI Categorization
  category           STRING,
  subcategory        STRING,

  -- Financial
  price              NUMBER(12,2),
  qty                NUMBER(10,2) DEFAULT 1,
  tax                NUMBER(12,2),
  tip                NUMBER(12,2),

  -- Need/Want Classification
  detected_needwant  STRING,
  user_needwant      STRING,

  -- AI Metadata
  reason             STRING,
  confidence         FLOAT,

  -- ML/Embeddings
  item_embed         VECTOR(FLOAT, 768),  -- Snowflake Cortex embedding

  -- Status
  status             STRING DEFAULT 'active',
  raw_line           VARIANT,

  -- Audit
  created_at         TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);

-- Verify table creation
SHOW TABLES LIKE 'purchase_items_test';
