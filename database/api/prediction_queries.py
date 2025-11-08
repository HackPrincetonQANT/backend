# Prediction Model Queries
# Optimized queries for ML predictions using purchase_items table

import os

DB = os.getenv("SNOWFLAKE_DATABASE", "SNOWFLAKE_LEARNING_DB")
SC = os.getenv("SNOWFLAKE_SCHEMA", "BALANCEIQ_CORE")

# ============================================================================
# Prediction Model Queries
# ============================================================================

# Get aggregated transactions for prediction model
# This view makes purchase_items compatible with existing prediction code
SQL_GET_TRANSACTIONS_FOR_PREDICTIONS = f"""
SELECT *
FROM {DB}.{SC}.transactions_for_predictions
WHERE user_id = %(user_id)s
  AND occurred_at >= DATEADD('day', -%(days)s, CURRENT_TIMESTAMP())
ORDER BY occurred_at DESC
"""

# Get category spending patterns (twice-weekly analysis)
SQL_GET_CATEGORY_SPENDING = f"""
SELECT
  category,
  subcategory,
  week_start,
  COUNT(DISTINCT purchase_id) AS purchases_per_week,
  SUM(total_spend) AS weekly_spend,
  SUM(need_spend) AS need_spend,
  SUM(want_spend) AS want_spend,
  AVG(avg_confidence) AS avg_confidence
FROM {DB}.{SC}.category_spending_summary
WHERE user_id = %(user_id)s
  AND week_start >= DATEADD('week', -%(weeks)s, CURRENT_TIMESTAMP())
GROUP BY category, subcategory, week_start
ORDER BY category, week_start DESC
"""

# Find overspending categories (for insights)
SQL_FIND_OVERSPENDING = f"""
WITH spending_stats AS (
  SELECT
    user_id,
    category,
    week_start,
    total_spend,
    AVG(total_spend) OVER (
      PARTITION BY user_id, category
      ORDER BY week_start
      ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING
    ) AS avg_last_4_weeks,
    STDDEV(total_spend) OVER (
      PARTITION BY user_id, category
      ORDER BY week_start
      ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING
    ) AS stddev_last_4_weeks
  FROM {DB}.{SC}.category_spending_summary
  WHERE user_id = %(user_id)s
)
SELECT
  category,
  week_start,
  total_spend,
  avg_last_4_weeks,
  ((total_spend - avg_last_4_weeks) / NULLIF(stddev_last_4_weeks, 0)) AS z_score
FROM spending_stats
WHERE week_start = (SELECT MAX(week_start) FROM spending_stats)
  AND total_spend > avg_last_4_weeks * 1.5  -- 50% above average
ORDER BY z_score DESC NULLS LAST
LIMIT 5
"""

# Get items for semantic search (alternative suggestions)
SQL_SEMANTIC_SEARCH_ITEMS = f"""
SELECT
  item_id,
  item_name,
  item_text,
  item_embed,
  category,
  subcategory,
  price,
  merchant,
  ts
FROM {DB}.{SC}.purchase_items
WHERE user_id = %(user_id)s
  AND item_embed IS NOT NULL
  AND status = 'active'
ORDER BY ts DESC
LIMIT 200
"""

# Get category trends (for predictions)
SQL_CATEGORY_TRENDS = f"""
SELECT
  category,
  week_start,
  SUM(total_spend) AS weekly_spend,
  SUM(want_spend) / NULLIF(SUM(total_spend), 0) AS want_ratio,
  COUNT(DISTINCT purchase_id) AS purchase_frequency
FROM {DB}.{SC}.category_spending_summary
WHERE user_id = %(user_id)s
  AND week_start >= DATEADD('week', -12, CURRENT_TIMESTAMP())
GROUP BY category, week_start
ORDER BY category, week_start
"""

# Find cancellation candidates (recurring wants with high spend)
SQL_CANCELLATION_CANDIDATES = f"""
WITH recurring_wants AS (
  SELECT
    category,
    subcategory,
    merchant,
    COUNT(DISTINCT week_start) AS weeks_purchased,
    SUM(total_spend) AS total_spend,
    AVG(total_spend) AS avg_weekly_spend,
    SUM(want_spend) / NULLIF(SUM(total_spend), 0) AS want_ratio
  FROM {DB}.{SC}.category_spending_summary
  WHERE user_id = %(user_id)s
    AND week_start >= DATEADD('week', -8, CURRENT_TIMESTAMP())
  GROUP BY category, subcategory, merchant
)
SELECT
  category,
  subcategory,
  merchant,
  weeks_purchased,
  total_spend,
  avg_weekly_spend,
  want_ratio,
  (total_spend * want_ratio) AS cancellable_amount
FROM recurring_wants
WHERE weeks_purchased >= 4  -- Recurring (at least 4 weeks)
  AND want_ratio > 0.7      -- Mostly wants
  AND total_spend > 50      -- Significant spend
ORDER BY cancellable_amount DESC
LIMIT 10
"""
