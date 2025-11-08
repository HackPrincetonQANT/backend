┌─────────────────────────────────┐
│  Load Amazon Mock Data JSON     │
│  (transactions with products)   │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  For Each Product in Transaction│
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Extract Item Name & Price      │
│  e.g., "Wemo Mini Smart Plug"   │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Call Dedalus AI Agent          │
│  → Model: openai/gpt-5-mini     │
│  → Prompt: "Categorize: {name}" │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Receive Category from Model    │
│  e.g., "Electronics"            │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Insert to Snowflake DB:        │
│  • category                     │
│  • item_name, price, qty        │
│  • merchant, timestamp          │
│  • confidence, reason           │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Auto-Generate Embeddings ✨    │
│  → Cortex EMBED_TEXT_768        │
│  → For ML/semantic search       │
│  → Batch processing             │
└─────────────────────────────────┘