"""End-to-end tests: full API lifecycle (register, login, create, read, update, delete)."""


def _register_and_login(client):
    """Register an API key and obtain a JWT token."""
    reg = client.post(
        "/api/v1/auth/register",
        json={"name": "e2e-test", "scopes": ["events:read", "events:write"]},
    )
    assert reg.status_code == 201
    api_key = reg.json()["api_key"]

    tok = client.post("/api/v1/auth/token", json={"api_key": api_key})
    assert tok.status_code == 200
    return tok.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_full_event_lifecycle(client):
    """Register -> login -> create event -> read -> list -> verify chain."""
    token = _register_and_login(client)

    # Create first event
    create_resp = client.post(
        "/api/v1/events",
        json={
            "stream_id": "e2e-stream",
            "actor": "bob@test.com",
            "action": "user.created",
            "resource_type": "user",
            "resource_id": "usr-001",
            "payload": {"email": "bob@test.com"},
        },
        headers=_auth(token),
    )
    assert create_resp.status_code == 201
    event = create_resp.json()
    event_id = event["id"]
    assert event["previous_hash"] == "0" * 64  # first in chain

    # Read event by ID
    get_resp = client.get(f"/api/v1/events/{event_id}", headers=_auth(token))
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == event_id
    assert get_resp.json()["action"] == "user.created"

    # Create second event — hash chain continues
    create2 = client.post(
        "/api/v1/events",
        json={
            "stream_id": "e2e-stream",
            "actor": "bob@test.com",
            "action": "user.updated",
            "resource_type": "user",
            "resource_id": "usr-001",
            "payload": {"role": "admin"},
        },
        headers=_auth(token),
    )
    assert create2.status_code == 201
    assert create2.json()["previous_hash"] == event["hash"]

    # List events filtered by stream
    list_resp = client.get(
        "/api/v1/events?stream_id=e2e-stream", headers=_auth(token)
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 2

    # Verify hash chain integrity
    verify_resp = client.get(
        "/api/v1/streams/e2e-stream/verify", headers=_auth(token)
    )
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["valid"] is True
    assert verify_data["total_events"] == 2
    assert verify_data["broken_links"] == []


def test_webhook_create_and_delete(client):
    """Create a webhook, list it, delete it, confirm it's gone."""
    token = _register_and_login(client)

    # Create webhook
    create_resp = client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/hook",
            "event_filter": "user.*",
            "secret": "s3cret",
        },
        headers=_auth(token),
    )
    assert create_resp.status_code == 201
    webhook_id = create_resp.json()["id"]
    assert create_resp.json()["event_filter"] == "user.*"

    # List webhooks — should have 1
    list_resp = client.get("/api/v1/webhooks", headers=_auth(token))
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Delete webhook
    del_resp = client.delete(
        f"/api/v1/webhooks/{webhook_id}", headers=_auth(token)
    )
    assert del_resp.status_code == 204

    # List webhooks — should be empty
    list_resp2 = client.get("/api/v1/webhooks", headers=_auth(token))
    assert list_resp2.json() == []


def test_retention_policy_lifecycle(client):
    """Create a retention policy, update it, list policies."""
    token = _register_and_login(client)

    # Create policy
    create_resp = client.post(
        "/api/v1/retention/policies",
        json={"stream_id": "audit-stream", "max_age_days": 90},
        headers=_auth(token),
    )
    assert create_resp.status_code == 201
    policy_id = create_resp.json()["id"]
    assert create_resp.json()["max_age_days"] == 90

    # Update policy
    update_resp = client.put(
        f"/api/v1/retention/policies/{policy_id}",
        json={"max_age_days": 30},
        headers=_auth(token),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["max_age_days"] == 30

    # List policies
    list_resp = client.get("/api/v1/retention/policies", headers=_auth(token))
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_unauthenticated_access_denied(client):
    """Endpoints requiring auth must reject requests without a token."""
    resp = client.get("/api/v1/events")
    assert resp.status_code in (401, 403)

    resp = client.post(
        "/api/v1/events",
        json={
            "stream_id": "s",
            "actor": "a",
            "action": "a",
            "resource_type": "r",
            "resource_id": "r",
        },
    )
    assert resp.status_code in (401, 403)


def test_duplicate_registration_rejected(client):
    """Registering the same name twice should return 400."""
    body = {"name": "dup-test", "scopes": ["events:read"]}
    resp1 = client.post("/api/v1/auth/register", json=body)
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/auth/register", json=body)
    assert resp2.status_code == 400
    assert "already registered" in resp2.json()["detail"].lower()
