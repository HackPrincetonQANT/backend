USE ROLE BALANCEIQ_ROLE;
USE WAREHOUSE BALANCEIQ_WH;
USE DATABASE BALANCEIQ_DB;
USE SCHEMA CORE;

CREATE OR REPLACE VIEW v_weekly_want_ratio AS
SELECT
  user_id,
  DATE_TRUNC('day', ts) AS day,
  COUNT_IF(COALESCE(user_needwant, detected_needwant) = 'want')::FLOAT /
  NULLIF(COUNT(*),0) AS want_ratio
FROM purchase_items
WHERE ts >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY 1,2;

CREATE OR REPLACE VIEW v_wants_by_merchant AS
SELECT
  user_id,
  merchant,
  COUNT_IF(COALESCE(user_needwant, detected_needwant)='want') AS want_count,
  COUNT(*) AS total_count,
  want_count::FLOAT / NULLIF(total_count,0) AS want_share
FROM purchase_items
WHERE ts >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY 1,2
QUALIFY want_count >= 3
ORDER BY want_share DESC, want_count DESC;

CREATE OR REPLACE VIEW v_user_profile_summary AS
SELECT
  u.user_id,
  p.display_name,
  p.age,
  p.location_country,
  p.location_region,
  p.tz,
  p.budgeting_style,
  (SELECT COUNT(*) FROM purchase_items pi WHERE pi.user_id = u.user_id) AS lifetime_items
FROM users u
LEFT JOIN user_profile p USING (user_id);