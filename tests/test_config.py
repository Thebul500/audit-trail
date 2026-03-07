"""Tests for application configuration."""

import os
from unittest.mock import patch

from audit_trail.config import Settings, settings


def test_default_settings():
    """Settings have expected defaults."""
    s = Settings()
    assert "sqlite+aiosqlite" in s.database_url
    assert s.secret_key == "change-me-in-production"
    assert s.access_token_expire_minutes == 30
    assert s.debug is False


def test_settings_from_env():
    """Settings can be overridden via environment variables."""
    env = {
        "AUDIT_TRAIL_SECRET_KEY": "test-secret",
        "AUDIT_TRAIL_DEBUG": "true",
        "AUDIT_TRAIL_ACCESS_TOKEN_EXPIRE_MINUTES": "60",
    }
    with patch.dict(os.environ, env):
        s = Settings()
    assert s.secret_key == "test-secret"
    assert s.debug is True
    assert s.access_token_expire_minutes == 60


def test_module_level_settings_instance():
    """Module-level settings singleton exists."""
    assert isinstance(settings, Settings)
