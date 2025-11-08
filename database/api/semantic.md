### Endpoints

    •	GET /feed?user_id=...&limit=...
→ Recent transactions from Snowflake.
	•	GET /stats/category?user_id=...&days=...
→ Category aggregates (count, want/need rate, total cents).
	•	GET /predictions?user_id=...
→ Pulls from PREDICTIONS table in Snowflake.
	•	GET /semantic-search?q=...&user_id=...&limit=...
→ Vector search over transactions.

1.	Embeddings are stored in Snowflake
	•	TRANSACTIONS has:
	•	ITEM_TEXT – e.g. "Starbucks · Coffee"
	•	ITEM_EMBED – vector from SNOWFLAKE.CORTEX.AI_EMBED_768(...)
	•	You successfully backfilled those embeddings.

2.	I built a semantic search function in Python
	•	It:
	•	embeds the query with Cortex (AI_EMBED_768)
	•	fetches candidate rows from TRANSACTIONS
	•	computes cosine similarity in Python
	•	sorts & returns top-k

### Snowflake setup
	•	Database: SNOWFLAKE_LEARNING_DB
	•	Schema: BALANCEIQ_CORE
	•	Tables:
	•	TRANSACTIONS
	•	important columns:
	•	ID
	•	USER_ID
	•	MERCHANT
	•	CATEGORY
	•	ITEM_TEXT – short text like "Starbucks · Coffee"
	•	ITEM_EMBED – VECTOR(FLOAT, 768) from SNOWFLAKE.CORTEX.AI_EMBED_768('e5-base-v2', ITEM_TEXT)
	•	USER_REPLIES
	•	PREDICTIONS

### Embeddings
	•	We use Snowflake Cortex:
	•	Model: e5-base-v2
	•	Function: SNOWFLAKE.CORTEX.AI_EMBED_768('e5-base-v2', <text>)
	•	ITEM_TEXT is backfilled for all existing rows as MERCHANT · CATEGORY.
	•	ITEM_EMBED is populated for all rows with non-null ITEM_TEXT.

### Backend env
	•	.env (ignored in git) lives at:
backend/database/api/.env
	•	Contains:
	•	SNOWFLAKE_ACCOUNT
	•	SNOWFLAKE_USER
	•	SNOWFLAKE_PASSWORD
	•	SNOWFLAKE_ROLE
	•	SNOWFLAKE_WAREHOUSE
	•	SNOWFLAKE_DATABASE
	•	SNOWFLAKE_SCHEMA


```bash
python -m uvicorn database.api.main:app \
  --reload \
  --port 8000 \
  --reload-dir database \
  --reload-exclude '.venv/*'
```

### 3. How semantic search works now

In database/api/main.py (or a helper module):
	1.	Embed the query with Cortex:
    SELECT SNOWFLAKE.CORTEX.AI_EMBED_768('e5-base-v2', :q) AS QV;

    2.	Fetch candidate transactions for that user from Snowflake:
    ```sql
SELECT ID, ITEM_TEXT, ITEM_EMBED
FROM TRANSACTIONS
WHERE USER_ID = :user_id
  AND ITEM_EMBED IS NOT NULL
ORDER BY OCCURRED_AT DESC
LIMIT 200;
```

	3.	Cosine similarity is computed in Python (not in Snowflake, since VECTOR_COSINE_DISTANCE isn’t available):
    def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return 0.0 if na == 0 or nb == 0 else dot / (na * nb)

    4.	Candidates are scored + sorted in Python and the endpoint returns top-k.
    curl -s "http://127.0.0.1:8000/semantic-search?q=coffee&user_id=u_demo_min&limit=5" | jq

    returns:
    [
  { "id": "t99", "item_text": "Starbucks · Coffee", "similarity": 0.88 },
  ...
]