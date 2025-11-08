USE ROLE BALANCEIQ_ROLE;
USE WAREHOUSE BALANCEIQ_WH;
USE DATABASE BALANCEIQ_DB;
USE SCHEMA CORE;

-- Demo user
INSERT INTO users (user_id, phone_e164, email)
VALUES ('u_demo', '+15551234567', 'demo@example.com');

INSERT INTO user_profile (user_id, display_name, age, location_country, location_region, tz, budgeting_style, saving_goals_json, preferences_json)
VALUES (
  'u_demo','Alex',25,'US','VA','America/New_York','moderate',
  PARSE_JSON('[{"goal_id":"g_bike","title":"Bike Fund","target_amount":250,"saved_amount":75}]'),
  PARSE_JSON('{"coffee_policy":"always_want"}')
);

-- Minimal, meaningful taxonomy
INSERT INTO category_taxonomy (category, subcategory, default_needwant, priority, notes) VALUES
('Rent', NULL, 'need', 1, 'Housing'),
('Groceries', NULL, 'need', 2, ''),
('Groceries', 'Fresh Produce', 'need', 2, ''),
('Groceries', 'Dairy', 'need', 2, ''),
('Healthcare', 'Medications', 'need', 1, ''),
('Transport', 'Public Transit', 'need', 2, ''),
('Coffee', NULL, 'want', 5, ''),
('Coffee', 'Latte', 'want', 5, ''),
('Dining Out', NULL, 'want', 5, ''),
('Dining Out', 'Fast Food', 'want', 5, ''),
('Electronics', 'Peripherals', 'want', 6, '');

-- User overrides
INSERT INTO user_category_rules (user_id, category, subcategory, rule, reason) VALUES
('u_demo','Coffee',NULL,'always_want','Treats flagged as wants'),
('u_demo','Groceries','Fresh Produce','always_need','Healthy staples');

-- Optional sample purchase header
INSERT INTO purchases (purchase_id, user_id, merchant, ts, currency, total_amount, source)
VALUES ('p_demo_1', 'u_demo', 'Starbucks', CURRENT_TIMESTAMP(), 'USD', 5.25, 'API');