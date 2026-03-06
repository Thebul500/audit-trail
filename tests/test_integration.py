"""API integration tests — real HTTP calls via FastAPI TestClient.

No mocks for HTTP calls. All requests go through the actual ASGI app
with a real (in-memory SQLite) database behind it.
"""


def _auth_headers(client) -> dict:
    """Register a service account and return Bearer auth headers."""
    reg = client.post(
        "/api/v1/auth/register",
        json={"name": "test-svc", "scopes": ["events:read", "events:write", "admin"]},
    )
    api_key = reg.json()["api_key"]
    token = client.post("/api/v1/auth/token", json={"api_key": api_key})
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Auth flow
# ---------------------------------------------------------------------------


class TestAuthFlow:
    def test_register_creates_api_key(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"name": "my-service", "scopes": ["events:read"]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "my-service"
        assert "api_key" in data
        assert "id" in data

    def test_register_duplicate_name_returns_400(self, client):
        client.post("/api/v1/auth/register", json={"name": "dup-svc"})
        resp = client.post("/api/v1/auth/register", json={"name": "dup-svc"})
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    def test_token_exchange(self, client):
        reg = client.post(
            "/api/v1/auth/register", json={"name": "token-svc"}
        )
        api_key = reg.json()["api_key"]
        resp = client.post("/api/v1/auth/token", json={"api_key": api_key})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_invalid_api_key_returns_401(self, client):
        resp = client.post(
            "/api/v1/auth/token", json={"api_key": "bogus-key-value"}
        )
        assert resp.status_code == 401

    def test_protected_endpoint_without_token_returns_401(self, client):
        resp = client.get("/api/v1/events")
        assert resp.status_code in (401, 403)

    def test_protected_endpoint_with_bad_token_returns_401(self, client):
        resp = client.get(
            "/api/v1/events",
            headers={"Authorization": "Bearer not-a-real-jwt"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Events CRUD (POST + GET)
# ---------------------------------------------------------------------------


class TestEvents:
    def test_create_event(self, client):
        headers = _auth_headers(client)
        resp = client.post(
            "/api/v1/events",
            json={
                "stream_id": "orders",
                "actor": "user@example.com",
                "action": "order.created",
                "resource_type": "order",
                "resource_id": "ord-123",
                "payload": {"amount": 99.99},
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["stream_id"] == "orders"
        assert data["action"] == "order.created"
        assert data["payload"] == {"amount": 99.99}
        assert data["previous_hash"] == "0" * 64
        assert len(data["hash"]) == 64

    def test_list_events(self, client):
        headers = _auth_headers(client)
        client.post(
            "/api/v1/events",
            json={
                "stream_id": "users",
                "actor": "admin",
                "action": "user.created",
                "resource_type": "user",
                "resource_id": "u-1",
            },
            headers=headers,
        )
        resp = client.get("/api/v1/events", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_get_event_by_id(self, client):
        headers = _auth_headers(client)
        create = client.post(
            "/api/v1/events",
            json={
                "stream_id": "users",
                "actor": "admin",
                "action": "user.deleted",
                "resource_type": "user",
                "resource_id": "u-456",
            },
            headers=headers,
        )
        event_id = create.json()["id"]
        resp = client.get(f"/api/v1/events/{event_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == event_id
        assert resp.json()["action"] == "user.deleted"

    def test_get_event_not_found_returns_404(self, client):
        headers = _auth_headers(client)
        resp = client.get("/api/v1/events/nonexistent-uuid", headers=headers)
        assert resp.status_code == 404

    def test_hash_chain_links_events(self, client):
        headers = _auth_headers(client)
        e1 = client.post(
            "/api/v1/events",
            json={
                "stream_id": "chain",
                "actor": "sys",
                "action": "step.one",
                "resource_type": "job",
                "resource_id": "j-1",
            },
            headers=headers,
        ).json()
        e2 = client.post(
            "/api/v1/events",
            json={
                "stream_id": "chain",
                "actor": "sys",
                "action": "step.two",
                "resource_type": "job",
                "resource_id": "j-1",
            },
            headers=headers,
        ).json()
        assert e1["previous_hash"] == "0" * 64
        assert e2["previous_hash"] == e1["hash"]
        assert e1["hash"] != e2["hash"]

    def test_create_event_missing_fields_returns_422(self, client):
        headers = _auth_headers(client)
        resp = client.post(
            "/api/v1/events",
            json={"stream_id": "incomplete"},
            headers=headers,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Retention Policies CRUD (POST + GET + PUT)
# ---------------------------------------------------------------------------


class TestRetentionPolicies:
    def test_create_policy(self, client):
        headers = _auth_headers(client)
        resp = client.post(
            "/api/v1/retention/policies",
            json={"stream_id": "orders", "max_age_days": 90},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["stream_id"] == "orders"
        assert data["max_age_days"] == 90
        assert data["is_active"] is True

    def test_list_policies(self, client):
        headers = _auth_headers(client)
        client.post(
            "/api/v1/retention/policies",
            json={"stream_id": "*", "max_age_days": 365},
            headers=headers,
        )
        resp = client.get("/api/v1/retention/policies", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_policy(self, client):
        headers = _auth_headers(client)
        create = client.post(
            "/api/v1/retention/policies",
            json={"stream_id": "logs", "max_age_days": 30},
            headers=headers,
        )
        policy_id = create.json()["id"]

        resp = client.put(
            f"/api/v1/retention/policies/{policy_id}",
            json={"max_age_days": 60, "is_active": False},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["max_age_days"] == 60
        assert data["is_active"] is False

    def test_update_policy_not_found_returns_404(self, client):
        headers = _auth_headers(client)
        resp = client.put(
            "/api/v1/retention/policies/nonexistent-id",
            json={"max_age_days": 10},
            headers=headers,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Webhooks CRUD (POST + GET + DELETE)
# ---------------------------------------------------------------------------


class TestWebhooks:
    def test_create_webhook(self, client):
        headers = _auth_headers(client)
        resp = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/hook",
                "event_filter": "order.*",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["url"] == "https://example.com/hook"
        assert data["event_filter"] == "order.*"
        assert data["is_active"] is True

    def test_list_webhooks(self, client):
        headers = _auth_headers(client)
        client.post(
            "/api/v1/webhooks",
            json={"url": "https://example.com/a", "event_filter": "*"},
            headers=headers,
        )
        resp = client.get("/api/v1/webhooks", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_delete_webhook(self, client):
        headers = _auth_headers(client)
        create = client.post(
            "/api/v1/webhooks",
            json={"url": "https://example.com/del", "event_filter": "x"},
            headers=headers,
        )
        wh_id = create.json()["id"]

        resp = client.delete(f"/api/v1/webhooks/{wh_id}", headers=headers)
        assert resp.status_code == 204

        # Confirm it no longer appears in the list
        remaining = client.get("/api/v1/webhooks", headers=headers).json()
        assert wh_id not in [w["id"] for w in remaining]

    def test_delete_webhook_not_found_returns_404(self, client):
        headers = _auth_headers(client)
        resp = client.delete(
            "/api/v1/webhooks/nonexistent-id", headers=headers
        )
        assert resp.status_code == 404
