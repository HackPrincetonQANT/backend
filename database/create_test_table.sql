-- Create test table for categorization testing
-- This is a copy of the production purchase_items schema for safe testing

USE DATABASE SNOWFLAKE_LEARNING_DB;
USE SCHEMA BALANCEIQ_CORE;

CREATE OR REPLACE TABLE purchase_items_test (
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
  detected_needwant  STRING,
  user_needwant      STRING,
  reason             STRING,
  confidence         FLOAT,
  status             STRING DEFAULT 'active',
  raw_line           VARIANT
);

-- Verify table creation
SHOW TABLES LIKE 'purchase_items_test';
