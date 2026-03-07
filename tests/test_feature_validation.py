"""Feature validation — end-to-end tests proving every API endpoint works
with real data against an in-memory SQLite database.

Exercises: auth registration/token, event CRUD + hash chain, stream
verification, CSV export, retention policies, and webhooks.
"""

import csv
import io


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_and_get_token(client, name="val-svc"):
    """Register an API key and exchange it for a JWT."""
    reg = client.post(
        "/api/v1/auth/register",
        json={"name": name, "scopes": ["events:read", "events:write", "admin"]},
    )
    assert reg.status_code == 201, reg.text
    api_key = reg.json()["api_key"]

    tok = client.post("/api/v1/auth/token", json={"api_key": api_key})
    assert tok.status_code == 200, tok.text
    return reg.json(), tok.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create_event(client, headers, **overrides):
    body = {
        "stream_id": "default-stream",
        "actor": "test-actor",
        "action": "test.action",
        "resource_type": "test-resource",
        "resource_id": "r-1",
        "payload": {},
    }
    body.update(overrides)
    resp = client.post("/api/v1/events", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# 1. Auth — register, token exchange, token validation
# ---------------------------------------------------------------------------


class TestAuthValidation:
    def test_full_auth_flow(self, client):
        """Register -> token -> use token on protected endpoint."""
        reg_data, token = _register_and_get_token(client, "auth-flow-svc")

        assert reg_data["name"] == "auth-flow-svc"
        assert len(reg_data["api_key"]) > 20

        # Token works on a protected endpoint
        resp = client.get("/api/v1/events", headers=_auth(token))
        assert resp.status_code == 200

    def test_invalid_token_rejected(self, client):
        resp = client.get(
            "/api/v1/events",
            headers={"Authorization": "Bearer forged.jwt.token"},
        )
        assert resp.status_code == 401

    def test_no_token_rejected(self, client):
        resp = client.get("/api/v1/events")
        assert resp.status_code in (401, 403)

    def test_bad_api_key_rejected(self, client):
        resp = client.post(
            "/api/v1/auth/token", json={"api_key": "wrong-key-value"}
        )
        assert resp.status_code == 401

    def test_duplicate_registration_rejected(self, client):
        client.post(
            "/api/v1/auth/register",
            json={"name": "once-only"},
        )
        resp = client.post(
            "/api/v1/auth/register",
            json={"name": "once-only"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 2. Events — create, read, list, filter, hash chain
# ---------------------------------------------------------------------------


class TestEventsCRUD:
    def test_create_and_retrieve_event(self, client):
        _, token = _register_and_get_token(client, "evt-crud-svc")
        headers = _auth(token)

        created = _create_event(
            client,
            headers,
            stream_id="orders",
            actor="alice@co.com",
            action="order.placed",
            resource_type="order",
            resource_id="ord-42",
            payload={"amount": 125.50, "currency": "USD"},
        )

        assert created["stream_id"] == "orders"
        assert created["actor"] == "alice@co.com"
        assert created["payload"] == {"amount": 125.50, "currency": "USD"}
        assert len(created["hash"]) == 64
        assert created["previous_hash"] == "0" * 64

        # Retrieve by ID
        fetched = client.get(
            f"/api/v1/events/{created['id']}", headers=headers
        )
        assert fetched.status_code == 200
        assert fetched.json()["id"] == created["id"]

    def test_list_with_pagination(self, client):
        _, token = _register_and_get_token(client, "evt-page-svc")
        headers = _auth(token)

        for i in range(5):
            _create_event(client, headers, stream_id="paged", resource_id=f"r-{i}")

        page1 = client.get("/api/v1/events?stream_id=paged&limit=3", headers=headers)
        assert page1.status_code == 200
        data = page1.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3

        page2 = client.get(
            "/api/v1/events?stream_id=paged&limit=3&skip=3", headers=headers
        )
        assert page2.status_code == 200
        assert len(page2.json()["items"]) == 2

    def test_filter_by_stream_actor_action(self, client):
        _, token = _register_and_get_token(client, "evt-filter-svc")
        headers = _auth(token)

        _create_event(client, headers, stream_id="billing", actor="bob", action="charge")
        _create_event(client, headers, stream_id="billing", actor="carol", action="refund")
        _create_event(client, headers, stream_id="support", actor="bob", action="ticket.open")

        # Filter by stream
        resp = client.get("/api/v1/events?stream_id=billing", headers=headers)
        items = resp.json()["items"]
        assert len(items) == 2
        assert all(e["stream_id"] == "billing" for e in items)

        # Filter by actor
        resp = client.get("/api/v1/events?actor=bob", headers=headers)
        items = resp.json()["items"]
        assert len(items) == 2
        assert all(e["actor"] == "bob" for e in items)

        # Filter by action
        resp = client.get("/api/v1/events?action=refund", headers=headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["actor"] == "carol"

    def test_hash_chain_integrity(self, client):
        """Each event's previous_hash links to the prior event's hash."""
        _, token = _register_and_get_token(client, "evt-chain-svc")
        headers = _auth(token)

        e1 = _create_event(client, headers, stream_id="chain-v", action="step.1")
        e2 = _create_event(client, headers, stream_id="chain-v", action="step.2")
        e3 = _create_event(client, headers, stream_id="chain-v", action="step.3")

        assert e1["previous_hash"] == "0" * 64
        assert e2["previous_hash"] == e1["hash"]
        assert e3["previous_hash"] == e2["hash"]

        # All hashes are unique
        hashes = {e1["hash"], e2["hash"], e3["hash"]}
        assert len(hashes) == 3

    def test_event_not_found(self, client):
        _, token = _register_and_get_token(client, "evt-404-svc")
        resp = client.get("/api/v1/events/does-not-exist", headers=_auth(token))
        assert resp.status_code == 404

    def test_invalid_event_body_rejected(self, client):
        _, token = _register_and_get_token(client, "evt-422-svc")
        resp = client.post(
            "/api/v1/events",
            json={"stream_id": ""},
            headers=_auth(token),
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 3. Stream verification — prove chain is tamper-evident
# ---------------------------------------------------------------------------


class TestStreamVerification:
    def test_verify_valid_chain(self, client):
        _, token = _register_and_get_token(client, "verify-svc")
        headers = _auth(token)

        for i in range(4):
            _create_event(client, headers, stream_id="verified", action=f"a.{i}")

        resp = client.get("/api/v1/streams/verified/verify", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is True
        assert body["total_events"] == 4
        assert body["broken_links"] == []
        assert body["stream_id"] == "verified"

    def test_verify_missing_stream_returns_404(self, client):
        _, token = _register_and_get_token(client, "verify-404-svc")
        resp = client.get("/api/v1/streams/ghost/verify", headers=_auth(token))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. CSV export
# ---------------------------------------------------------------------------


class TestCSVExport:
    def test_export_returns_valid_csv(self, client):
        _, token = _register_and_get_token(client, "csv-svc")
        headers = _auth(token)

        _create_event(client, headers, stream_id="csv-stream", action="row.one")
        _create_event(client, headers, stream_id="csv-stream", action="row.two")

        resp = client.get(
            "/api/v1/events/export/csv?stream_id=csv-stream", headers=headers
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        assert rows[0][0] == "id"  # header
        assert len(rows) == 3  # header + 2 data rows

    def test_export_empty_stream(self, client):
        _, token = _register_and_get_token(client, "csv-empty-svc")
        resp = client.get(
            "/api/v1/events/export/csv?stream_id=nope", headers=_auth(token)
        )
        assert resp.status_code == 200
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) == 1  # header only


# ---------------------------------------------------------------------------
# 5. Retention policies — create, list, update
# ---------------------------------------------------------------------------


class TestRetentionPolicies:
    def test_full_lifecycle(self, client):
        _, token = _register_and_get_token(client, "ret-svc")
        headers = _auth(token)

        # Create
        create_resp = client.post(
            "/api/v1/retention/policies",
            json={"stream_id": "audit-logs", "max_age_days": 90},
            headers=headers,
        )
        assert create_resp.status_code == 201
        policy = create_resp.json()
        assert policy["stream_id"] == "audit-logs"
        assert policy["max_age_days"] == 90
        assert policy["is_active"] is True
        policy_id = policy["id"]

        # List
        list_resp = client.get("/api/v1/retention/policies", headers=headers)
        assert list_resp.status_code == 200
        policies = list_resp.json()
        assert any(p["id"] == policy_id for p in policies)

        # Update
        update_resp = client.put(
            f"/api/v1/retention/policies/{policy_id}",
            json={"max_age_days": 180, "is_active": False},
            headers=headers,
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["max_age_days"] == 180
        assert updated["is_active"] is False

    def test_update_nonexistent_returns_404(self, client):
        _, token = _register_and_get_token(client, "ret-404-svc")
        resp = client.put(
            "/api/v1/retention/policies/no-such-id",
            json={"max_age_days": 7},
            headers=_auth(token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 6. Webhooks — create, list, delete
# ---------------------------------------------------------------------------


class TestWebhooks:
    def test_full_lifecycle(self, client):
        _, token = _register_and_get_token(client, "wh-svc")
        headers = _auth(token)

        # Create
        create_resp = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://hooks.example.com/audit",
                "event_filter": "order.*",
                "secret": "s3cret",
            },
            headers=headers,
        )
        assert create_resp.status_code == 201
        wh = create_resp.json()
        assert wh["url"] == "https://hooks.example.com/audit"
        assert wh["event_filter"] == "order.*"
        assert wh["is_active"] is True
        wh_id = wh["id"]

        # List
        list_resp = client.get("/api/v1/webhooks", headers=headers)
        assert list_resp.status_code == 200
        assert any(w["id"] == wh_id for w in list_resp.json())

        # Delete
        del_resp = client.delete(f"/api/v1/webhooks/{wh_id}", headers=headers)
        assert del_resp.status_code == 204

        # Confirm gone
        after = client.get("/api/v1/webhooks", headers=headers)
        assert wh_id not in [w["id"] for w in after.json()]

    def test_delete_nonexistent_returns_404(self, client):
        _, token = _register_and_get_token(client, "wh-404-svc")
        resp = client.delete("/api/v1/webhooks/fake-id", headers=_auth(token))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 7. Health endpoint (no auth required)
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert "version" in body
        assert "timestamp" in body

    def test_readiness_check(self, client):
        resp = client.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


# ---------------------------------------------------------------------------
# 8. End-to-end workflow — full journey through the system
# ---------------------------------------------------------------------------


class TestEndToEndWorkflow:
    def test_complete_audit_trail_journey(self, client):
        """Simulate a realistic workflow:
        register -> token -> create events -> verify chain -> export CSV
        -> set retention policy -> subscribe webhook -> cleanup.
        """
        # 1. Register and authenticate
        reg_data, token = _register_and_get_token(client, "e2e-service")
        headers = _auth(token)
        assert reg_data["id"]

        # 2. Create a series of audit events in a stream
        events = []
        actions = [
            ("user.created", {"email": "new@co.com"}),
            ("user.verified", {"method": "email"}),
            ("user.role_assigned", {"role": "editor"}),
        ]
        for action, payload in actions:
            ev = _create_event(
                client,
                headers,
                stream_id="user-lifecycle",
                actor="system",
                action=action,
                resource_type="user",
                resource_id="usr-1001",
                payload=payload,
            )
            events.append(ev)

        # 3. Verify the hash chain
        verify = client.get(
            "/api/v1/streams/user-lifecycle/verify", headers=headers
        )
        assert verify.status_code == 200
        assert verify.json()["valid"] is True
        assert verify.json()["total_events"] == 3

        # 4. Query/filter events
        filtered = client.get(
            "/api/v1/events?stream_id=user-lifecycle&action=user.verified",
            headers=headers,
        )
        assert filtered.status_code == 200
        assert filtered.json()["total"] == 1
        assert filtered.json()["items"][0]["payload"] == {"method": "email"}

        # 5. Export to CSV
        csv_resp = client.get(
            "/api/v1/events/export/csv?stream_id=user-lifecycle", headers=headers
        )
        assert csv_resp.status_code == 200
        reader = csv.reader(io.StringIO(csv_resp.text))
        csv_rows = list(reader)
        assert len(csv_rows) == 4  # header + 3 events

        # 6. Set a retention policy
        policy = client.post(
            "/api/v1/retention/policies",
            json={"stream_id": "user-lifecycle", "max_age_days": 365},
            headers=headers,
        )
        assert policy.status_code == 201

        # 7. Subscribe a webhook
        wh = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://alerts.example.com/audit",
                "event_filter": "user.*",
            },
            headers=headers,
        )
        assert wh.status_code == 201
        wh_id = wh.json()["id"]

        # 8. Clean up webhook
        del_resp = client.delete(f"/api/v1/webhooks/{wh_id}", headers=headers)
        assert del_resp.status_code == 204
