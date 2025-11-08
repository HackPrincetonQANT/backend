-- Generate Embeddings for ML/Semantic Search
-- Run this after inserting new items to populate item_embed column
-- Uses Snowflake Cortex AI for embedding generation

USE DATABASE SNOWFLAKE_LEARNING_DB;
USE SCHEMA BALANCEIQ_CORE;

-- ============================================================================
-- Generate embeddings for items without embeddings
-- ============================================================================

-- For production table
UPDATE purchase_items
SET item_embed = SNOWFLAKE.CORTEX.AI_EMBED_768('e5-base-v2', item_text)
WHERE item_text IS NOT NULL
  AND item_embed IS NULL
  AND status = 'active';

-- For test table
UPDATE purchase_items_test
SET item_embed = SNOWFLAKE.CORTEX.AI_EMBED_768('e5-base-v2', item_text)
WHERE item_text IS NOT NULL
  AND item_embed IS NULL
  AND status = 'active';

-- Verify embeddings generated
SELECT
  'production' AS table_name,
  COUNT(*) AS total_items,
  COUNT(item_embed) AS items_with_embeddings,
  ROUND(COUNT(item_embed) * 100.0 / COUNT(*), 2) AS coverage_percent
FROM purchase_items
WHERE status = 'active'
UNION ALL
SELECT
  'test' AS table_name,
  COUNT(*) AS total_items,
  COUNT(item_embed) AS items_with_embeddings,
  ROUND(COUNT(item_embed) * 100.0 / COUNT(*), 2) AS coverage_percent
FROM purchase_items_test
WHERE status = 'active';
