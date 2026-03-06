# Project Plan — audit-trail

Immutable audit logging service with tamper-evident hash chains, REST API for
ingestion/search/export, retention policies, and webhook notifications.

---

## Architecture

### System Overview

```
Clients (SDK / curl / webhooks)
        |
        v
  +-----------+       +------------+
  |  FastAPI   | ----> | PostgreSQL |
  |  (uvicorn) |       |   (async)  |
  +-----------+       +------------+
        |
        v
  Webhook dispatcher (async background tasks)
```

The service is a single deployable unit — a FastAPI application backed by
PostgreSQL. All writes are append-only. Every event is linked to its
predecessor via a SHA-256 hash chain, making the log tamper-evident.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/events` | Ingest a new audit event |
| `GET` | `/api/v1/events` | Search/list events (filtered, paginated) |
| `GET` | `/api/v1/events/{id}` | Retrieve a single event |
| `POST` | `/api/v1/events/export` | Export events as JSON or CSV |
| `POST` | `/api/v1/events/verify` | Verify hash chain integrity |
| `GET` | `/api/v1/streams` | List event streams |
| `GET` | `/api/v1/streams/{stream_id}/events` | Events within a stream |
| `POST` | `/api/v1/auth/register` | Register an API key / service account |
| `POST` | `/api/v1/auth/token` | Obtain a JWT access token |
| `GET` | `/api/v1/retention/policies` | List retention policies |
| `POST` | `/api/v1/retention/policies` | Create a retention policy |
| `PUT` | `/api/v1/retention/policies/{id}` | Update a retention policy |
| `GET` | `/api/v1/webhooks` | List webhook subscriptions |
| `POST` | `/api/v1/webhooks` | Register a webhook |
| `DELETE` | `/api/v1/webhooks/{id}` | Remove a webhook |
| `GET` | `/health` | Liveness probe |
| `GET` | `/ready` | Readiness probe (DB connectivity) |

### Data Model

```
AuditEvent
  id              UUID (PK)
  stream_id       VARCHAR(255)     -- logical grouping (e.g. "orders", "users")
  actor           VARCHAR(255)     -- who performed the action
  action          VARCHAR(255)     -- what happened (e.g. "user.created")
  resource_type   VARCHAR(255)     -- entity type affected
  resource_id     VARCHAR(255)     -- entity identifier
  payload         JSONB            -- arbitrary event data
  hash            VARCHAR(64)      -- SHA-256 of (previous_hash + event data)
  previous_hash   VARCHAR(64)      -- hash of the preceding event in the stream
  created_at      TIMESTAMPTZ      -- immutable timestamp

APIKey
  id              UUID (PK)
  name            VARCHAR(255)     -- human-readable label
  key_hash        VARCHAR(128)     -- bcrypt hash of the API key
  scopes          JSONB            -- allowed operations
  is_active       BOOLEAN
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ

RetentionPolicy
  id              UUID (PK)
  stream_id       VARCHAR(255)     -- which stream this applies to ("*" = all)
  max_age_days    INTEGER          -- delete events older than this
  is_active       BOOLEAN
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ

WebhookSubscription
  id              UUID (PK)
  url             VARCHAR(2048)    -- delivery target
  secret          VARCHAR(255)     -- HMAC signing secret
  event_filter    VARCHAR(255)     -- action pattern to match (e.g. "user.*")
  is_active       BOOLEAN
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ
```

**Hash chain mechanics:** Each event within a stream is chained. When a new
event is inserted, its `hash` is computed as
`SHA-256(previous_hash || stream_id || actor || action || resource_type || resource_id || payload_json || created_at)`.
The first event in a stream uses `previous_hash = "0" * 64`. Verification
walks the chain and recomputes each hash — any mismatch indicates tampering.

### Auth Flow

1. An administrator calls `POST /api/v1/auth/register` with a service name
   and desired scopes. The API returns a plaintext API key (shown once).
2. The service calls `POST /api/v1/auth/token` with the API key to obtain a
   short-lived JWT (default 30 min, configurable).
3. Subsequent requests include `Authorization: Bearer <jwt>`. The JWT contains
   the `sub` (key ID) and `scopes` claims.
4. Route dependencies verify the token signature and check scopes before
   processing the request.

### Deployment Architecture

- **Docker Compose** (default): `app` + `postgres` containers. Suitable for
  single-node or small-team deployments.
- **Production**: Container image deployed to any orchestrator (Kubernetes,
  ECS, Fly.io). PostgreSQL runs as a managed service (RDS, Cloud SQL). The app
  is stateless — scale horizontally behind a load balancer.
- **Migrations**: Alembic manages schema changes. Migrations run at startup or
  as a pre-deploy step.

---

## Technology

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.11+ | Mature async ecosystem, strong typing with Pydantic, broad adoption for backend services. |
| **Web framework** | FastAPI | Native async/await, automatic OpenAPI docs, Pydantic integration for request validation, dependency injection system for auth. |
| **ORM** | SQLAlchemy 2.0 (async) | Industry-standard Python ORM with first-class async support via `asyncpg`. Declarative models, Alembic integration for migrations. |
| **Database** | PostgreSQL 16 | JSONB for flexible payloads, robust indexing (B-tree + GIN), ACID guarantees critical for immutable logs, battle-tested at scale. |
| **Auth** | JWT via `python-jose` | Stateless tokens avoid session storage. Scopes provide fine-grained access control. `passlib`/bcrypt for key hashing. |
| **Migrations** | Alembic | De facto standard for SQLAlchemy migrations. Supports auto-generation and manual revision scripts. |
| **HTTP client** | httpx | Async HTTP client for webhook delivery. Connection pooling, timeouts, retry support. |
| **Linting** | Ruff | Fast, single-tool replacement for flake8 + isort + pyupgrade. |
| **Testing** | pytest + pytest-asyncio | Async test support, fixtures, parametrize. httpx `AsyncClient` for integration tests against the ASGI app. |
| **Containerization** | Docker + Compose | Reproducible builds, single-command local dev, CI-compatible. |

---

## Milestones

### Milestone 1 — Core Event Ingestion & Hash Chain
**Goal:** Accept, store, and verify audit events with tamper-evident chaining.

- [ ] `AuditEvent` model with UUID PKs, JSONB payload, hash fields
- [ ] Alembic migration for the events table
- [ ] `POST /api/v1/events` — ingest with hash chain computation
- [ ] `GET /api/v1/events` — list with pagination (cursor + limit)
- [ ] `GET /api/v1/events/{id}` — single event retrieval
- [ ] `POST /api/v1/events/verify` — chain integrity verification
- [ ] Request/response Pydantic schemas for all event endpoints
- [ ] Unit and integration tests (target 80%+ coverage)

### Milestone 2 — Authentication & Authorization
**Goal:** Secure the API with API keys and JWT tokens.

- [ ] `APIKey` model and migration
- [ ] `POST /api/v1/auth/register` — create API key
- [ ] `POST /api/v1/auth/token` — exchange key for JWT
- [ ] JWT dependency for protected routes (signature + expiry + scope checks)
- [ ] Scope-based access control (`events:write`, `events:read`, `admin`)
- [ ] Tests for auth flows and permission enforcement

### Milestone 3 — Streams, Search & Export
**Goal:** Organize events into streams and provide rich querying.

- [ ] `GET /api/v1/streams` — list distinct streams
- [ ] `GET /api/v1/streams/{stream_id}/events` — scoped event listing
- [ ] Search filters: actor, action, resource_type, resource_id, date range
- [ ] `POST /api/v1/events/export` — JSON and CSV export
- [ ] GIN index on `payload` for JSONB queries
- [ ] Tests for search, filtering, and export

### Milestone 4 — Webhooks & Notifications
**Goal:** Push event notifications to external systems.

- [ ] `WebhookSubscription` model and migration
- [ ] CRUD endpoints for webhook management
- [ ] Async webhook dispatcher (background task on event ingestion)
- [ ] HMAC-SHA256 signature on webhook payloads
- [ ] Retry with exponential backoff (3 attempts)
- [ ] Tests for webhook delivery and failure handling

### Milestone 5 — Retention Policies
**Goal:** Automated cleanup of old events based on configurable rules.

- [ ] `RetentionPolicy` model and migration
- [ ] CRUD endpoints for retention policy management
- [ ] Background task to enforce retention (periodic sweep)
- [ ] Soft-delete or hard-delete with audit of the deletion itself
- [ ] Tests for policy enforcement

### Milestone 6 — Hardening & Production Readiness
**Goal:** Security, performance, observability, and documentation.

- [ ] Rate limiting on ingestion endpoints
- [ ] Structured JSON logging
- [ ] Prometheus metrics endpoint (`/metrics`)
- [ ] CI pipeline: lint, test, coverage gate (80%), security scan
- [ ] SECURITY.md, CONTRIBUTING.md, API documentation
- [ ] Performance benchmarks (ingestion throughput, query latency)
- [ ] Container security scan and SBOM generation
- [ ] Load testing and validation report
