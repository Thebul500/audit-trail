"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: datetime


# --- Events ---


class EventCreate(BaseModel):
    stream_id: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    payload: dict[str, Any] = {}


class EventResponse(BaseModel):
    id: str
    stream_id: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    payload: dict[str, Any]
    hash: str
    previous_hash: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EventList(BaseModel):
    items: list[EventResponse]
    total: int


# --- Auth ---


class RegisterRequest(BaseModel):
    name: str
    scopes: list[str] = ["events:read"]


class RegisterResponse(BaseModel):
    id: str
    name: str
    api_key: str


class TokenRequest(BaseModel):
    api_key: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Retention Policies ---


class RetentionPolicyCreate(BaseModel):
    stream_id: str
    max_age_days: int


class RetentionPolicyUpdate(BaseModel):
    stream_id: str | None = None
    max_age_days: int | None = None
    is_active: bool | None = None


class RetentionPolicyResponse(BaseModel):
    id: str
    stream_id: str
    max_age_days: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Webhooks ---


class WebhookCreate(BaseModel):
    url: str
    event_filter: str
    secret: str | None = None


class WebhookResponse(BaseModel):
    id: str
    url: str
    event_filter: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
