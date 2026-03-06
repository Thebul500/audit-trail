"""Audit event endpoints."""

import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import AuditEvent
from ..schemas import EventCreate, EventList, EventResponse

router = APIRouter(prefix="/api/v1", tags=["events"])


def compute_hash(
    previous_hash: str,
    stream_id: str,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str,
    payload: dict,
    created_at: datetime,
) -> str:
    data = (
        f"{previous_hash}{stream_id}{actor}{action}"
        f"{resource_type}{resource_id}"
        f"{json.dumps(payload, sort_keys=True)}{created_at.isoformat()}"
    )
    return hashlib.sha256(data.encode()).hexdigest()


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: EventCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.stream_id == event_in.stream_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(1)
    )
    last_event = result.scalar_one_or_none()
    previous_hash = last_event.hash if last_event else "0" * 64

    now = datetime.now(timezone.utc)
    event_hash = compute_hash(
        previous_hash,
        event_in.stream_id,
        event_in.actor,
        event_in.action,
        event_in.resource_type,
        event_in.resource_id,
        event_in.payload,
        now,
    )

    event = AuditEvent(
        stream_id=event_in.stream_id,
        actor=event_in.actor,
        action=event_in.action,
        resource_type=event_in.resource_type,
        resource_id=event_in.resource_id,
        payload=event_in.payload,
        hash=event_hash,
        previous_hash=previous_hash,
        created_at=now,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("/events", response_model=EventList)
async def list_events(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(AuditEvent).offset(skip).limit(limit))
    events = result.scalars().all()
    count_result = await db.execute(select(func.count()).select_from(AuditEvent))
    total = count_result.scalar()
    return EventList(items=events, total=total)


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(AuditEvent).where(AuditEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event
