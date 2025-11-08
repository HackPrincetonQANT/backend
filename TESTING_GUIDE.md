# Post-Merge Testing Guide

**Status**: Merged to main - Now verifying deployment
**Date**: 2025-11-08

---

## 📋 Testing Checklist

- [ ] Step 1: Configure Snowflake credentials
- [ ] Step 2: Deploy schema to Snowflake
- [ ] Step 3: Test database connection
- [ ] Step 4: Run categorization script
- [ ] Step 5: Generate embeddings
- [ ] Step 6: Test API endpoints
- [ ] Step 7: Verify end-to-end flow

---

## Step 1: Configure Snowflake Credentials ⚠️ REQUIRED

### Create .env file

```bash
# Copy the example file
cp database/api/.env.example database/api/.env

# Edit with your credentials
nano database/api/.env  # or use your preferred editor
```

### Required credentials:

```env
SNOWFLAKE_ACCOUNT=your-account.snowflakecomputing.com
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ROLE=your_role
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=SNOWFLAKE_LEARNING_DB
SNOWFLAKE_SCHEMA=BALANCEIQ_CORE
```

### Verify credentials format:

- ✅ SNOWFLAKE_ACCOUNT should be `xxx.snowflakecomputing.com` or `xxx.region.cloud`
- ✅ All fields filled in (no placeholders)
- ✅ Password has no special shell characters unescaped

---

## Step 2: Deploy Schema to Snowflake

### Option A: Using Snowflake Web UI (Recommended)

1. **Log into Snowflake** at https://app.snowflake.com

2. **Select your account** and open a worksheet

3. **Run schema deployment** in this order:

```sql
-- 1. Set context
USE DATABASE SNOWFLAKE_LEARNING_DB;
USE SCHEMA BALANCEIQ_CORE;

-- 2. Deploy main schema (purchase_items + views)
-- Copy/paste contents of: database/snowflake/02_purchase_items_schema.sql

-- 3. Deploy backward compatibility layer (TRANSACTIONS, USER_REPLIES, PREDICTIONS)
-- Copy/paste contents of: database/snowflake/04_transactions_view.sql

-- 4. OPTIONAL: Create test table for development
-- Copy/paste contents of: database/create_test_table.sql
```

4. **Verify tables created:**

```sql
-- Check all tables exist
SHOW TABLES;

-- Should see:
-- - purchase_items
-- - USER_REPLIES
-- - PREDICTIONS
-- - purchase_items_test (if you created it)

-- Check views exist
SHOW VIEWS;

-- Should see:
-- - TRANSACTIONS (view)
-- - transactions_for_predictions (view)
-- - category_spending_summary (view)
```

### Option B: Using SnowSQL CLI

```bash
# Connect to Snowflake
snowsql -a your-account -u your-username

# Run schema files
USE DATABASE SNOWFLAKE_LEARNING_DB;
USE SCHEMA BALANCEIQ_CORE;

!source database/snowflake/02_purchase_items_schema.sql
!source database/snowflake/04_transactions_view.sql
!source database/create_test_table.sql  -- Optional
```

---

## Step 3: Test Database Connection

### Quick Python test:

```bash
cd /home/user/backend
python3 -c "
from database.api.db import fetch_all

# Test health check
result = fetch_all('SELECT CURRENT_USER() U, CURRENT_ROLE() R, CURRENT_DATABASE() D, CURRENT_SCHEMA() S')
print('✅ Connection successful!')
print(result)
"
```

**Expected output:**
```
✅ Connection successful!
[{'U': 'YOUR_USER', 'R': 'YOUR_ROLE', 'D': 'SNOWFLAKE_LEARNING_DB', 'S': 'BALANCEIQ_CORE'}]
```

**If it fails:**
- ❌ Check .env file exists at `database/api/.env`
- ❌ Verify credentials are correct
- ❌ Check firewall/network access to Snowflake
- ❌ Ensure database/schema exist

---

## Step 4: Run Categorization Script

### Test with mock data:

```bash
cd src
python categorization-model.py
```

**Expected output:**
```
✅ Categorized 10 products from Amazon
✅ Inserted 10 records to purchase_items_test

Category Summary:
  • Electronics: $320.95 (4 items)
  • Home & Kitchen: $273.98 (3 items)
  • Pet Supplies: $238.00 (2 items)
  • Household Essentials: $19.99 (1 items)
```

**If it fails:**

### Error: "ModuleNotFoundError: No module named 'dedalus_labs'"
```bash
pip install dedalus-labs python-dotenv
```

### Error: "Table 'PURCHASE_ITEMS_TEST' does not exist"
```sql
-- Run in Snowflake:
USE DATABASE SNOWFLAKE_LEARNING_DB;
USE SCHEMA BALANCEIQ_CORE;
-- Then execute: database/create_test_table.sql
```

### Error: "DEDALUS_API_KEY not found"
```bash
# Add to database/api/.env:
DEDALUS_API_KEY=your_api_key
```

### Verify data was inserted:

```sql
-- In Snowflake, run:
SELECT COUNT(*) as total_items FROM purchase_items_test;

-- Should return 10 (or more if you ran multiple times)

SELECT
  category,
  COUNT(*) as item_count,
  SUM(price * qty) as total_spend
FROM purchase_items_test
GROUP BY category
ORDER BY total_spend DESC;
```

---

## Step 5: Generate Embeddings

### Run embedding generation:

```sql
-- In Snowflake, execute:
USE DATABASE SNOWFLAKE_LEARNING_DB;
USE SCHEMA BALANCEIQ_CORE;

-- Copy/paste contents of: database/snowflake/03_generate_embeddings.sql
```

**The script will:**
- Generate 768-dimensional embeddings for all items with `item_text`
- Use Snowflake Cortex AI (`e5-base-v2` model)
- Skip items that already have embeddings

### Verify embeddings generated:

```sql
-- Check how many items have embeddings
SELECT
  COUNT(*) as total_items,
  COUNT(item_embed) as items_with_embeddings,
  (COUNT(item_embed)::FLOAT / COUNT(*)::FLOAT * 100) as completion_percentage
FROM purchase_items_test;

-- Expected: 100% completion

-- View sample embedding
SELECT
  item_name,
  item_text,
  VECTOR_L2_DISTANCE(item_embed, item_embed) as should_be_zero
FROM purchase_items_test
WHERE item_embed IS NOT NULL
LIMIT 5;
```

---

## Step 6: Test API Endpoints

### Start the FastAPI server:

```bash
cd /home/user/backend/database/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**In a separate terminal, test endpoints:**

### 1. Health Check
```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{"U": "YOUR_USER", "R": "YOUR_ROLE", "W": "YOUR_WAREHOUSE", "D": "SNOWFLAKE_LEARNING_DB", "S": "BALANCEIQ_CORE"}
```

### 2. Transaction Feed (uses TRANSACTIONS view)
```bash
curl "http://localhost:8000/feed?user_id=test_user_001&limit=10"
```

**Expected:** Array of transactions (empty if no data yet)

### 3. Category Stats (uses TRANSACTIONS view)
```bash
curl "http://localhost:8000/stats/category?user_id=test_user_001&days=30"
```

**Expected:** Category spending statistics

### 4. Semantic Search (uses item_embed)
```bash
curl "http://localhost:8000/semantic-search?q=smart+home&user_id=test_user_001&limit=5"
```

**Expected:** Similar items ranked by semantic similarity

### 5. Insert Test Transaction
```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test_txn_001",
    "user_id": "test_user_001",
    "transaction_id": "amzn_test_001",
    "merchant": "Amazon",
    "amount_cents": 2999,
    "currency": "USD",
    "category": "Electronics",
    "need_or_want": "want",
    "confidence": 0.95,
    "occurred_at": "2024-11-08T12:00:00Z"
  }'
```

**Expected:**
```json
{"status": "ok", "id": "test_txn_001"}
```

---

## Step 7: Verify End-to-End Flow

### Complete workflow test:

```bash
# 1. Run categorization (creates purchase_items)
cd /home/user/backend/src
python categorization-model.py

# 2. Generate embeddings (populates item_embed)
# Run in Snowflake: database/snowflake/03_generate_embeddings.sql

# 3. Query via TRANSACTIONS view
curl "http://localhost:8000/feed?user_id=test_user_001&limit=10"

# 4. Test semantic search
curl "http://localhost:8000/semantic-search?q=electronics&user_id=test_user_001&limit=5"

# 5. Verify in database
```

### Verify in Snowflake:

```sql
-- 1. Check purchase_items has data
SELECT COUNT(*) FROM purchase_items_test;

-- 2. Check TRANSACTIONS view works
SELECT COUNT(*) FROM TRANSACTIONS;

-- 3. Verify embeddings exist
SELECT COUNT(*) FROM purchase_items_test WHERE item_embed IS NOT NULL;

-- 4. Test semantic search directly
SELECT
  item_name,
  category,
  VECTOR_L2_DISTANCE(
    item_embed,
    SNOWFLAKE.CORTEX.AI_EMBED_768('e5-base-v2', 'smart home device')
  ) as distance
FROM purchase_items_test
WHERE item_embed IS NOT NULL
ORDER BY distance ASC
LIMIT 5;
```

---

## 🎯 Success Criteria

### All tests pass when:

- ✅ Database connection successful
- ✅ All tables created (purchase_items, USER_REPLIES, PREDICTIONS)
- ✅ All views created (TRANSACTIONS, transactions_for_predictions, category_spending_summary)
- ✅ Categorization script runs without errors
- ✅ Data inserted into purchase_items_test
- ✅ Embeddings generated (item_embed populated)
- ✅ API health check returns 200
- ✅ API endpoints return valid data
- ✅ TRANSACTIONS view aggregates purchase_items correctly
- ✅ Semantic search returns relevant results

---

## 🐛 Common Issues & Solutions

### Issue: "Authentication failed"
**Solution:** Check SNOWFLAKE_PASSWORD in .env has no special characters unescaped

### Issue: "Database does not exist"
**Solution:** Create database first:
```sql
CREATE DATABASE IF NOT EXISTS SNOWFLAKE_LEARNING_DB;
USE DATABASE SNOWFLAKE_LEARNING_DB;
CREATE SCHEMA IF NOT EXISTS BALANCEIQ_CORE;
```

### Issue: "Table already exists" when running schema
**Solution:** Use `CREATE OR REPLACE` or drop existing tables:
```sql
DROP TABLE IF EXISTS purchase_items CASCADE;
```

### Issue: "Embeddings not generating"
**Solution:** Check Snowflake Cortex AI is enabled for your account. Contact Snowflake support if needed.

### Issue: "API returns 500 error"
**Solution:** Check API logs:
```bash
# Look for errors in terminal where uvicorn is running
# Common: missing .env file, wrong database name
```

---

## 📊 Performance Benchmarks

After testing, you should see:

| Metric | Target | Your Result |
|--------|--------|-------------|
| Categorization time (10 items) | ~1-2 seconds | _________ |
| Database insert time | < 500ms | _________ |
| Embedding generation (10 items) | ~2-3 seconds | _________ |
| API health check latency | < 100ms | _________ |
| Semantic search latency | < 500ms | _________ |

---

## ✅ Final Verification

Run this comprehensive check in Snowflake:

```sql
-- Comprehensive system check
WITH system_check AS (
  SELECT
    (SELECT COUNT(*) FROM purchase_items_test) as items_count,
    (SELECT COUNT(*) FROM purchase_items_test WHERE item_embed IS NOT NULL) as embeddings_count,
    (SELECT COUNT(DISTINCT category) FROM purchase_items_test) as categories_count,
    (SELECT COUNT(*) FROM TRANSACTIONS) as transactions_count,
    (SELECT COUNT(*) FROM USER_REPLIES) as replies_count,
    (SELECT COUNT(*) FROM PREDICTIONS) as predictions_count
)
SELECT
  items_count,
  embeddings_count,
  ROUND((embeddings_count::FLOAT / NULLIF(items_count, 0)::FLOAT * 100), 2) as embedding_percentage,
  categories_count,
  transactions_count,
  replies_count,
  predictions_count,
  CASE
    WHEN items_count > 0 AND embeddings_count = items_count THEN '✅ PASS'
    ELSE '⚠️  INCOMPLETE'
  END as status
FROM system_check;
```

---

**Next Steps After All Tests Pass:**

1. ✅ Document any custom configurations
2. ✅ Set up monitoring/alerts
3. ✅ Plan migration from test table to production
4. ✅ Consider implementing the "Future Cleanup" tasks from docs/todo.md

---

**Need Help?**
- Review `docs/todo.md` for detailed architecture
- Check `docs/unified-architecture.md` for schema details
- Review SQL files for exact table definitions
