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
│  Update Snowflake DB:           │
│  • category                     │
│  • total_spend += price         │
│  • add to items list            │
│  • timestamp                    │
└─────────────────────────────────┘