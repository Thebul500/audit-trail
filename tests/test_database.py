"""Tests for database module."""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from audit_trail.database import Base, async_session, engine, get_db


def test_engine_is_async():
    """Engine is an async SQLAlchemy engine."""
    assert isinstance(engine, AsyncEngine)


def test_async_session_factory():
    """Session factory produces async sessions."""
    assert isinstance(async_session, async_sessionmaker)


def test_base_declarative():
    """Base is a valid declarative base."""
    assert hasattr(Base, "metadata")
    assert hasattr(Base, "__subclasses__")


@pytest.mark.asyncio
async def test_get_db_yields_session():
    """get_db yields an AsyncSession then closes it."""
    gen = get_db()
    session = await gen.__anext__()
    assert isinstance(session, AsyncSession)
    # Clean up - drive generator to completion
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()
