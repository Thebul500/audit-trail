# Enterprise Review — audit-trail

Self-evaluation conducted March 2026, comparing audit-trail against the
existing landscape of open-source audit logging tools.

---

## Competitors

### 1. immudb (CodeNotary)

- **GitHub**: ~8,900 stars
- **Language**: Go
- **License**: BUSL-1.1 (not OSI-approved open source)
- **Key features**: Full immutable database (SQL/KV/Document), Merkle tree
  proofs, time-travel queries, SDKs for Go/Java/Python/.NET, built-in audit
  mode.
- **Target audience**: Enterprises needing a dedicated immutable database for
  compliance workloads (financial services, healthcare).
- **We lack**: Merkle tree proofs (we use linear hash chains), SQL query
  interface, time-travel queries, multi-model storage.

### 2. Retraced (BoxyHQ)

- **GitHub**: ~500 stars
- **Language**: TypeScript / Node.js
- **License**: Apache-2.0
- **Key features**: Multi-tenant, embeddable viewer UI, CSV export, GraphQL
  API, client SDKs for Go and JavaScript.
- **Target audience**: SaaS companies embedding audit logs into their product
  for end-customer visibility.
- **We lack**: Embeddable viewer UI, GraphQL API, multi-tenant isolation by
  design.

### 3. Google Trillian

- **GitHub**: ~3,800 stars
- **Language**: Go
- **License**: Apache-2.0
- **Key features**: Merkle tree transparency log, cryptographic inclusion and
  consistency proofs, scales to billions of entries. Powers Certificate
  Transparency.
- **Target audience**: Infrastructure teams building transparency systems
  (certificate logs, binary transparency).
- **We lack**: Merkle tree proofs, mathematical consistency proofs, scale to
  billions. (But Trillian is in maintenance mode; successor is Tessera.)

### 4. Auditum (auditumio)

- **GitHub**: ~120 stars
- **Language**: Go
- **License**: Apache-2.0
- **Key features**: HTTP and gRPC APIs, Protobuf contracts, OpenAPI spec,
  Prometheus metrics, OpenTelemetry tracing, Kubernetes-native.
- **Target audience**: Cloud-native teams wanting structured audit records
  across microservices.
- **We lack**: gRPC API, OpenTelemetry tracing, Prometheus metrics endpoint.

### 5. Attest

- **GitHub**: ~50 stars
- **Language**: Go
- **License**: Apache-2.0
- **Key features**: SHA-256 hash chains per tenant, external anchoring (proves
  integrity outside the database), REST API, multi-tenant isolation.
- **Target audience**: Teams wanting tamper-evident logs with external proof
  anchoring.
- **We lack**: External anchoring (publishing hash snapshots to blockchain or
  external timestamping service).

### 6. audittrail-py (ethanbonsall)

- **GitHub**: New / small
- **Language**: Python
- **License**: MIT
- **Key features**: FastAPI middleware, tamper-proof hash chains, encrypted
  payloads, WORM protection, anomaly detection, CLI tools, SQLite storage.
- **Target audience**: Python developers wanting drop-in audit middleware.
- **We lack**: Middleware mode (auto-capture all requests), encrypted payloads,
  WORM protection.

### 7. Spine (spine-oss)

- **GitHub**: New / small
- **Language**: TypeScript
- **License**: MIT
- **Key features**: Ed25519 signatures, BLAKE3 hash chains, append-only JSON
  Lines files, offline verification via CLI.
- **Target audience**: Developers wanting local tamper-evident logs without a
  server.
- **We lack**: Digital signatures (Ed25519), offline verification mode.

---

## Functionality Gaps

### Feature-by-Feature Comparison

| Feature                    | immudb | Retraced | Trillian | Auditum | Attest | audit-trail |
|----------------------------|--------|----------|----------|---------|--------|-------------|
| Hash chain / tamper proof  | Merkle | No       | Merkle   | No      | SHA256 | SHA256      |
| Chain verification API     | Yes    | No       | Yes      | No      | Yes    | **Yes** (new) |
| REST API                   | Partial| Yes      | No       | Yes     | Yes    | Yes         |
| Search & filtering         | SQL    | Yes      | No       | Basic   | No     | **Yes** (new) |
| CSV export                 | No     | Yes      | No       | No      | No     | **Yes** (new) |
| Retention policies         | No     | No       | No       | No      | No     | Yes         |
| Webhook subscriptions      | No     | No       | No       | No      | No     | Yes         |
| Input validation           | Yes    | Yes      | N/A      | Yes     | Yes    | **Yes** (new) |
| Multi-tenant isolation     | No     | Yes      | N/A      | Yes     | Yes    | Partial (streams) |
| Embeddable UI              | No     | Yes      | No       | No      | No     | No          |
| External anchoring         | N/A    | No       | N/A      | No      | Yes    | No          |
| Digital signatures          | No     | No       | Yes      | No      | No     | No          |
| Metrics (Prometheus)       | No     | No       | No       | Yes     | No     | No          |
| Lightweight deploy         | No     | No       | No       | Moderate| Yes    | Yes         |
| Python-native              | SDK    | No       | No       | No      | No     | Yes         |
| Truly OSI open source      | No     | Yes      | Yes      | Yes     | Yes    | Yes (MIT)   |

### Core Functions We Are Missing

1. **Actual webhook delivery**: We store webhook subscriptions but never
   dispatch events to them. The subscription CRUD exists but the event pipeline
   does not fire notifications. This is a serious gap — the feature is
   advertised but not implemented.

2. **Actual retention policy execution**: We store retention policies but
   never apply them. There is no background task or scheduler that deletes
   expired events. Same problem as webhooks — CRUD exists, execution does not.

3. **No Prometheus metrics or OpenTelemetry**: Enterprise users expect
   `/metrics` for monitoring. We have no observability integration.

4. **No rate limiting**: Any authenticated client can flood the API. No
   protection against abuse or accidental loops.

5. **Token endpoint scans all keys**: The `/auth/token` endpoint iterates
   over every active API key to find a match (O(n)). This won't scale past
   a few hundred keys.

### Common Workflows We Don't Support

- **Bulk event ingestion**: No batch endpoint. Clients must POST one event at
  a time.
- **Event replay/streaming**: No SSE or WebSocket endpoint for real-time
  event consumption.
- **Cross-stream verification**: Can verify one stream at a time, but no
  way to verify the entire database.

### Edge Cases Unhandled

- Concurrent writes to the same stream could produce duplicate
  `previous_hash` values (race condition). No database-level locking or
  optimistic concurrency control on the hash chain.
- Extremely large payloads have no size limit (no max payload validation).
- The `Query` import in events.py is currently unused.

---

## Quality Gaps

### Code Robustness: B+

The codebase is clean, well-structured, and follows FastAPI best practices.
Async/await is used consistently. Models and schemas are properly separated.
The hash chain implementation is correct and straightforward. Test coverage
is solid with 39 passing integration tests.

However:
- No structured logging (uses no logging at all).
- No request ID tracking for debugging.
- CORS is wide open (`allow_origins=["*"]`) — fine for development, risky
  for production.
- The default secret key is `"change-me-in-production"` which is 23 bytes
  and triggers PyJWT `InsecureKeyLengthWarning` in tests.

### Error Messages: B

Error messages are clear and standard (`"Event not found"`, `"Invalid API
key"`, `"Name already registered"`). The new input validation returns proper
422 responses with Pydantic's detailed error format. But there's no custom
error handler for unhandled exceptions — a 500 error returns FastAPI's
default response.

### Output Quality: A-

API responses are clean JSON with proper schemas. The CSV export produces
well-formed output. The health endpoint returns structured data. The OpenAPI
docs (auto-generated) are complete and usable.

### CLI Experience: N/A

This is a web API, not a CLI tool. No CLI interface exists. (Not a gap —
it's by design.)

### Would a Developer Trust This in Daily Workflow?

For a v0.1.0, yes — with caveats. The core event ingestion and hash chain
verification work correctly. Auth flow is solid. The API is intuitive and
well-documented via OpenAPI. But the incomplete webhook delivery and
retention execution would frustrate anyone who tries to use those features
in production.

---

## Improvement Plan

### Implemented in This Review (4 improvements)

1. **Chain verification endpoint** (`GET /api/v1/streams/{stream_id}/verify`)
   — Walks the entire hash chain for a stream, recomputes every hash, and
   reports any broken links. This is the single most important feature for
   an "immutable audit logging" tool — without it, the hash chain is
   write-only with no way to verify. 2 new tests added.

2. **Event search and filtering** — The `GET /api/v1/events` endpoint now
   supports query parameters: `stream_id`, `actor`, `action`,
   `resource_type`, `resource_id`, `since`, `until`. Previously it only
   had `skip` and `limit` with no filtering. Results are now sorted by
   `created_at` descending. 2 new tests added.

3. **CSV export** (`GET /api/v1/events/export/csv`) — Export filtered events
   as CSV with all fields. Supports the same filter parameters as the list
   endpoint. Returns proper `Content-Disposition` header for browser
   download. 2 new tests added.

4. **Input validation on all schemas** — Added `min_length`, `max_length`,
   and `gt=0` constraints using Pydantic `Field`. Empty strings, negative
   retention days, and oversized inputs are now rejected with 422. 1 new
   test added.

### Remaining Items (Not Implemented — Future Work)

5. **Implement webhook delivery** — When an event is created, match it
   against active webhook subscriptions and POST to the configured URLs.
   Use background tasks to avoid blocking the event creation response.

6. **Implement retention policy execution** — Add a periodic task (or
   management command) that deletes events older than `max_age_days` for
   each active policy.

7. **Add structured logging** — Use Python `logging` with JSON format.
   Include request IDs, timestamps, and correlation.

8. **Add Prometheus metrics** — Expose `/metrics` with counters for events
   created, verification runs, API errors, and request latency histograms.

9. **Add concurrency control** — Use `SELECT ... FOR UPDATE` or optimistic
   locking on the hash chain to prevent race conditions on concurrent writes
   to the same stream.

10. **Tighten CORS** — Make `allow_origins` configurable via environment
    variable instead of hardcoded `*`.

---

## Final Verdict

**NOT READY** for production enterprise use. **READY** for early adopters and
development/staging environments.

### Reasoning

**What works well:**
- Core event ingestion with SHA-256 hash chains is correct and tested.
- Chain verification endpoint now exists and works.
- Search, filtering, and CSV export are functional.
- Auth flow (API keys + JWT) is solid.
- Deployment is genuinely simple (`docker-compose up`).
- Input validation catches bad data at the boundary.
- 39 integration tests pass.
- MIT license, Python-native, lightweight — real differentiators.

**What blocks production readiness:**
- Webhook delivery is not implemented (feature is advertised but broken).
- Retention policy execution is not implemented (same problem).
- No structured logging makes debugging in production impossible.
- No concurrency control on hash chain writes.
- CORS `*` is a security concern.
- No rate limiting.
- No Prometheus metrics for monitoring.

**Bottom line:** The core audit logging and verification pipeline is sound.
The project fills a genuine gap in the Python ecosystem. But two advertised
features (webhooks, retention execution) are facade-only, and operational
necessities (logging, metrics, rate limiting) are absent. A team could use
this today for non-critical audit logging in staging, but it needs 1-2 more
development cycles before it's enterprise-ready.

**Version recommendation:** Ship as `v0.1.0-beta` with clear documentation
about which features are complete and which are planned.
