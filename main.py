from fastapi import FastAPI
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
import re

app = FastAPI(title="Webhook Validator")

# In-memory store for valid events
events: list[dict] = []


# --- Pydantic Model ---

class WebhookEvent(BaseModel):
    event_type: str
    timestamp: datetime
    payload: dict
    source: Optional[str] = None

    @field_validator("event_type")
    @classmethod
    def event_type_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("event_type must not be empty")
        return v

    @field_validator("payload")
    @classmethod
    def payload_must_not_be_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("payload must not be empty")
        return v


# --- Routes ---

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/webhook", status_code=200)
def receive_webhook(event: WebhookEvent):
    stored = {
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "payload": event.payload,
        "source": event.source,
    }
    events.append(stored)
    return {
        "message": "Webhook received successfully",
        "event_type": event.event_type,
        "timestamp": stored["timestamp"],
    }


@app.get("/webhooks")
def list_webhooks():
    return {"count": len(events), "events": events}
