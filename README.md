# webhook-validator

A lightweight webhook receiver built with FastAPI and Pydantic. Validates incoming payloads, rejects bad data with field-level error messages, and stores valid events in memory.

Built with Claude as part of a vibe-coding workflow.

## Stack

- **FastAPI** — API framework
- **Pydantic v2** — payload validation
- **Uvicorn** — ASGI server

## Setup

```bash
pip install fastapi uvicorn pydantic pytest httpx
```

## Run

```bash
uvicorn main:app --reload
```

API docs available at: `http://localhost:8000/docs`

---

## Testing

Tests are written with `pytest` and FastAPI's built-in `TestClient` (powered by `httpx`). No running server needed — the test client runs the app in-process.

### Run all tests

```bash
pytest test_main.py -v
```

### Expected output

```
test_main.py::test_health_check PASSED
test_main.py::test_webhook_valid_full_payload PASSED
test_main.py::test_webhook_valid_without_optional_source PASSED
test_main.py::test_webhook_stores_event PASSED
test_main.py::test_webhook_stores_multiple_events PASSED
test_main.py::test_webhook_missing_event_type PASSED
test_main.py::test_webhook_missing_timestamp PASSED
test_main.py::test_webhook_missing_payload PASSED
test_main.py::test_webhook_empty_event_type PASSED
test_main.py::test_webhook_empty_payload PASSED
test_main.py::test_webhook_invalid_timestamp_format PASSED
test_main.py::test_webhook_payload_must_be_dict PASSED
test_main.py::test_webhook_missing_all_required_fields PASSED
test_main.py::test_webhook_invalid_does_not_store_event PASSED
test_main.py::test_list_webhooks_empty PASSED
test_main.py::test_list_webhooks_returns_stored_events PASSED
test_main.py::test_list_webhooks_count_matches_events PASSED

17 passed in 0.XXs
```

### Run a specific test

```bash
pytest test_main.py::test_webhook_valid_full_payload -v
```

### What's covered

| Area | Tests |
|---|---|
| `GET /health` | Status 200, correct response body |
| `POST /webhook` valid | Full payload, optional field omitted, event stored, multiple events |
| `POST /webhook` invalid | Missing each required field, empty strings, bad timestamp, wrong payload type, all fields missing, invalid input not stored |
| `GET /webhooks` | Empty list, correct events returned, count matches |

> Each test runs against a clean slate — a `pytest` fixture clears the in-memory events list before and after every test automatically.

---

## Endpoints

### `GET /health`
Simple uptime check.

```bash
curl http://localhost:8000/health
```
```json
{ "status": "ok" }
```

---

### `POST /webhook`
Validates and stores an incoming webhook event.

**Valid request:**
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "payment.created",
    "timestamp": "2024-01-15T10:30:00Z",
    "payload": {"amount": 99.99, "currency": "USD"},
    "source": "stripe"
  }'
```
```json
{
  "message": "Webhook received successfully",
  "event_type": "payment.created",
  "timestamp": "2024-01-15T10:30:00+00:00"
}
```

**Invalid request (missing required field):**
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"event_type": "payment.created"}'
```
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "timestamp"],
      "msg": "Field required"
    },
    {
      "type": "missing",
      "loc": ["body", "payload"],
      "msg": "Field required"
    }
  ]
}
```

---

### `GET /webhooks`
Returns all stored valid events.

```bash
curl http://localhost:8000/webhooks
```
```json
{
  "count": 1,
  "events": [
    {
      "event_type": "payment.created",
      "timestamp": "2024-01-15T10:30:00+00:00",
      "payload": {"amount": 99.99, "currency": "USD"},
      "source": "stripe"
    }
  ]
}
```

---

## Pydantic Model

```python
class WebhookEvent(BaseModel):
    event_type: str        # required
    timestamp: datetime    # required, auto-parsed from ISO 8601
    payload: dict          # required, must not be empty
    source: Optional[str]  # optional
```

FastAPI automatically returns `422 Unprocessable Entity` with field-level detail on validation failure — no extra error handling code needed.

---

## Code Review: Common Pydantic Mistake

```python
# Broken
user_data = {"name": "John", ";email": "john@email", "age": "25"}
user = User(user_data)

# Fixed
user_data = {"name": "John", "email": "john@example.com", "age": 25}
user = User(**user_data)
```

**Issues in the original:**
1. Semicolon typo in `";email"` key
2. Invalid email format (`john@email` has no TLD)
3. `age` passed as a string `"25"` instead of an integer `25`
4. `User(user_data)` passes a dict as a positional arg — Pydantic requires `**` unpacking
