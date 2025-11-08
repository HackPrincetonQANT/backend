USE ROLE BALANCEIQ_ROLE;
USE WAREHOUSE BALANCEIQ_WH;
USE DATABASE BALANCEIQ_DB;
USE SCHEMA CORE;

-- demo constants
SET demo_user = 'u_demo_min';

-- 12 transactions across 4 categories
INSERT INTO transactions (id,user_id,transaction_id,merchant,amount_cents,currency,category,need_or_want,confidence,occurred_at)
VALUES
  ('t1', $demo_user, 'ext-1001', 'Starbucks',          525,  'USD','Coffee','want', 0.95, DATEADD('day',-1, CURRENT_TIMESTAMP())),
  ('t2', $demo_user, 'ext-1002', 'Walmart',            389,  'USD','Groceries','need', 0.90, DATEADD('day',-2, CURRENT_TIMESTAMP())),
  ('t3', $demo_user, 'ext-1003', 'Chipotle',          1299,  'USD','Dining Out','want', 0.85, DATEADD('day',-3, CURRENT_TIMESTAMP())),
  ('t4', $demo_user, 'ext-1004', 'Metro',              250,  'USD','Transport','need', 0.80, DATEADD('day',-3, CURRENT_TIMESTAMP())),
  ('t5', $demo_user, 'ext-1005', 'Amazon',            5999,  'USD','Electronics','want', 0.70, DATEADD('day',-4, CURRENT_TIMESTAMP())),
  ('t6', $demo_user, 'ext-1006', 'Trader Joes',       4587,  'USD','Groceries','need', 0.88, DATEADD('day',-5, CURRENT_TIMESTAMP())),
  ('t7', $demo_user, 'ext-1007', 'Starbucks',          525,  'USD','Coffee','want', 0.95, DATEADD('day',-6, CURRENT_TIMESTAMP())),
  ('t8', $demo_user, 'ext-1008', 'Apartment Rent', 120000,  'USD','Rent','need', 0.99, DATEADD('day',-10, CURRENT_TIMESTAMP())),
  ('t9', $demo_user, 'ext-1009', 'CVS Pharmacy',      1899,  'USD','Healthcare','need', 0.90, DATEADD('day',-9, CURRENT_TIMESTAMP())),
  ('t10',$demo_user, 'ext-1010', 'Uber Eats',         2299,  'USD','Dining Out','want', 0.80, DATEADD('day',-8, CURRENT_TIMESTAMP())),
  ('t11',$demo_user, 'ext-1011', 'Shell Gas',         4321,  'USD','Transport','need', 0.75, DATEADD('day',-12, CURRENT_TIMESTAMP())),
  ('t12',$demo_user, 'ext-1012', 'Kroger',            6789,  'USD','Groceries','need', 0.90, DATEADD('day',-13, CURRENT_TIMESTAMP()));

-- optional example replies (latest wins)
INSERT INTO user_replies (id,transaction_id,user_id,user_label,received_at)
VALUES
  ('r1','t1',$demo_user,'want', DATEADD('minute', 30, (SELECT occurred_at FROM transactions WHERE id='t1'))),
  ('r2','t3',$demo_user,'want', DATEADD('minute', 15, (SELECT occurred_at FROM transactions WHERE id='t3')));

-- optional predictions
INSERT INTO predictions (id,user_id,category,window_start,window_end,probability,annual_savings_hint_usd)
VALUES
  ('p1',$demo_user,'Coffee', DATEADD('hour',-2,CURRENT_TIMESTAMP()), DATEADD('hour',10,CURRENT_TIMESTAMP()), 0.72, 180.00),
  ('p2',$demo_user,'Dining Out', DATEADD('day',0,CURRENT_TIMESTAMP()), DATEADD('day',7,CURRENT_TIMESTAMP()), 0.41, 520.00);