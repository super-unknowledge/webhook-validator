import pytest
from fastapi.testclient import TestClient
from main import app, events

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_events():
    """Clear the in-memory events list before each test."""
    events.clear()
    yield
    events.clear()


# --- /health ---

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- POST /webhook: valid inputs ---

def test_webhook_valid_full_payload():
    response = client.post("/webhook", json={
        "event_type": "payment.created",
        "timestamp": "2024-01-15T10:30:00Z",
        "payload": {"amount": 99.99, "currency": "USD"},
        "source": "stripe"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "payment.created"
    assert "timestamp" in data
    assert data["message"] == "Webhook received successfully"


def test_webhook_valid_without_optional_source():
    response = client.post("/webhook", json={
        "event_type": "user.signup",
        "timestamp": "2024-01-15T10:30:00Z",
        "payload": {"user_id": 42}
    })
    assert response.status_code == 200
    assert response.json()["event_type"] == "user.signup"


def test_webhook_stores_event():
    client.post("/webhook", json={
        "event_type": "order.placed",
        "timestamp": "2024-01-15T10:30:00Z",
        "payload": {"order_id": "abc123"},
        "source": "shopify"
    })
    assert len(events) == 1
    assert events[0]["event_type"] == "order.placed"
    assert events[0]["source"] == "shopify"


def test_webhook_stores_multiple_events():
    for i in range(3):
        client.post("/webhook", json={
            "event_type": f"event.{i}",
            "timestamp": "2024-01-15T10:30:00Z",
            "payload": {"index": i}
        })
    assert len(events) == 3


# --- POST /webhook: invalid inputs ---

def test_webhook_missing_event_type():
    response = client.post("/webhook", json={
        "timestamp": "2024-01-15T10:30:00Z",
        "payload": {"key": "value"}
    })
    assert response.status_code == 422
    fields = [e["loc"] for e in response.json()["detail"]]
    assert ["body", "event_type"] in fields


def test_webhook_missing_timestamp():
    response = client.post("/webhook", json={
        "event_type": "payment.created",
        "payload": {"key": "value"}
    })
    assert response.status_code == 422
    fields = [e["loc"] for e in response.json()["detail"]]
    assert ["body", "timestamp"] in fields


def test_webhook_missing_payload():
    response = client.post("/webhook", json={
        "event_type": "payment.created",
        "timestamp": "2024-01-15T10:30:00Z"
    })
    assert response.status_code == 422
    fields = [e["loc"] for e in response.json()["detail"]]
    assert ["body", "payload"] in fields


def test_webhook_empty_event_type():
    response = client.post("/webhook", json={
        "event_type": "   ",
        "timestamp": "2024-01-15T10:30:00Z",
        "payload": {"key": "value"}
    })
    assert response.status_code == 422


def test_webhook_empty_payload():
    response = client.post("/webhook", json={
        "event_type": "payment.created",
        "timestamp": "2024-01-15T10:30:00Z",
        "payload": {}
    })
    assert response.status_code == 422


def test_webhook_invalid_timestamp_format():
    response = client.post("/webhook", json={
        "event_type": "payment.created",
        "timestamp": "not-a-date",
        "payload": {"key": "value"}
    })
    assert response.status_code == 422


def test_webhook_payload_must_be_dict():
    response = client.post("/webhook", json={
        "event_type": "payment.created",
        "timestamp": "2024-01-15T10:30:00Z",
        "payload": "this is a string"
    })
    assert response.status_code == 422


def test_webhook_missing_all_required_fields():
    response = client.post("/webhook", json={})
    assert response.status_code == 422
    assert len(response.json()["detail"]) >= 3


def test_webhook_invalid_does_not_store_event():
    client.post("/webhook", json={
        "event_type": "payment.created",
        "timestamp": "bad-timestamp",
        "payload": {"key": "value"}
    })
    assert len(events) == 0


# --- GET /webhooks ---

def test_list_webhooks_empty():
    response = client.get("/webhooks")
    assert response.status_code == 200
    assert response.json() == {"count": 0, "events": []}


def test_list_webhooks_returns_stored_events():
    client.post("/webhook", json={
        "event_type": "payment.created",
        "timestamp": "2024-01-15T10:30:00Z",
        "payload": {"amount": 50},
        "source": "stripe"
    })
    response = client.get("/webhooks")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["events"][0]["event_type"] == "payment.created"
    assert data["events"][0]["source"] == "stripe"


def test_list_webhooks_count_matches_events():
    for i in range(5):
        client.post("/webhook", json={
            "event_type": f"event.{i}",
            "timestamp": "2024-01-15T10:30:00Z",
            "payload": {"i": i}
        })
    response = client.get("/webhooks")
    data = response.json()
    assert data["count"] == 5
    assert len(data["events"]) == 5
