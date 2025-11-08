# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Real-Time Spending Coach** - A conversational financial assistant that reacts instantly to new purchases, classifying transactions as "Need" or "Want" using AI, and sending timely nudges through iMessage to reinforce healthy spending decisions.

## Technology Stack

- **Backend**: Python Flask
- **Agent Framework**: Dedalus / MCP (classification logic)
- **Database**: Snowflake (with SQLite fallback)
- **Messaging**: Photon (iMessage integration)
- **Auth**: Clerk
- **Frontend**: Next.js or Vite + React
- **Transaction Data**: Knot API

## Repository Structure

```
/backend      - Flask application, API endpoints, orchestration logic
/agents       - Dedalus/MCP classification agents
/frontend     - Next.js/Vite app for transaction summary visualization
/database     - Schema definitions and CRUD operations
/tmp/claude   - Temporary files and plans (not committed)
```

## Development Setup

### Backend (Python/Flask)
```bash
# Create and activate virtual environment
python -m venv .hack_venv
source .hack_venv/bin/activate  # On Windows: .hack_venv\Scripts\activate

# Install dependencies (when requirements.txt exists)
pip install -r backend/requirements.txt

# Run Flask server
cd backend
flask run
```

### Frontend (Next.js/Vite)
```bash
# Install dependencies
cd frontend
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## Core Architecture

### Data Flow
```
[Purchase] → [Knot API] → [Flask Backend] → [Dedalus Classification]
    ↓
[Database: store transaction + classification]
    ↓
[Photon iMessage: "Need or Want?"]
    ↓
[User Reply] → [Backend] → [Update database]
    ↓
[Prediction Engine] → [Photon: preemptive nudge]
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/events/transaction` | POST | Receives purchase event, calls classification agent, sends notification |
| `/notifications/reply` | POST | Receives user's Need/Want reply, updates database |
| `/user/<user_id>/summary` | GET | Returns recent transactions and predictions for frontend |

### Database Schema

**users**: id, name, clerk_id
**transactions**: id, user_id, merchant, item, amount, timestamp
**classifications**: transaction_id, need_or_want, category, confidence, reasoning
**user_labels**: transaction_id, user_label, updated_at
**predictions**: transaction_id, next_eta, probability, yearly_savings_estimate

## Key Integration Points

- **Knot**: Provides merchant and transaction data, triggers `/events/transaction`
- **Dedalus/MCP**: Classification agent returning `{need_or_want, category, confidence, reasoning}`
- **Photon**: Sends/receives iMessages for user interaction
- **Clerk**: User authentication and session management

## Workflow Rules

### Planning and Execution
0. **Always create a plan and confirm before proceeding**
1. Think through the problem, read relevant files, write plan to `tmp/claude/todo.md`
2. Plan should include todo items with tests to validate each change
3. For every step, provide high-level explanation of planned changes
4. After plan confirmation, work on todos and mark complete as you go

### Code Quality
5. Keep changes simple - minimize code impact
6. Avoid duplicate code
7. Add docstrings explaining purpose, inputs, and outputs for all functions
8. Follow security best practices:
   - No sensitive information in frontend
   - Validate all inputs
   - Sanitize user data before database operations
   - Secure API endpoints with Clerk authentication

### Testing and Review
9. After tests pass, confirm whether to keep test files for unit testing
10. Add review section to `todo.md` summarizing changes
11. Keep all temporary files under `tmp/claude/` directory

## Demo Flow (for reference)

1. Submit transaction via mock event
2. Backend calls classification agent → returns "Want"
3. User receives Photon message → replies "Need"
4. Database updates with user feedback
5. Prediction model identifies future purchase
6. System sends preemptive nudge
7. Frontend displays transaction chain and savings estimate
