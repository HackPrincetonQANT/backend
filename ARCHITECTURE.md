# Real-Time Spending Coach - Unified Architecture

**Last Updated:** 2025-11-08
**Status:** In Development (HackPrinceton MVP)
**Main API:** Flask (src/main.py) on port 8000

---

## Table of Contents
1. [System Overview](#system-overview)
2. [End-to-End Data Flow](#end-to-end-data-flow)
3. [Module Boundaries](#module-boundaries)
4. [Data Contracts](#data-contracts)
5. [Integration Points](#integration-points)
6. [Team Responsibilities](#team-responsibilities)
7. [Database Schema](#database-schema)
8. [Deployment & Setup](#deployment--setup)

---

## System Overview

### Architecture Diagram
```
┌─────────────┐
│ User makes  │
│  purchase   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                      KNOT API                                │
│  (External: captures real-time transaction data)            │
└──────────────────────────┬──────────────────────────────────┘
                           │ webhook
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   FLASK BACKEND (Port 8000)                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  POST /api/knot/webhooks                               │ │
│  │  • Receives transaction from Knot                      │ │
│  │  • Calls Classification Agent (Dedalus)                │ │
│  │  • Stores result in Database                           │ │
│  │  • Triggers Photon notification if WANT                │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
│  ┌────────────────▼───────────────────────────────────────┐ │
│  │  Classification Module (classification.py)             │ │
│  │  • Calls Dedalus MCP Server                            │ │
│  │  • Returns: {need_or_want, category, confidence}       │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
│  ┌────────────────▼───────────────────────────────────────┐ │
│  │  Database Module (database/api/)                       │ │
│  │  • insert_transaction(...)                             │ │
│  │  • insert_user_reply(...)                              │ │
│  │  • get_user_feed(...)                                  │ │
│  │  • Uses Snowflake or SQLite                            │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
│  ┌────────────────▼───────────────────────────────────────┐ │
│  │  Photon Module (photon.py)                             │ │
│  │  • send_message(user_id, text)                         │ │
│  │  • Handles iMessage sending                            │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      PHOTON API                              │
│  Sends iMessage: "Was this coffee a NEED or WANT?"          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  User replies via iMessage: "WANT"                          │
└──────────────────────────┬──────────────────────────────────┘
                           │ webhook
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              FLASK: POST /api/photon/reply                   │
│  • Updates database with user label                         │
│  • Calls Prediction Engine                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Prediction Module (prediction.py)                          │
│  • Calls Dedalus MCP → DigitalOcean AI / LLM                │
│  • Estimates: next_purchase_eta, yearly_savings             │
│  • Stores prediction in database                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  FLASK: Triggers Photon notification                         │
│  "You buy coffee weekly. Skip today = save $273/year."      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND (Next.js/React)                   │
│  GET /user/<id>/summary                                      │
│  • Displays recent transactions                             │
│  • Shows predictions and savings                            │
│  • Demo visualization                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## End-to-End Data Flow

### Flow 1: Transaction Classification (Automated)
```
1. User makes purchase at Starbucks ($5.25)
   ↓
2. Knot captures transaction
   ↓
3. Knot sends webhook → POST /api/knot/webhooks
   {
     "event": "TRANSACTION_CREATED",
     "transaction_id": "ext-12345",
     "merchant": "Starbucks",
     "amount": 5.25,
     "currency": "USD",
     "user_id": "u_demo"
   }
   ↓
4. Flask backend calls classification.classify_transaction()
   ↓
5. Classification module calls Dedalus MCP server with prompt:
   "Classify this transaction: Starbucks, $5.25.
    Return: {need_or_want, category, confidence, reasoning}"
   ↓
6. Dedalus returns:
   {
     "need_or_want": "want",
     "category": "Coffee",
     "confidence": 0.85,
     "reasoning": "Daily coffee is discretionary spending"
   }
   ↓
7. Backend calls database.insert_transaction()
   Stores: transaction + classification + timestamp
   ↓
8. IF need_or_want == "want":
      photon.send_message(user_id, "Was that $5.25 coffee a NEED or WANT?")
   ELSE:
      Skip notification (essential purchase)
```

### Flow 2: User Feedback Loop
```
1. User receives iMessage notification
   ↓
2. User replies: "NEED" or "WANT"
   ↓
3. Photon sends webhook → POST /api/photon/reply
   {
     "user_id": "u_demo",
     "transaction_id": "t_12345",
     "message": "NEED"
   }
   ↓
4. Backend extracts label, calls database.insert_user_reply()
   ↓
5. Backend calls prediction.generate_prediction(user_id, transaction_id)
   ↓
6. Prediction module:
   a. Fetches user's transaction history from database
   b. Calls Dedalus MCP → DigitalOcean AI model
   c. Prompt: "User buys coffee 3x/week at $5.25. Predict next purchase and annual savings."
   d. Gets response: {next_eta: "2 days", yearly_savings: "$273"}
   ↓
7. Store prediction in database
   ↓
8. Send preemptive nudge:
   photon.send_message(user_id, "You typically buy coffee on Friday.
                       Skip this one = $273/year saved!")
```

### Flow 3: Frontend Dashboard
```
1. Frontend loads → GET /user/u_demo/summary
   ↓
2. Flask backend calls:
   - database.get_user_feed(user_id, limit=20)
   - database.get_predictions(user_id)
   ↓
3. Returns:
   {
     "recent_transactions": [
       {
         "id": "t_12345",
         "merchant": "Starbucks",
         "amount": 5.25,
         "need_or_want": "want",
         "user_label": "need",  // User corrected AI
         "category": "Coffee",
         "occurred_at": "2025-11-08T10:30:00Z"
       },
       ...
     ],
     "predictions": [
       {
         "category": "Coffee",
         "next_eta": "2 days",
         "yearly_savings": 273.00,
         "probability": 0.78
       }
     ]
   }
   ↓
4. Frontend displays summary with visualizations
```

---

## Module Boundaries

### 1. Flask Backend (src/main.py)
**Responsibilities:**
- Main HTTP server (port 8000)
- Route handling and request validation
- Orchestration of business logic
- Webhook verification (Knot, Photon)
- CORS and authentication middleware
- Logging and error handling

**What it DOES NOT do:**
- Direct database queries (delegates to database module)
- Direct ML inference (delegates to classification/prediction modules)
- Direct iMessage sending (delegates to photon module)

### 2. Database Module (database/api/)
**Responsibilities:**
- Database connection management (Snowflake/SQLite)
- CRUD operations
- Data validation (Pydantic models)
- Query construction

**Files:**
- `db.py` - Connection pooling, execute/fetch functions
- `models.py` - Pydantic schemas (TransactionInsert, UserReply, etc.)
- `queries.py` - SQL query strings
- `__init__.py` - Public API exports

**Public Interface (what Flask imports):**
```python
from database.api import (
    insert_transaction,
    insert_user_reply,
    insert_prediction,
    get_user_feed,
    get_user_stats,
    get_predictions
)
```

**NOT a separate API server** - Just a Python module that Flask imports.

### 3. Classification Module (src/classification.py)
**Responsibilities:**
- Interface with Dedalus MCP server
- Transaction classification logic
- Prompt engineering for LLM
- Response parsing and validation

**Public Interface:**
```python
def classify_transaction(
    merchant: str,
    amount: float,
    currency: str,
    user_id: str
) -> dict:
    """
    Returns:
    {
        "need_or_want": "want",
        "category": "Coffee",
        "confidence": 0.85,
        "reasoning": "..."
    }
    """
```

### 4. Prediction Module (src/prediction.py)
**Responsibilities:**
- Fetch user transaction history
- Call Dedalus MCP → DigitalOcean AI model
- Generate predictions (next purchase ETA, savings estimate)
- Store predictions in database

**Public Interface:**
```python
def generate_prediction(user_id: str, transaction_id: str) -> dict:
    """
    Returns:
    {
        "next_eta": "2 days",
        "yearly_savings": 273.00,
        "probability": 0.78,
        "category": "Coffee"
    }
    """
```

### 5. Photon Module (src/photon.py)
**Responsibilities:**
- Send iMessages via Photon API
- Handle Photon webhook verification
- Message formatting

**Public Interface:**
```python
def send_message(user_id: str, text: str) -> bool:
    """Send iMessage to user. Returns success status."""

def parse_reply(webhook_data: dict) -> dict:
    """Extract user reply from Photon webhook."""
```

---

## Data Contracts

### Transaction Object (from Knot → Database)
```python
{
    "id": str,                    # Internal ID (auto-generated)
    "user_id": str,               # "u_demo"
    "transaction_id": str,        # External Knot ID
    "merchant": str,              # "Starbucks"
    "amount_cents": int,          # 525 (stored as cents)
    "currency": str,              # "USD"
    "category": str,              # "Coffee" (from classification)
    "need_or_want": str,          # "need" | "want"
    "confidence": float,          # 0.0 - 1.0
    "occurred_at": str,           # ISO8601 timestamp
    "created_at": str             # Auto-generated
}
```

### Classification Response (Dedalus → Backend)
```python
{
    "need_or_want": str,          # "need" | "want"
    "category": str,              # "Coffee", "Groceries", "Entertainment"
    "confidence": float,          # 0.0 - 1.0
    "reasoning": str              # Human-readable explanation
}
```

### User Reply (Photon → Database)
```python
{
    "id": str,                    # Auto-generated
    "transaction_id": str,        # Links to transaction
    "user_id": str,               # "u_demo"
    "user_label": str,            # "need" | "want"
    "received_at": str            # ISO8601 timestamp
}
```

### Prediction Object (Prediction Engine → Database)
```python
{
    "id": str,                    # Auto-generated
    "user_id": str,               # "u_demo"
    "category": str,              # "Coffee"
    "next_eta": str,              # "2 days", "1 week"
    "yearly_savings": float,      # 273.00 (dollars)
    "probability": float,         # 0.0 - 1.0
    "created_at": str             # Auto-generated
}
```

### Frontend Summary Response
```python
{
    "recent_transactions": [
        {
            "id": str,
            "merchant": str,
            "amount": float,          # In dollars (converted from cents)
            "category": str,
            "need_or_want": str,
            "user_label": str | null, # User's correction if provided
            "occurred_at": str
        }
    ],
    "predictions": [
        {
            "category": str,
            "next_eta": str,
            "yearly_savings": float,
            "probability": float
        }
    ],
    "stats_30d": {
        "total_spent": float,
        "want_count": int,
        "need_count": int,
        "categories": [
            {
                "name": str,
                "total": float,
                "txn_count": int,
                "want_rate": float
            }
        ]
    }
}
```

---

## Integration Points

### 1. Knot API → Flask Backend

**Endpoint:** `POST /api/knot/webhooks`

**Request (from Knot):**
```json
{
  "event": "TRANSACTION_CREATED",
  "session_id": "sess_abc123",
  "transaction": {
    "id": "ext-12345",
    "merchant": "Starbucks",
    "amount": 5.25,
    "currency": "USD",
    "timestamp": "2025-11-08T10:30:00Z"
  },
  "user": {
    "external_user_id": "u_demo"
  }
}
```

**Backend Action:**
```python
1. Verify webhook signature (HMAC-SHA256)
2. Extract transaction data
3. Call classify_transaction(merchant, amount, currency, user_id)
4. Call insert_transaction(transaction_data)
5. If classification.need_or_want == "want":
      send_photon_message(user_id, "Was this a NEED or WANT?")
6. Return 200 OK
```

**Response to Knot:**
```json
{
  "success": true
}
```

---

### 2. Flask Backend → Dedalus MCP (Classification)

**Function Call:** `classification.classify_transaction(...)`

**Request to Dedalus:**
```python
# Dedalus MCP server call (exact format TBD - depends on MCP setup)
{
  "tool": "llm_classify",
  "prompt": """
    Classify this transaction:
    - Merchant: Starbucks
    - Amount: $5.25
    - Context: User's daily purchase pattern

    Return JSON:
    {
      "need_or_want": "need" or "want",
      "category": "category name",
      "confidence": 0.0-1.0,
      "reasoning": "brief explanation"
    }
  """,
  "model": "claude-3-5-sonnet-20241022"
}
```

**Response from Dedalus:**
```json
{
  "need_or_want": "want",
  "category": "Coffee",
  "confidence": 0.85,
  "reasoning": "Daily coffee purchases are typically discretionary"
}
```

---

### 3. Flask Backend → Database Module

**Function Calls:**

```python
# Insert transaction with classification
from database.api import insert_transaction

insert_transaction({
    "id": "t_12345",
    "user_id": "u_demo",
    "transaction_id": "ext-12345",
    "merchant": "Starbucks",
    "amount_cents": 525,
    "currency": "USD",
    "category": "Coffee",
    "need_or_want": "want",
    "confidence": 0.85,
    "occurred_at": "2025-11-08T10:30:00Z"
})

# Insert user reply
from database.api import insert_user_reply

insert_user_reply({
    "id": "r_456",
    "transaction_id": "t_12345",
    "user_id": "u_demo",
    "user_label": "need",
    "received_at": "2025-11-08T10:35:00Z"
})

# Get user feed
from database.api import get_user_feed

transactions = get_user_feed(user_id="u_demo", limit=20)
# Returns: List[dict] with transaction objects
```

---

### 4. Flask Backend → Photon API

**Function Call:** `photon.send_message(...)`

**Request to Photon:**
```python
import requests

def send_message(user_id: str, text: str) -> bool:
    response = requests.post(
        "https://api.photon.com/v1/messages",  # TBD: actual endpoint
        headers={
            "Authorization": f"Bearer {PHOTON_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "recipient_id": user_id,
            "message": text,
            "platform": "imessage"
        }
    )
    return response.status_code == 200
```

**Photon Webhook → Flask:**

**Endpoint:** `POST /api/photon/reply`

**Request (from Photon):**
```json
{
  "user_id": "u_demo",
  "message": "NEED",
  "timestamp": "2025-11-08T10:35:00Z",
  "context": {
    "transaction_id": "t_12345"  // If we sent metadata
  }
}
```

---

### 5. Flask Backend → Prediction Engine

**Function Call:** `prediction.generate_prediction(...)`

**Internal Flow:**
```python
def generate_prediction(user_id: str, transaction_id: str) -> dict:
    # 1. Fetch transaction history
    history = get_user_feed(user_id, limit=100)

    # 2. Find patterns (category, frequency, amount)
    coffee_txns = [t for t in history if t['category'] == 'Coffee']

    # 3. Call Dedalus MCP → DigitalOcean AI
    prompt = f"""
    User transaction pattern:
    - {len(coffee_txns)} coffee purchases in last 30 days
    - Average: ${sum(t['amount_cents'] for t in coffee_txns)/len(coffee_txns)/100}
    - Frequency: {len(coffee_txns)/30} times per week

    Predict:
    1. When will they likely buy coffee again?
    2. Annual savings if they skip once per week?

    Return JSON: {{next_eta, yearly_savings, probability}}
    """

    result = dedalus_mcp_call(prompt)

    # 4. Store prediction
    insert_prediction({
        "user_id": user_id,
        "category": "Coffee",
        "next_eta": result['next_eta'],
        "yearly_savings": result['yearly_savings'],
        "probability": result['probability']
    })

    return result
```

---

### 6. Frontend → Flask Backend

**Endpoint:** `GET /user/<user_id>/summary`

**Request:**
```
GET /user/u_demo/summary?days=30
```

**Response:**
```json
{
  "recent_transactions": [
    {
      "id": "t_12345",
      "merchant": "Starbucks",
      "amount": 5.25,
      "category": "Coffee",
      "need_or_want": "want",
      "user_label": "need",
      "occurred_at": "2025-11-08T10:30:00Z"
    }
  ],
  "predictions": [
    {
      "category": "Coffee",
      "next_eta": "2 days",
      "yearly_savings": 273.00,
      "probability": 0.78
    }
  ],
  "stats_30d": {
    "total_spent": 450.00,
    "want_count": 15,
    "need_count": 8,
    "categories": [
      {
        "name": "Coffee",
        "total": 157.50,
        "txn_count": 30,
        "want_rate": 0.9
      }
    ]
  }
}
```

---

## Team Responsibilities

### Backend Team (Tony + You)

**Your Tasks:**

1. **Knot Integration** (Already done in src/main.py:65-202)
   - ✅ Session creation
   - ✅ Webhook verification
   - ⏳ Hook up classification call

2. **Classification Module** (src/classification.py) - **PRIORITY**
   - Create Dedalus MCP client
   - Implement `classify_transaction()` function
   - Test with mock transactions
   - **Deliverable:** Function that takes (merchant, amount) and returns classification

3. **Prediction Module** (src/prediction.py)
   - Create Dedalus MCP client for predictions
   - Implement `generate_prediction()` function
   - Call DigitalOcean AI or use function calling
   - **Deliverable:** Function that analyzes history and predicts next purchase

4. **Photon Integration** (src/photon.py)
   - Implement `send_message()` function
   - Implement webhook handler at `POST /api/photon/reply`
   - Parse user replies ("NEED" vs "WANT")
   - **Deliverable:** Working iMessage send/receive

5. **Main Route Updates** (src/main.py)
   - Wire classification into `/api/knot/webhooks`
   - Implement `GET /user/<user_id>/summary`
   - Add error handling and logging

### Database Team (Nguyen - Already Merged)

**Tasks:**

1. **Refactor database/api to be library module** (NOT a server)
   - Remove FastAPI app
   - Export functions: insert_transaction, get_user_feed, etc.
   - Keep db.py, models.py, queries.py

2. **Test database functions independently**
   - Create sample data
   - Verify Snowflake/SQLite connection
   - Test CRUD operations

3. **Add missing functions**
   - `insert_prediction()`
   - `get_predictions(user_id)`
   - `get_user_stats(user_id, days=30)`

**Deliverable:** Python module that Flask can import

### Frontend Team (Separate Repo)

**Integration Requirements:**

1. **Call Flask API:**
   ```javascript
   const response = await fetch('http://localhost:8000/user/u_demo/summary?days=30')
   const data = await response.json()
   ```

2. **Display:**
   - Recent transactions table (show AI classification vs user label)
   - Predictions widget (next purchase, savings estimate)
   - Category breakdown chart

3. **Knot Session (if applicable):**
   - Call `POST /api/knot/create-session` to get session token
   - Embed Knot widget for account linking

**Contract:** Frontend only needs to know the summary endpoint format (defined above)

---

## Database Schema

See `database/snowflake/01_schema_tables.sql` for full DDL.

**Core Tables:**

```sql
-- Transactions (from Knot + AI classification)
CREATE TABLE TRANSACTIONS (
    ID VARCHAR PRIMARY KEY,
    USER_ID VARCHAR NOT NULL,
    TRANSACTION_ID VARCHAR,        -- External Knot ID
    MERCHANT VARCHAR,
    AMOUNT_CENTS INTEGER,
    CURRENCY VARCHAR(6),
    CATEGORY VARCHAR,              -- From AI classification
    NEED_OR_WANT VARCHAR(4),       -- "need" or "want"
    CONFIDENCE FLOAT,              -- AI confidence 0-1
    OCCURRED_AT TIMESTAMP_TZ,
    CREATED_AT TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);

-- User replies (feedback from iMessage)
CREATE TABLE USER_REPLIES (
    ID VARCHAR PRIMARY KEY,
    TRANSACTION_ID VARCHAR REFERENCES TRANSACTIONS(ID),
    USER_ID VARCHAR,
    USER_LABEL VARCHAR(4),         -- "need" or "want"
    RECEIVED_AT TIMESTAMP_TZ,
    CREATED_AT TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);

-- Predictions (from ML pipeline)
CREATE TABLE PREDICTIONS (
    ID VARCHAR PRIMARY KEY,
    USER_ID VARCHAR,
    CATEGORY VARCHAR,
    NEXT_ETA VARCHAR,              -- "2 days", "1 week"
    YEARLY_SAVINGS FLOAT,          -- Dollars
    PROBABILITY FLOAT,
    CREATED_AT TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP()
);
```

**SQLite Fallback:** Use `database/snowflake/seed_sqlite.py` for local testing.

---

## Deployment & Setup

### Environment Variables

**Create `.env` file in project root:**

```bash
# Knot API
KNOT_CLIENT_ID=your_client_id
KNOT_API_SECRET=your_api_secret

# Photon API
PHOTON_API_KEY=your_api_key

# Dedalus/MCP
DEDALUS_API_URL=http://localhost:3000  # Or actual MCP server
ANTHROPIC_API_KEY=your_anthropic_key    # If using Claude directly

# Database (Snowflake)
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=SNOWFLAKE_LEARNING_DB
SNOWFLAKE_SCHEMA=BALANCEIQ_CORE
SNOWFLAKE_WAREHOUSE=COMPUTE_WH

# Or use SQLite for local dev
USE_SQLITE=true
SQLITE_DB_PATH=./local.db

# Server
FLASK_ENV=development
PORT=8000
```

### Running the Backend

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up database (Snowflake or SQLite)
python database/snowflake/seed_sqlite.py  # For local testing

# 3. Run Flask server
python src/main.py
# Server runs on http://localhost:8000
```

### Testing Integration Points

```bash
# Test Knot webhook (mock)
curl -X POST http://localhost:8000/api/knot/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "event": "TRANSACTION_CREATED",
    "transaction": {
      "id": "test-123",
      "merchant": "Starbucks",
      "amount": 5.25
    },
    "user": {"external_user_id": "u_demo"}
  }'

# Test summary endpoint
curl http://localhost:8000/user/u_demo/summary

# Test classification (once module is built)
curl -X POST http://localhost:8000/test/classify \
  -H "Content-Type: application/json" \
  -d '{"merchant": "Starbucks", "amount": 5.25}'
```

---

## Next Steps (Priority Order)

### Immediate (Day 1)
1. ✅ Unified architecture document (this file)
2. ⏳ Refactor database module (remove FastAPI)
3. ⏳ Set up Dedalus MCP server locally
4. ⏳ Implement classification.py with mock data

### Day 2
1. Wire classification into Knot webhook
2. Implement photon.py (send message)
3. Test end-to-end: Knot → Classification → DB → Photon

### Day 3
1. Implement prediction.py
2. Handle Photon replies
3. Build frontend summary endpoint
4. Integration testing

### Demo Day
1. Full end-to-end test with real transactions
2. Frontend connected
3. Live demo: purchase → classification → iMessage → prediction

---

## Decision Log

**2025-11-08:**
- ✅ Flask chosen as main API (remove FastAPI)
- ✅ Database module will be imported library, not separate server
- ✅ Classification and Prediction both use Dedalus MCP
- ✅ Prediction engine may use DigitalOcean AI or function calling (TBD)
- ✅ Photon handles all iMessage communication
- ⏳ Search term preparation logic (TBD - may not be needed if we just use categories)

**Questions to Resolve:**
- [ ] What MCP server/tool for classification? (Custom vs existing)
- [ ] DigitalOcean AI model specifics for prediction?
- [ ] Photon webhook format and authentication?
- [ ] Do we need search terms, or just categories?

---

## Contact & Ownership

**Backend:** Tony + [Your Name]
**Database:** Nguyen
**Frontend:** Noctorious
**Integrations:** Quang (Photon + Clerk)

**Questions?** Update this doc and ping the team!
