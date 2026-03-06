"""Retention policy endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import RetentionPolicy
from ..schemas import RetentionPolicyCreate, RetentionPolicyResponse, RetentionPolicyUpdate

router = APIRouter(prefix="/api/v1/retention", tags=["retention"])


@router.post(
    "/policies", response_model=RetentionPolicyResponse, status_code=status.HTTP_201_CREATED
)
async def create_policy(
    policy_in: RetentionPolicyCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    policy = RetentionPolicy(
        stream_id=policy_in.stream_id,
        max_age_days=policy_in.max_age_days,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.get("/policies", response_model=list[RetentionPolicyResponse])
async def list_policies(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(select(RetentionPolicy))
    return result.scalars().all()


@router.put("/policies/{policy_id}", response_model=RetentionPolicyResponse)
async def update_policy(
    policy_id: str,
    policy_in: RetentionPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(RetentionPolicy).where(RetentionPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found"
        )

    for field, value in policy_in.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)

    await db.commit()
    await db.refresh(policy)
    return policy
