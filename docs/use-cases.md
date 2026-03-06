# Use Cases

## Financial Transaction Auditing

Banks and fintech companies must maintain tamper-evident records of every transaction for regulatory compliance (SOX, PCI-DSS). Audit Trail provides hash-chained event logging that makes retroactive modification detectable.

**Example: Recording a wire transfer**

```bash
curl -X POST https://audit.example.com/api/v1/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stream_id": "payments",
    "actor": "user:alice@bank.com",
    "action": "wire_transfer.initiated",
    "resource_type": "transaction",
    "resource_id": "txn-9f8e7d6c",
    "payload": {
      "amount": 50000,
      "currency": "USD",
      "recipient_account": "****4321",
      "approval_level": "dual_signature"
    }
  }'
```

Each event is SHA-256 hashed with a reference to the previous event's hash, forming an unbreakable chain. Any gap or modification in the chain is immediately detectable by comparing hashes.

## Healthcare Access Logging (HIPAA)

HIPAA requires covered entities to log all access to protected health information (PHI). Audit Trail tracks who accessed what patient data and when.

```bash
curl -X POST https://audit.example.com/api/v1/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stream_id": "ehr-access",
    "actor": "provider:dr.smith@hospital.org",
    "action": "patient_record.viewed",
    "resource_type": "patient",
    "resource_id": "patient-12345",
    "payload": {
      "sections_accessed": ["medications", "lab_results"],
      "reason": "scheduled_appointment",
      "ip_address": "10.0.50.12"
    }
  }'
```

Retention policies ensure logs are kept for the HIPAA-mandated 6-year minimum:

```bash
curl -X POST https://audit.example.com/api/v1/retention/policies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stream_id": "ehr-access", "max_age_days": 2190}'
```

## CI/CD Pipeline Auditing

Track every deployment, configuration change, and infrastructure modification across your DevOps pipeline. Webhook subscriptions enable real-time alerting.

```bash
# Log a deployment event
curl -X POST https://audit.example.com/api/v1/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stream_id": "deployments",
    "actor": "ci:github-actions",
    "action": "deployment.completed",
    "resource_type": "service",
    "resource_id": "api-gateway-v2.4.1",
    "payload": {
      "environment": "production",
      "commit_sha": "a1b2c3d4",
      "rollback_available": true
    }
  }'

# Subscribe to deployment events via webhook
curl -X POST https://audit.example.com/api/v1/webhooks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://slack-webhook.example.com/audit-alerts",
    "event_filter": "deployment.*",
    "secret": "whsec_abc123"
  }'
```

## SaaS Multi-Tenant Activity Logging

SaaS platforms use stream-based isolation to maintain separate audit trails per tenant while running a single Audit Trail instance.

Each tenant gets its own `stream_id`, and the hash chain is computed per stream, so tenants have independent, verifiable audit histories:

```bash
# Tenant A activity
curl -X POST https://audit.example.com/api/v1/events \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "stream_id": "tenant-acme-corp",
    "actor": "user:bob@acme.com",
    "action": "document.shared",
    "resource_type": "document",
    "resource_id": "doc-abc",
    "payload": {"shared_with": ["carol@acme.com"], "permission": "read"}
  }'
```

## Querying the Audit Trail

Retrieve events with pagination for investigation or compliance reporting:

```bash
# List recent events (paginated)
curl "https://audit.example.com/api/v1/events?skip=0&limit=20" \
  -H "Authorization: Bearer $TOKEN"

# Get a specific event by ID
curl "https://audit.example.com/api/v1/events/evt-123" \
  -H "Authorization: Bearer $TOKEN"
```

The response includes the hash chain fields for verification:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "stream_id": "payments",
  "actor": "user:alice@bank.com",
  "action": "wire_transfer.initiated",
  "resource_type": "transaction",
  "resource_id": "txn-9f8e7d6c",
  "payload": {"amount": 50000, "currency": "USD"},
  "hash": "a3f2b8c1d4e5f6...",
  "previous_hash": "9c8b7a6d5e4f3...",
  "created_at": "2026-03-06T12:00:00Z"
}
```
