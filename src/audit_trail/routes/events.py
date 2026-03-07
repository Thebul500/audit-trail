"""Audit event endpoints."""

import csv
import hashlib
import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import AuditEvent
from ..schemas import EventCreate, EventList, EventResponse, VerifyResponse

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
    previous_hash: str = str(last_event.hash) if last_event else "0" * 64

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
    stream_id: str | None = None,
    actor: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    query = select(AuditEvent)
    count_query = select(func.count()).select_from(AuditEvent)

    if stream_id:
        query = query.where(AuditEvent.stream_id == stream_id)
        count_query = count_query.where(AuditEvent.stream_id == stream_id)
    if actor:
        query = query.where(AuditEvent.actor == actor)
        count_query = count_query.where(AuditEvent.actor == actor)
    if action:
        query = query.where(AuditEvent.action == action)
        count_query = count_query.where(AuditEvent.action == action)
    if resource_type:
        query = query.where(AuditEvent.resource_type == resource_type)
        count_query = count_query.where(AuditEvent.resource_type == resource_type)
    if resource_id:
        query = query.where(AuditEvent.resource_id == resource_id)
        count_query = count_query.where(AuditEvent.resource_id == resource_id)
    if since:
        query = query.where(AuditEvent.created_at >= since)
        count_query = count_query.where(AuditEvent.created_at >= since)
    if until:
        query = query.where(AuditEvent.created_at <= until)
        count_query = count_query.where(AuditEvent.created_at <= until)

    query = query.order_by(AuditEvent.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    events = result.scalars().all()
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    return EventList(items=list(events), total=total or 0)  # type: ignore[arg-type]


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


@router.get("/streams/{stream_id}/verify", response_model=VerifyResponse)
async def verify_stream(
    stream_id: str,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Verify the hash chain integrity for a stream."""
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.stream_id == stream_id)
        .order_by(AuditEvent.created_at.asc())
    )
    events = result.scalars().all()

    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No events found for stream '{stream_id}'",
        )

    broken_links: list[dict] = []
    for i, event in enumerate(events):
        if i == 0:
            expected_previous = "0" * 64
        else:
            expected_previous = str(events[i - 1].hash)

        if str(event.previous_hash) != expected_previous:
            broken_links.append({
                "event_id": str(event.id),
                "position": i,
                "expected_previous_hash": expected_previous,
                "actual_previous_hash": str(event.previous_hash),
            })

        created_at = event.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        expected_hash = compute_hash(
            str(event.previous_hash),
            str(event.stream_id),
            str(event.actor),
            str(event.action),
            str(event.resource_type),
            str(event.resource_id),
            event.payload or {},
            created_at,
        )
        if str(event.hash) != expected_hash:
            broken_links.append({
                "event_id": str(event.id),
                "position": i,
                "expected_hash": expected_hash,
                "actual_hash": str(event.hash),
            })

    return VerifyResponse(
        stream_id=stream_id,
        total_events=len(events),
        valid=len(broken_links) == 0,
        broken_links=broken_links,
    )


@router.get("/events/export/csv")
async def export_events_csv(
    stream_id: str | None = None,
    actor: str | None = None,
    action: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Export events as CSV."""
    query = select(AuditEvent)

    if stream_id:
        query = query.where(AuditEvent.stream_id == stream_id)
    if actor:
        query = query.where(AuditEvent.actor == actor)
    if action:
        query = query.where(AuditEvent.action == action)
    if since:
        query = query.where(AuditEvent.created_at >= since)
    if until:
        query = query.where(AuditEvent.created_at <= until)

    query = query.order_by(AuditEvent.created_at.desc())
    result = await db.execute(query)
    events = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "stream_id", "actor", "action", "resource_type",
        "resource_id", "payload", "hash", "previous_hash", "created_at",
    ])
    for event in events:
        writer.writerow([
            event.id, event.stream_id, event.actor, event.action,
            event.resource_type, event.resource_id,
            json.dumps(event.payload or {}),
            event.hash, event.previous_hash,
            event.created_at.isoformat() if event.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_events.csv"},
    )
