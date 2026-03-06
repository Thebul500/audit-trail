"""Tests for SQLAlchemy models."""

from sqlalchemy import inspect

from audit_trail.database import Base
from audit_trail.models import BaseModel


def test_base_model_is_abstract():
    """BaseModel is declared abstract."""
    assert BaseModel.__abstract__ is True


def test_base_model_columns():
    """BaseModel defines id, created_at, updated_at columns."""
    col_names = {name for name, _ in BaseModel.__dict__.items() if not name.startswith("_")}
    assert "id" in col_names
    assert "created_at" in col_names
    assert "updated_at" in col_names


def test_base_model_inherits_base():
    """BaseModel inherits from declarative Base."""
    assert issubclass(BaseModel, Base)
