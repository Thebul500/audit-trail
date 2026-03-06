"""Authentication endpoints."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import create_access_token, hash_key, verify_key
from ..database import get_db
from ..models import APIKey
from ..schemas import RegisterRequest, RegisterResponse, TokenRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.name == req.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Name already registered"
        )

    raw_key = secrets.token_urlsafe(32)
    api_key = APIKey(
        name=req.name,
        key_hash=hash_key(raw_key),
        scopes=req.scopes,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return RegisterResponse(id=str(api_key.id), name=str(api_key.name), api_key=raw_key)


@router.post("/token", response_model=TokenResponse)
async def get_token(req: TokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.is_active.is_(True)))
    keys = result.scalars().all()

    for key in keys:
        if verify_key(req.api_key, str(key.key_hash)):
            token = create_access_token({"sub": key.id, "scopes": key.scopes})
            return TokenResponse(access_token=token)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
    )
