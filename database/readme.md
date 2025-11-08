### Endpoints

GET
/health
Returns current Snowflake connection info

GET
/feed?user_id=u_demo_min&limit=5
Latest transactions for user


GET
/stats/category?user_id=u_demo_min&days=30
Spending stats per category

GET
/predictions?user_id=u_demo_min
Prediction results from ML pipeline

POST
/transactions
Upsert a transaction

POST
/reply
Upsert a user reply label (“need”/“want”)


### curl -s http://127.0.0.1:8000/health | jq
```bash
{
  "U": "NGSTEPHEN1",
  "R": "ACCOUNTADMIN",
  "W": "COMPUTE_WH",
  "D": "SNOWFLAKE_LEARNING_DB",
  "S": "BALANCEIQ_CORE"
}
Feed
curl -s "http://127.0.0.1:8000/feed?user_id=u_demo_min&limit=5" | jq

Category Stats
curl -s "http://127.0.0.1:8000/stats/category?user_id=u_demo_min&days=30" | jq

Predictions
curl -s "http://127.0.0.1:8000/predictions?user_id=u_demo_min" | jq

Insert / Update a Transaction
curl -s -X POST http://127.0.0.1:8000/transactions \
  -H "content-type: application/json" \
  -d @samples/txn_sample.json | jq
```

```json
{
  "id": "t_demo",
  "user_id": "u_demo_min",
  "transaction_id": "ext-demo",
  "merchant": "Starbucks",
  "amount_cents": 525,
  "currency": "USD",
  "category": "Coffee",
  "need_or_want": "want",
  "confidence": 0.9,
  "occurred_at": "2025-11-07T13:05:00-08:00"
}
```

### checklist
	•	Tables exist in SNOWFLAKE_LEARNING_DB.BALANCEIQ_CORE
	•	Seed data loaded
	•	/feed, /stats/category, /predictions return JSON
	•	/transactions and /reply POST work
	•	.env.example + README included
	•	Sample JSON outputs saved under samples/
