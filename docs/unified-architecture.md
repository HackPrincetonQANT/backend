# Unified Architecture: Categorization + ML Predictions

## Overview

This document describes the unified data architecture that serves both **AI-powered categorization** (via Dedalus Labs) and **ML prediction models** for user spending insights.

## Data Flow

```
┌─────────────────┐
│  Purchase Data  │
│  (Knot/Amazon)  │
└────────┬────────┘
         │
         ▼
┌──────────────────────────────────────┐
│  Categorization Script               │
│  (Dedalus AI - Batch)                │
│  src/categorization-model.py         │
│  - AI categorization                 │
│  - Database insertion                │
│  - Auto-generate embeddings ✨       │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│  purchase_items Table                │
│  (Single Source of Truth)            │
│  - Item-level detail                 │
│  - AI categorization                 │
│  - ML embeddings (auto-generated)    │
└────────┬─────────────────────────────┘
         │
         ├──────────────────┬─────────────────┐
         │                  │                 │
         ▼                  ▼                 ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────┐
│  Prediction      │  │  Semantic    │  │  Weekly      │
│  Model           │  │  Search      │  │  Insights    │
│  (ML Analysis)   │  │  (Cortex)    │  │  (2x/week)   │
└──────────────────┘  └──────────────┘  └──────────────┘
```

## Database Schema

### Main Table: `purchase_items`

**Purpose**: Single source of truth for all categorized purchases
**Granularity**: Item-level (multiple items per purchase)

```sql
CREATE TABLE purchase_items (
  -- Identity
  item_id            STRING PRIMARY KEY,
  purchase_id        STRING,              -- Groups items from same purchase
  user_id            STRING,

  -- Purchase Details
  merchant           STRING,
  ts                 TIMESTAMP_TZ,

  -- Item Information
  item_name          STRING,              -- Original item name
  item_text          STRING,              -- "merchant · category · item_name"

  -- AI Categorization (from Dedalus)
  category           STRING,              -- Main category
  subcategory        STRING,              -- Optional detail

  -- Financial
  price              NUMBER(12,2),
  qty                NUMBER(10,2),

  -- Need/Want Classification
  detected_needwant  STRING,              -- AI: 'need' | 'want'
  user_needwant      STRING,              -- User override

  -- AI Metadata
  reason             STRING,              -- Why this category
  confidence         FLOAT,               -- 0..1

  -- ML/Embeddings
  item_embed         VECTOR(FLOAT, 768),  -- Cortex embedding

  -- Status
  status             STRING DEFAULT 'active',
  created_at         TIMESTAMP_TZ
);
```

### Helper Views

#### 1. `transactions_for_predictions`

Aggregates item-level data to transaction-level for prediction model compatibility.

```sql
SELECT
  purchase_id AS id,
  user_id,
  merchant,
  SUM(price * qty) AS amount_cents,
  category,
  need_or_want,
  AVG(confidence) AS confidence,
  ts AS occurred_at,
  LISTAGG(item_name, ' · ') AS item_text,
  item_embed
FROM purchase_items
GROUP BY purchase_id, user_id, ...
```

#### 2. `category_spending_summary`

Pre-aggregated spending by category for fast twice-weekly analysis.

```sql
SELECT
  user_id,
  category,
  subcategory,
  week_start,
  COUNT(DISTINCT purchase_id) AS purchase_count,
  SUM(price * qty) AS total_spend,
  SUM(need_spend) AS need_spend,
  SUM(want_spend) AS want_spend
FROM purchase_items
GROUP BY user_id, category, subcategory, week_start
```

## Key Design Decisions

### Why Item-Level Granularity?

**Better ML Predictions**:
- Can learn "user buys coffee 3x/week at $5 each" vs just "coffee: $15/week"
- Subcategories provide detailed spending patterns
- Individual items enable better semantic search

**Flexibility**:
- Easy to aggregate up to transaction/weekly/monthly levels
- Can analyze individual purchasing decisions
- Supports detailed insights ("You bought 5 lattes this week")

### Why Single Table vs Multiple?

**Avoids Data Duplication**:
- No sync issues between TRANSACTIONS and purchase_items
- Single update point for corrections
- Views provide different "lenses" on same data

**Performance**:
- Clustered by (user_id, ts) for fast queries
- Pre-aggregated views for common patterns
- Embeddings stored once, used everywhere

## Categorization Process

### 1. Data Collection
- Source: Knot API / Amazon data
- Format: JSON with transactions → products

### 2. AI Categorization (Dedalus Labs)
- **Batch processing**: All products in single API call
- **Smart prompting**: AI ensures consistent categories
- **Output**: category, subcategory, confidence, reason

### 3. Data Storage
```python
# Creates normalized item_text
item_text = f"{merchant} · {category} · {subcategory} · {item_name}"

# Batch insert to purchase_items_test or purchase_items
INSERT INTO purchase_items_test (
  item_id, purchase_id, user_id,
  item_name, item_text,
  category, subcategory,
  price, qty, reason, confidence, ...
)
```

### 4. Embedding Generation (Automatic!)
```python
# ✨ NEW: Embeddings are automatically generated after insertion
# by categorization-model.py using generate_embeddings_batch()

# Batch generate embeddings for all newly inserted items
UPDATE purchase_items_test
SET item_embed = SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', item_text)
WHERE item_id IN ('item1', 'item2', ...)

# This happens automatically - no manual SQL script needed!
# See src/categorization-model.py: generate_embeddings_batch()
```

**Note**: Manual embedding generation script still available at `database/snowflake/03_generate_embeddings.sql` for backup/recovery purposes.

## Prediction Model Integration

### Query Patterns

**Weekly Category Spending**:
```python
from database.api.prediction_queries import SQL_GET_CATEGORY_SPENDING

results = fetch_all(SQL_GET_CATEGORY_SPENDING, {
    'user_id': 'user_123',
    'weeks': 8
})
```

**Overspending Detection**:
```python
from database.api.prediction_queries import SQL_FIND_OVERSPENDING

overspending = fetch_all(SQL_FIND_OVERSPENDING, {'user_id': 'user_123'})
# Returns categories with z-score > 1.5
```

**Cancellation Candidates**:
```python
from database.api.prediction_queries import SQL_CANCELLATION_CANDIDATES

candidates = fetch_all(SQL_CANCELLATION_CANDIDATES, {'user_id': 'user_123'})
# Returns recurring "wants" with high spend
```

### Semantic Search (Alternative Suggestions)

```python
from database.api.semantic import search_similar_items

# Find similar items for cost-saving alternatives
similar = search_similar_items(
    query="starbucks coffee",
    user_id="user_123",
    limit=5
)
```

## Twice-Weekly Insights

The prediction model runs every 3-4 days to generate insights:

1. **Spending Patterns**: Analyze category_spending_summary
2. **Overspending Alerts**: Compare current week vs historical average
3. **Cancellation Suggestions**: Identify recurring wants
4. **Alternative Recommendations**: Semantic search for cheaper options

## File Structure

```
backend/
├── database/
│   ├── snowflake/
│   │   ├── 02_purchase_items_schema.sql    # Main schema + views
│   │   └── 03_generate_embeddings.sql      # Embedding generation (backup/optional)
│   ├── create_test_table.sql               # Test table (same schema)
│   └── api/
│       ├── db.py                           # Connection + execute_many()
│       ├── queries.py                      # Original queries (deprecated)
│       ├── prediction_queries.py           # ML prediction queries
│       └── semantic.py                     # Semantic search helper
├── src/
│   └── categorization-model.py             # Dedalus AI categorization + embeddings
└── docs/
    └── unified-architecture.md             # This file
```

## Migration Guide

### From TRANSACTIONS to purchase_items

If you have existing code using `TRANSACTIONS` table:

**Option 1**: Use the view
```python
# Old code
SELECT * FROM TRANSACTIONS WHERE user_id = ?

# New code (no change needed!)
SELECT * FROM transactions_for_predictions WHERE user_id = ?
```

**Option 2**: Query purchase_items directly for better detail
```python
# Get item-level detail instead of transaction-level
SELECT * FROM purchase_items WHERE user_id = ?
```

## Security & Privacy

- ✅ All queries use parameterized binding (no SQL injection)
- ✅ User data isolated by user_id
- ✅ Credentials stored in .env (not in code)
- ✅ Test table for development (purchase_items_test)
- ✅ Production table protected (purchase_items)

## Performance Optimization

**Clustering**: `CLUSTER BY (user_id, ts)` enables partition pruning
**Views**: Pre-aggregated for common patterns (2x/week analysis)
**Embeddings**: Generated once, reused for all searches
**Batch Inserts**: `execute_many()` for efficient writes

## Next Steps

1. ✅ Create tables: Run `database/snowflake/02_purchase_items_schema.sql`
2. ✅ Create test table: Run `database/create_test_table.sql`
3. ✅ Test categorization: `python src/categorization-model.py` (auto-generates embeddings!)
4. ⏳ Update prediction model to use new queries
5. ⏳ Validate insights accuracy

**Note**: Step 4 (Generate embeddings) is now automatic! The categorization script handles it.

## Support

For questions about:
- **Schema design**: See this doc
- **Categorization**: See `src/categorization-model.py`
- **Predictions**: See `database/api/prediction_queries.py`
- **Semantic search**: See `database/api/semantic.py`
