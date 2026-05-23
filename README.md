<div align="center">

# ZoomConnect Backend

**Production-grade REST API for a Zoom-style video meeting platform**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL%20mode-003B57?style=flat-square&logo=sqlite&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=flat-square)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-brightgreen?style=flat-square)

Converted from the original Express.js 5 / TypeScript implementation.  
Built with strict adherence to REST conventions, database normalisation,  
and zero platform-specific dependencies.

[Quick Start](#quick-start) · [API Reference](#api-reference) · [Schema](#database-schema) · [Architecture](#architecture-decisions)

</div>

---

## Tech Stack

| Layer            | Technology                                       |
|------------------|--------------------------------------------------|
| **Language**     | Python 3.11+                                     |
| **Framework**    | FastAPI 0.115 (ASGI)                             |
| **ORM**          | SQLAlchemy 2.0 — typed, declarative              |
| **Database**     | SQLite with WAL mode & foreign-key enforcement   |
| **Validation**   | Pydantic v2 — camelCase wire format              |
| **Server**       | Uvicorn                                          |
| **Linting**      | Ruff                                             |
| **Type checking**| Mypy (strict)                                    |

---

## Project Structure

```
zoom_clone_backend/
│
├── app/
│   ├── main.py                ← Application factory, lifespan, middleware
│   ├── config.py              ← Pydantic-settings — all config from environment
│   ├── database.py            ← Engine, session factory, declarative Base
│   ├── exceptions.py          ← Domain exceptions + FastAPI error handlers
│   ├── logging_config.py      ← Centralised, structured logging
│   │
│   ├── models/
│   │   ├── _base.py           ← TimestampMixin (auto-managed timestamps)
│   │   ├── user.py            ← Users table
│   │   ├── meeting.py         ← Meetings table (indexes + CHECK constraints)
│   │   ├── participant.py     ← Participants table  ← 1:N to meetings
│   │   └── __init__.py        ← Injects participant_count SQL subquery
│   │
│   ├── schemas/
│   │   ├── common.py          ← ErrorResponse, PaginatedResponse
│   │   ├── user.py            ← UserCreate / UserUpdate / UserRead
│   │   ├── meeting.py         ← MeetingCreate / MeetingUpdate / MeetingRead
│   │   └── participant.py     ← JoinMeetingInput / ParticipantRead
│   │
│   ├── routers/
│   │   ├── __init__.py        ← Aggregates all sub-routers into api_router
│   │   ├── health.py          ← GET  /api/healthz
│   │   ├── meetings.py        ← Full CRUD + join / end / participants
│   │   ├── dashboard.py       ← GET  /api/dashboard/summary
│   │   └── users.py           ← Full CRUD /api/users
│   │
│   └── utils/
│       └── meeting_utils.py   ← ID generator, invite-link builder, normaliser
│
├── seed.py                    ← Idempotent demo-data seeder (5 users, 11 meetings)
├── run.py                     ← Development server launcher
├── Makefile                   ← install · dev · seed · lint · typecheck · test
├── pyproject.toml             ← Project metadata + tool configuration
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

---

## Database Schema

> Schema is in **BCNF** (Boyce-Codd Normal Form). No data is stored redundantly.

### `users`

| Column         | Type      | Constraints              | Notes                       |
|----------------|-----------|--------------------------|-----------------------------|
| `id`           | INTEGER   | PK, autoincrement        |                             |
| `display_name` | TEXT(120) | NOT NULL                 |                             |
| `email`        | TEXT(255) | NOT NULL, UNIQUE, indexed|                             |
| `avatar_url`   | TEXT      | nullable                 |                             |
| `created_at`   | DATETIME  | NOT NULL, UTC            | Set once at creation        |
| `updated_at`   | DATETIME  | NOT NULL, UTC            | Auto-refreshed on every write|

### `meetings`

| Column            | Type      | Constraints                          | Notes                              |
|-------------------|-----------|--------------------------------------|------------------------------------|
| `id`              | INTEGER   | PK, autoincrement                    |                                    |
| `meeting_id`      | TEXT(20)  | NOT NULL, UNIQUE, indexed            | Human-readable `"XXX XXX XXXX"`    |
| `title`           | TEXT(255) | NOT NULL                             |                                    |
| `description`     | TEXT      | nullable                             |                                    |
| `host_id`         | INTEGER   | FK → `users.id` CASCADE, indexed     |                                    |
| `type`            | TEXT(20)  | CHECK(`instant`\|`scheduled`)        |                                    |
| `status`          | TEXT(20)  | CHECK(`waiting`\|`active`\|`ended`), indexed |                           |
| `scheduled_at`    | DATETIME  | nullable                             |                                    |
| `duration_minutes`| INTEGER   | NOT NULL, default 60                 |                                    |
| `invite_link`     | TEXT      | NOT NULL                             | `BASE_URL/join/{compactId}`        |
| `passcode`        | TEXT(50)  | nullable                             |                                    |
| `created_at`      | DATETIME  | NOT NULL, indexed                    |                                    |
| `updated_at`      | DATETIME  | NOT NULL                             | Auto-refreshed on every write      |

> **`participant_count`** is NOT a stored column. It is a correlated SQL `column_property`  
> (live `COUNT` subquery) — always accurate, zero drift risk.

### `participants`

| Column         | Type      | Constraints                                | Notes                              |
|----------------|-----------|--------------------------------------------|------------------------------------|
| `id`           | INTEGER   | PK, autoincrement                          |                                    |
| `meeting_id`   | INTEGER   | FK → `meetings.id` CASCADE, indexed        |                                    |
| `user_id`      | INTEGER   | FK → `users.id` SET NULL, indexed, nullable| NULL for unauthenticated guests    |
| `display_name` | TEXT(120) | NOT NULL                                   | Snapshot at join-time              |
| `is_muted`     | BOOLEAN   | NOT NULL, CHECK(0\|1), default 0           |                                    |
| `is_camera_off`| BOOLEAN   | NOT NULL, CHECK(0\|1), default 1           |                                    |
| `is_admitted`  | BOOLEAN   | NOT NULL, CHECK(0\|1), default 1           | Waiting-room gate                  |
| `is_host`      | BOOLEAN   | NOT NULL, CHECK(0\|1), default 0           |                                    |
| `joined_at`    | DATETIME  | NOT NULL, indexed                          |                                    |
| `left_at`      | DATETIME  | nullable                                   | NULL while still in the meeting    |

---

## API Reference

Base path: `/api`  
Interactive docs: `http://localhost:8000/api/docs`

### Health

| Method | Path         | Description      |
|--------|--------------|------------------|
| `GET`  | `/healthz`   | Liveness probe   |

### Meetings

| Method   | Path                          | Description                                           |
|----------|-------------------------------|-------------------------------------------------------|
| `GET`    | `/meetings`                   | List meetings — filterable by type, paginated         |
| `POST`   | `/meetings`                   | Create an instant or scheduled meeting                |
| `POST`   | `/meetings/join/{id}`         | Join a meeting — creates a Participant row            |
| `GET`    | `/meetings/{id}`              | Get a single meeting by ID or PK                      |
| `PATCH`  | `/meetings/{id}`              | Partial update                                        |
| `DELETE` | `/meetings/{id}`              | Delete — cascades to participants                     |
| `POST`   | `/meetings/{id}/end`          | End a meeting — stamps `left_at` on all participants  |
| `GET`    | `/meetings/{id}/participants` | List all participant records                          |

#### Pagination

```
GET /api/meetings?type=upcoming&page=1&page_size=20
```

Pagination metadata is available in response headers:

```
X-Total-Count: 42
X-Page: 1
X-Page-Size: 20
```

### Dashboard

| Method | Path               | Description                                     |
|--------|--------------------|-------------------------------------------------|
| `GET`  | `/dashboard/summary` | Stats + top-5 meetings per category            |

### Users

| Method   | Path          | Description    |
|----------|---------------|----------------|
| `GET`    | `/users`      | List users     |
| `POST`   | `/users`      | Create user    |
| `GET`    | `/users/{id}` | Get user       |
| `PATCH`  | `/users/{id}` | Update user    |
| `DELETE` | `/users/{id}` | Delete user    |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/ketarora/ZOOM_clone_backend.git
cd ZOOM_clone_backend

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set BASE_URL to your domain in production

# 5. Start the development server
python run.py
# Server running at http://localhost:8000
# Swagger UI at http://localhost:8000/api/docs

# 6. Seed demo data (optional, idempotent)
python seed.py
```

**Or use the Makefile:**

```bash
make install   # create venv + install all deps
make dev       # start dev server with hot-reload
make seed      # populate demo data
make lint      # ruff check + format check
make typecheck # mypy strict
make test      # pytest
```

---

## Environment Variables

All settings are read from environment variables or a `.env` file.  
Copy `.env.example` → `.env` and adjust as needed.

| Variable        | Default                      | Description                                     |
|-----------------|------------------------------|-------------------------------------------------|
| `DATABASE_URL`  | `sqlite:///./zoom_clone.db`  | SQLAlchemy connection string                    |
| `BASE_URL`      | `http://localhost:8000`      | Used to generate shareable invite links         |
| `HOST`          | `0.0.0.0`                    | Server bind address                             |
| `PORT`          | `8000`                       | Server port                                     |
| `LOG_LEVEL`     | `info`                       | `debug` · `info` · `warning` · `error`          |
| `CORS_ORIGINS`  | `*`                          | Comma-separated allowed origins                 |
| `RELOAD`        | `true`                       | Uvicorn hot-reload (development only)           |

---

## Wire Format

All JSON responses use **camelCase** field names to match the frontend TypeScript interfaces:

```jsonc
// GET /api/meetings/:id
{
  "id": 1,
  "meetingId": "312 748 5920",
  "title": "Sprint Planning",
  "hostName": "Ketan Arora",
  "hostEmail": "ketan.arora019@gmail.com",
  "type": "scheduled",
  "status": "waiting",
  "scheduledAt": "2026-05-25T10:00:00Z",
  "durationMinutes": 60,
  "participantCount": 0,
  "inviteLink": "http://localhost:8000/join/3127485920",
  "passcode": null,
  "createdAt": "2026-05-23T08:00:00Z",
  "updatedAt": "2026-05-23T08:00:00Z"
}
```

---

## Architecture Decisions

| Decision | Rationale |
|---|---|
| **`participants` table** instead of `participantCount` integer | Proper 1:N relation — tracks identity, join/leave time, mic/camera/host state per session |
| **`participant_count` as SQL `column_property`** | Correlated COUNT subquery — always accurate, never drifts, no application bookkeeping |
| **`users` table** instead of hardcoded host strings | Enables future multi-user auth; fixes a data integrity violation from day one |
| **`CHECK` constraints on `type` / `status`** | Enum integrity enforced at the database layer, not just application code |
| **5 explicit indexes** | `meeting_id(unique)`, `status`, `host_id`, `created_at`, `joined_at` — prevents full-table scans |
| **BCNF normalisation** | `host_name` / `host_email` via FK, not stored on `meetings`; `participant_count` never stored |
| **`lifespan` context manager** | `@app.on_event("startup")` was deprecated in FastAPI 0.93 |
| **Domain exceptions** (`NotFoundError`, `ConflictError`, `BusinessRuleError`) | HTTP concerns never leak into business logic; previous handler swallowed real 404s |
| **`updated_at` via `before_update` SQLAlchemy event** | Fires on every ORM flush — more reliable than the `onupdate` Column parameter |
| **`secrets.randbelow`** for meeting ID | Cryptographically random vs. predictable `random` module |
| **Pagination on `GET /api/meetings`** | Prevents memory exhaustion when the table grows; metadata in response headers |
| **Indexed lookup → PK fallback** | Meeting resolution is O(log n) via indexed `meeting_id`; no full-table scans or LIKE queries |

---

## Frontend Compatibility

The API is a drop-in replacement for the original Express.js backend.  
The frontend (`artifacts/zoom-connect`) can point to this server with no changes  
other than updating the base URL in its environment config.

---

## License

MIT
