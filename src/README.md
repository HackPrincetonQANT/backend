# Backend Skeleton Guide

This document summarizes the initial Flask backend scaffold that was just added so the team can plug in real logic quickly. The structure mirrors the expectations described in `CLAUDE.md` (clear layout, logging, CORS, stub endpoints, documented run flow).

## Overview

- **Framework:** Flask with `flask-cors`.
- **Server:** Runs on `0.0.0.0:8000` via `run.sh`.
- **Logging:** Every request logs `METHOD PATH` using Flask's logger + stream handler.
- **Purpose:** Provide mock responses while Quang and others wire up Knot, Dedalus, Photon, Clerk, and database logic.

## Folder Layout

```
backend/
├── main.py             # Flask app factory, logging, endpoints
├── requirements.txt    # Flask + flask-cors
└── README.md           # This guide
run.sh                  # Bootstrapper that handles venv + server start
```

## Dependencies

`backend/requirements.txt` contains:

- `Flask`
- `flask-cors`

`run.sh` installs these into an existing `.hack_venv` (preferred) or an auto-created `.venv`.

## Local Setup & Run

```bash
# From repo root
./run.sh
```

The script:

1. Detects `.hack_venv` (or makes `.venv`) and activates it.
2. Upgrades pip and installs `backend/requirements.txt`.
3. Starts `python backend/main.py` on port 8000.

Console output shows standard Flask startup plus per-request logs.

## Stub Endpoints

| Method | Path                              | Mock Response                           |
|--------|-----------------------------------|-----------------------------------------|
| POST   | `/events/transaction`             | `{"transaction_id": "mock123"}`         |
| POST   | `/notifications/reply`            | `{"ok": true}`                          |
| GET    | `/user/<user_id>/summary`         | `{"recent": [], "predictions": {}}`     |

Example verification commands:

```bash
curl -X POST http://localhost:8000/events/transaction
curl -X POST http://localhost:8000/notifications/reply
curl http://localhost:8000/user/demo/summary
```

Each call logs the method and path in the server terminal.

## CORS & Logging Notes

- `flask_cors.CORS(app)` enables cross-origin access for the frontend.
- A `before_request` hook logs every incoming request. When expanding the backend, keep this hook so judges can see traffic flow.

## Next Steps

- Replace mock JSON with real Knot/Dedalus/Photon/DB integrations.
- Extend `requirements.txt` as new services are added.
- Document additional endpoints in this file to keep it aligned with `CLAUDE.md` guidelines.
