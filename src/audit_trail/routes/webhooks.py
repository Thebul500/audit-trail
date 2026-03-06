"""Webhook subscription endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import WebhookSubscription
from ..schemas import WebhookCreate, WebhookResponse

router = APIRouter(prefix="/api/v1", tags=["webhooks"])


@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook_in: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    webhook = WebhookSubscription(
        url=webhook_in.url,
        event_filter=webhook_in.event_filter,
        secret=webhook_in.secret,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return webhook


@router.get("/webhooks", response_model=list[WebhookResponse])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(WebhookSubscription))
    return result.scalars().all()


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )
    await db.delete(webhook)
    await db.commit()
