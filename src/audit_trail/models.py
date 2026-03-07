"""SQLAlchemy database models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String
from sqlalchemy.sql import func

from .database import Base


class BaseModel(Base):
    """Abstract base with common fields."""

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AuditEvent(Base):
    """Immutable audit event with hash chain."""

    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stream_id = Column(String(255), nullable=False, index=True)
    actor = Column(String(255), nullable=False)
    action = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(255), nullable=False)
    resource_id = Column(String(255), nullable=False)
    payload = Column(JSON, default=dict)
    hash = Column(String(64), nullable=False)
    previous_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class APIKey(Base):
    """API key for service authentication."""

    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    key_hash = Column(String(128), nullable=False)
    scopes = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class RetentionPolicy(Base):
    """Retention policy for event cleanup."""

    __tablename__ = "retention_policies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stream_id = Column(String(255), nullable=False)
    max_age_days = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class WebhookSubscription(Base):
    """Webhook subscription for event notifications."""

    __tablename__ = "webhook_subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(String(2048), nullable=False)
    secret = Column(String(255), nullable=True)
    event_filter = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
