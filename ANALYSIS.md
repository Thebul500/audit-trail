# Competitive Analysis — audit-trail

Research conducted March 2026 to evaluate the existing landscape of open-source
audit logging tools before building another one.

---

## Existing Tools

### 1. immudb (CodeNotary)

- **GitHub**: ~8,900 stars
- **Language**: Go
- **License**: BUSL-1.1 (Business Source License — not fully open source)
- **What it does**: A full immutable database (SQL/Key-Value/Document) with
  built-in cryptographic verification. Tamper-proof by design — you can add
  records but never delete or modify them. Supports Merkle tree proofs.
- **Key features**: SQL interface, multi-model (KV + SQL + Document),
  built-in audit mode, time-travel queries, SDKs for Go/Java/Python/.NET.
- **What users complain about**:
  - It's a full database, not an audit logging service. Using it just for
    audit logs is like using a sledgehammer to hang a picture frame.
  - License changed from Apache-2.0 to BUSL-1.1, which restricts production
    use for competing services. Not truly open source by OSI definition.
  - GitHub issue #2063: audit mode reported `consistent: true` even after
    manual hex-editor tampering of the underlying .val file, raising questions
    about file-level tamper detection.
  - Requires running a separate database server. Teams already using
    PostgreSQL/MySQL now have two databases to operate.
  - Documentation quality and learning curve cited as pain points.

### 2. Retraced (BoxyHQ)

- **GitHub**: ~425 stars
- **Language**: TypeScript / Node.js
- **License**: Apache-2.0
- **What it does**: Embeddable audit log service for SaaS applications.
  Searchable, exportable event records with a built-in viewer UI component.
- **Key features**: Multi-tenant, embeddable viewer UI, CSV export, client
  SDKs for Go and JavaScript, GraphQL API for querying.
- **What users complain about**:
  - Requires Kubernetes for deployment. No simple docker-compose or
    single-binary option. This is a hard blocker for small teams.
  - Depends on Elasticsearch + PostgreSQL + NSQ (message queue) — heavy
    infrastructure footprint for what should be a simple service.
  - npm package maintenance flagged as "Inactive" by Snyk analysis.
  - No Python SDK. Only Go and JavaScript clients available.
  - No hash chain or cryptographic tamper evidence — it's append-only by
    convention, not by cryptographic proof.
  - No built-in retention policies.
  - No webhook/notification support for real-time alerting on events.

### 3. Google Trillian

- **GitHub**: ~3,200 stars
- **Language**: Go
- **License**: Apache-2.0
- **What it does**: Merkle-tree-backed transparency log. Powers Certificate
  Transparency (one of the largest crypto-ledger ecosystems in production).
- **Key features**: Append-only Merkle tree log, cryptographic inclusion and
  consistency proofs, scales to billions of entries, battle-tested in
  production at Google scale.
- **What users complain about**:
  - **Now in maintenance mode.** Google recommends Trillian Tessera instead.
  - Designed for certificate transparency, not general audit logging. Using
    it for business events requires significant custom work.
  - No REST API for event ingestion — you must build your own API layer.
  - No search/query capabilities — it's a log, not a database.
  - No retention policies, no export, no webhooks.
  - Extremely complex to operate (gRPC, custom map/log servers, MySQL backend).
  - Not meant to be user-facing; it's infrastructure plumbing.

### 4. Auditum

- **GitHub**: ~120 stars (estimate)
- **Language**: Go
- **License**: Apache-2.0
- **What it does**: Cloud-native audit log management system. Collect, store,
  and query audit records across multiple applications via API.
- **Key features**: HTTP and gRPC APIs, Protobuf contracts, OpenAPI spec,
  Prometheus metrics, OpenTelemetry tracing, Kubernetes-native.
- **What users complain about**:
  - Small community, limited adoption. Few real-world deployment reports.
  - No tamper evidence or hash chains — records are mutable at the
    database level.
  - No built-in retention policies or lifecycle management.
  - No webhook or notification support.
  - No embeddable UI for end-users.
  - Go-only ecosystem; no Python or JavaScript SDKs.

### 5. Attest

- **GitHub**: New project (~50 stars, growing after Show HN in early 2026)
- **Language**: Go
- **License**: Apache-2.0
- **What it does**: Multi-tenant, append-only audit logging with cryptographic
  proof via external anchoring. Each tenant has an isolated hash chain.
  Anchoring publishes snapshots to an external system to prevent silent
  history rewriting even by a privileged operator.
- **Key features**: SHA-256 hash chains per tenant, external anchoring
  (proves integrity outside the database), REST API, multi-tenant isolation.
- **What users complain about**:
  - Very new — limited production validation.
  - Explicitly states it does NOT provide: real-time alerts, retention
    policies, search/query capabilities, or application-level validation.
  - No export functionality (JSON, CSV).
  - No webhook notifications.
  - No UI or dashboard.
  - Go-only; no Python SDK or client libraries yet.

### 6. Spine (spine-oss)

- **GitHub**: New project (small)
- **Language**: TypeScript
- **License**: MIT
- **What it does**: SDK and CLI for tamper-evident audit logging. No server
  required — creates signed logs locally using Ed25519 signatures and BLAKE3
  hash chains. Verification is done offline via CLI.
- **Key features**: Ed25519 signatures, BLAKE3 hash chains, append-only JSON
  Lines files, standalone verification without a server.
- **What users complain about**:
  - Not a service — it's a library/CLI. No centralized storage or API.
  - No search, no query, no multi-tenant support.
  - File-based storage doesn't scale for production services.
  - No retention policies, no webhooks, no export.

---

## Gap Analysis

After reviewing these tools, clear gaps emerge:

| Feature | immudb | Retraced | Trillian | Auditum | Attest | Spine |
|---|---|---|---|---|---|---|
| Hash chain / tamper evidence | Yes | No | Yes (Merkle) | No | Yes | Yes |
| Simple REST API | Partial | Yes | No | Yes | Yes | No |
| Search & query | SQL | Yes | No | Basic | No | No |
| Retention policies | No | No | No | No | No | No |
| Webhook notifications | No | No | No | No | No | No |
| Export (JSON/CSV) | No | Yes | No | No | No | No |
| Lightweight deployment | No | No | No | Moderate | Yes | N/A |
| Python ecosystem | SDK exists | No | No | No | No | No |
| Stream/tenant isolation | No | Yes | N/A | Yes | Yes | No |
| Truly open source (OSI) | No (BUSL) | Yes | Yes | Yes | Yes | Yes |

**Key gaps no tool fills well:**

1. **Retention policies are universally missing.** Not a single open-source
   audit logging tool offers built-in retention lifecycle management (archive
   after X days, delete after Y days). Every team rolls their own cron jobs.

2. **Webhook notifications don't exist.** No tool notifies downstream systems
   when specific audit events occur. Teams build custom glue code to forward
   events to Slack, PagerDuty, or SIEM systems.

3. **Hash chains + usability is an either/or.** Tools with cryptographic
   integrity (immudb, Trillian, Attest) are complex infrastructure. Tools
   with good developer UX (Retraced, Auditum) skip tamper evidence entirely.
   Nobody combines both.

4. **Python ecosystem is underserved.** The audit logging space is dominated
   by Go and TypeScript. For Python/FastAPI shops, there is no turnkey
   self-hosted audit service with a native feel.

5. **Lightweight deployment is rare.** Most tools require Kubernetes,
   Elasticsearch, or custom databases. Teams that just want
   `docker-compose up` with PostgreSQL (which they already run) have no good
   option.

---

## Differentiator

**audit-trail** targets a specific, underserved niche: teams that need
cryptographic tamper evidence but refuse to adopt a new database or wrestle
with Kubernetes.

Our positioning: **"Tamper-evident audit logging that deploys like any other
FastAPI microservice."**

Concrete differentiators:

1. **Hash chains on PostgreSQL.** SHA-256 hash chains over a database teams
   already operate. No new infrastructure to learn. No immudb, no
   Elasticsearch, no Kubernetes required. Just `docker-compose up` with
   FastAPI + PostgreSQL.

2. **Built-in retention policies.** First open-source audit logger with
   declarative retention rules — archive events after N days, purge after M
   days, per-stream configuration. This is the #1 missing feature across
   every competitor.

3. **Webhook notifications.** Real-time event forwarding to external systems
   (Slack, PagerDuty, SIEM, custom endpoints). Filter by event type, stream,
   or severity. No other self-hosted audit tool offers this.

4. **Python-native.** FastAPI + async SQLAlchemy + Pydantic. First-class
   citizen in the Python ecosystem. Teams using Django, FastAPI, or Flask
   get a service that speaks their language, with schemas they can import
   directly.

5. **Stream isolation with shared verification.** Events are organized into
   streams (per-service, per-tenant), each with its own hash chain, but
   verification can span across streams for cross-service audits.

6. **Export and search from day one.** Filtered search with pagination,
   JSON and CSV export — features that Attest, Trillian, and Spine lack
   entirely, and that immudb handles awkwardly through SQL.

### Honest Assessment

We are NOT competing with immudb or Trillian on cryptographic rigor. Those
tools offer Merkle tree proofs and mathematical guarantees we won't match
with linear hash chains. We are also not competing with Retraced's
embeddable UI component for SaaS products.

What we offer is the **pragmatic middle ground**: real tamper evidence
(hash chains that detect modification), combined with the operational
features teams actually need (retention, webhooks, search, export), in a
package that deploys in 60 seconds on infrastructure they already have.

The bet is that most teams don't need Merkle proofs — they need to know
if someone quietly deleted a row from the audit log. Hash chains solve
that. And they need retention policies so their audit table doesn't grow
unbounded. And they need webhooks so security events trigger alerts. No
existing tool gives them all three.
