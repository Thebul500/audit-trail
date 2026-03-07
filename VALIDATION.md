# Real-World Validation

Full Docker Compose stack (FastAPI app + PostgreSQL 16) exercised end-to-end on a live network.

**Environment:**
- Host: Linux 6.17.0-14-generic (x86_64)
- Docker Compose: app (python:3.12-alpine) + postgres:16-alpine
- Database: PostgreSQL 16 via asyncpg
- Date: 2026-03-06

## Stack Startup

```
$ docker compose up -d
 Container audit-trail-postgres-1  Created
 Container audit-trail-app-1       Created
 Container audit-trail-postgres-1  Started
 Container audit-trail-postgres-1  Healthy
 Container audit-trail-app-1       Started

$ docker compose ps
NAME                     IMAGE                STATUS                    PORTS
audit-trail-app-1        audit-trail-app      Up 4 seconds              0.0.0.0:8000->8000/tcp
audit-trail-postgres-1   postgres:16-alpine   Up 12 seconds (healthy)   0.0.0.0:5433->5432/tcp
```

App logs confirm clean startup against PostgreSQL:
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Test Results

### 1. Health Check
**Timestamp:** 2026-03-06T23:57:51Z
```
GET /health -> 200
{
    "status": "healthy",
    "version": "0.1.0",
    "timestamp": "2026-03-06T23:57:51.600929Z"
}
```

### 2. Readiness Check
**Timestamp:** 2026-03-06T23:57:52Z
```
GET /ready -> 200
{
    "status": "ready"
}
```

### 3. Register API Key
**Timestamp:** 2026-03-06T23:57:57Z
```
POST /api/v1/auth/register -> 201
{
    "id": "6933896a-d5ef-44eb-b9bc-ed51869467bb",
    "name": "validation-test",
    "api_key": "PszMRurdr7FNZ3zBmOvP8ug5Q4MWQ312CY8AWuZtxjQ"
}
```

### 4. Get JWT Token
**Timestamp:** 2026-03-06T23:58:02Z
```
POST /api/v1/auth/token -> 200
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

### 5. Create Audit Event #1 (Genesis)
**Timestamp:** 2026-03-06T23:58:09Z
```
POST /api/v1/events -> 201
{
    "id": "37ca0bba-d16e-4779-927c-08ced8a4b549",
    "stream_id": "user-service",
    "actor": "admin@example.com",
    "action": "user.created",
    "resource_type": "user",
    "resource_id": "usr-001",
    "payload": {"email": "new@example.com", "role": "viewer"},
    "hash": "475b72fc4696ab3deaa5a07827a4af4cfc5b6b90c404c0793c352183b479506c",
    "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
    "created_at": "2026-03-06T23:58:09.841292Z"
}
```
First event in stream starts with genesis hash (64 zeros).

### 6. Create Audit Event #2 (Chain Verified)
**Timestamp:** 2026-03-06T23:58:18Z
```
POST /api/v1/events -> 201
{
    "id": "e5297a71-ec7c-4e7c-a178-ae187ed90fd9",
    "stream_id": "user-service",
    "actor": "admin@example.com",
    "action": "user.updated",
    "resource_type": "user",
    "resource_id": "usr-001",
    "payload": {"role": "editor"},
    "hash": "36735790c79b5d8e5e5ec4df084b85b6cdde140911e934e1a9c0a3d185ace5a2",
    "previous_hash": "475b72fc4696ab3deaa5a07827a4af4cfc5b6b90c404c0793c352183b479506c",
    "created_at": "2026-03-06T23:58:18.126554Z"
}
```
`previous_hash` matches event #1's `hash` -- tamper-evident chain is working.

### 7. List Events
**Timestamp:** 2026-03-06T23:58:26Z
```
GET /api/v1/events -> 200
{
    "items": [... 2 events ...],
    "total": 2
}
```
Pagination response with correct total count.

### 8. Get Event by ID
**Timestamp:** 2026-03-06T23:58:28Z
```
GET /api/v1/events/37ca0bba-d16e-4779-927c-08ced8a4b549 -> 200
{
    "id": "37ca0bba-d16e-4779-927c-08ced8a4b549",
    "stream_id": "user-service",
    "actor": "admin@example.com",
    "action": "user.created",
    ...
}
```

### 9. Get Non-Existent Event (404)
**Timestamp:** 2026-03-06T23:58:36Z
```
GET /api/v1/events/00000000-0000-0000-0000-000000000000 -> 404
{"detail": "Event not found"}
```

### 10. Unauthorized Access (No Token)
**Timestamp:** 2026-03-06T23:58:37Z
```
GET /api/v1/events -> 401
{"detail": "Not authenticated"}
```

### 11. Invalid Token
**Timestamp:** 2026-03-06T23:58:38Z
```
GET /api/v1/events (Bearer invalid-token-here) -> 401
{"detail": "Invalid token"}
```

### 12. Create Retention Policy
**Timestamp:** 2026-03-06T23:58:44Z
```
POST /api/v1/retention/policies -> 201
{
    "id": "1063ff77-07dc-41ea-bf31-157058120b13",
    "stream_id": "user-service",
    "max_age_days": 90,
    "is_active": true,
    "created_at": "2026-03-06T23:58:44.428854Z",
    "updated_at": "2026-03-06T23:58:44.428862Z"
}
```

### 13. List Retention Policies
**Timestamp:** 2026-03-06T23:58:48Z
```
GET /api/v1/retention/policies -> 200
[{"id": "1063ff77-...", "stream_id": "user-service", "max_age_days": 90, ...}]
```

### 14. Update Retention Policy
**Timestamp:** 2026-03-06T23:58:53Z
```
PUT /api/v1/retention/policies/1063ff77-07dc-41ea-bf31-157058120b13 -> 200
{
    "id": "1063ff77-07dc-41ea-bf31-157058120b13",
    "stream_id": "user-service",
    "max_age_days": 180,
    "is_active": true,
    "created_at": "2026-03-06T23:58:44.428854Z",
    "updated_at": "2026-03-06T23:58:53.940028Z"
}
```
`max_age_days` updated from 90 to 180, `updated_at` timestamp advanced.

### 15. Create Webhook
**Timestamp:** 2026-03-06T23:58:59Z
```
POST /api/v1/webhooks -> 201
{
    "id": "8f245986-73ea-4988-b742-ec1ebcdc8b1d",
    "url": "https://example.com/webhook",
    "event_filter": "user.*",
    "is_active": true,
    "created_at": "2026-03-06T23:58:59.352924Z"
}
```

### 16. List Webhooks
**Timestamp:** 2026-03-06T23:59:05Z
```
GET /api/v1/webhooks -> 200
[{"id": "8f245986-...", "url": "https://example.com/webhook", "event_filter": "user.*", ...}]
```

### 17. Delete Webhook
**Timestamp:** 2026-03-06T23:59:08Z
```
DELETE /api/v1/webhooks/8f245986-73ea-4988-b742-ec1ebcdc8b1d -> 204
(empty response body)
```

### 18. Duplicate Registration (400)
**Timestamp:** 2026-03-06T23:59:09Z
```
POST /api/v1/auth/register -> 400
{"detail": "Name already registered"}
```

### 19. Hash Chain Isolation (Separate Stream)
**Timestamp:** 2026-03-06T23:59:19Z
```
POST /api/v1/events -> 201
{
    "id": "0cf9bf2b-d06e-41db-b143-99a5e2af5bc2",
    "stream_id": "billing-service",
    "actor": "system",
    "action": "invoice.created",
    "resource_type": "invoice",
    "resource_id": "inv-001",
    "payload": {"amount": 99.99, "currency": "USD"},
    "hash": "3bc1567eec4dadb81a182b5058dca7096cb7645f5098ab8daca56343e991b3dc",
    "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
    "created_at": "2026-03-06T23:59:19.348501Z"
}
```
New stream starts its own chain from genesis -- hash chains are isolated per `stream_id`.

### 20. OpenAPI Schema
**Timestamp:** 2026-03-06T23:59:23Z
```
GET /openapi.json -> 200
Title: audit-trail
Version: 0.1.0
Paths: 10
Endpoints:
  POST /api/v1/auth/register
  POST /api/v1/auth/token
  POST /api/v1/events
  GET  /api/v1/events
  GET  /api/v1/events/{event_id}
  GET  /api/v1/retention/policies
  POST /api/v1/retention/policies
  PUT  /api/v1/retention/policies/{policy_id}
  GET  /api/v1/webhooks
  POST /api/v1/webhooks
  DELETE /api/v1/webhooks/{webhook_id}
  GET  /health
  GET  /ready
```

## Summary

| Test | Endpoint | Method | Expected | Actual | Status |
|------|----------|--------|----------|--------|--------|
| Health check | /health | GET | 200 | 200 | PASS |
| Readiness | /ready | GET | 200 | 200 | PASS |
| Register API key | /api/v1/auth/register | POST | 201 | 201 | PASS |
| Get JWT token | /api/v1/auth/token | POST | 200 | 200 | PASS |
| Create event (genesis) | /api/v1/events | POST | 201 | 201 | PASS |
| Create event (chained) | /api/v1/events | POST | 201 | 201 | PASS |
| List events | /api/v1/events | GET | 200 | 200 | PASS |
| Get event by ID | /api/v1/events/{id} | GET | 200 | 200 | PASS |
| Event not found | /api/v1/events/{id} | GET | 404 | 404 | PASS |
| No auth token | /api/v1/events | GET | 401 | 401 | PASS |
| Invalid token | /api/v1/events | GET | 401 | 401 | PASS |
| Create retention policy | /api/v1/retention/policies | POST | 201 | 201 | PASS |
| List retention policies | /api/v1/retention/policies | GET | 200 | 200 | PASS |
| Update retention policy | /api/v1/retention/policies/{id} | PUT | 200 | 200 | PASS |
| Create webhook | /api/v1/webhooks | POST | 201 | 201 | PASS |
| List webhooks | /api/v1/webhooks | GET | 200 | 200 | PASS |
| Delete webhook | /api/v1/webhooks/{id} | DELETE | 204 | 204 | PASS |
| Duplicate registration | /api/v1/auth/register | POST | 400 | 400 | PASS |
| Hash chain isolation | /api/v1/events | POST | 201 | 201 | PASS |
| OpenAPI schema | /openapi.json | GET | 200 | 200 | PASS |

**20/20 tests passed.**

## Hash Chain Verification

The tamper-evident hash chain was verified across two scenarios:

1. **Sequential events in same stream** (`user-service`):
   - Event #1 `previous_hash` = `0000...0000` (genesis)
   - Event #2 `previous_hash` = Event #1's `hash` (`475b72fc...`)

2. **Separate stream** (`billing-service`):
   - Event #1 `previous_hash` = `0000...0000` (independent genesis)

Hash chains are correctly isolated per `stream_id` and linked sequentially within each stream.

## Limitations and Notes

- **No Alembic migrations ran**: Table creation uses `Base.metadata.create_all` at startup, which works for fresh databases but doesn't handle schema evolution. Production deployments should run Alembic migrations.
- **Secret key**: Uses the default `change-me` secret in Docker Compose via `${SECRET_KEY:-change-me}`. Must be changed for production.
- **Webhook delivery**: Webhook subscriptions are stored but no delivery mechanism was tested (the service records subscriptions; delivery is out of scope for this validation).
- **Retention policy enforcement**: Policies are stored but no background job runs to delete expired events. The CRUD for policies works correctly.
- **CORS**: Currently allows all origins (`*`). Should be restricted in production.
