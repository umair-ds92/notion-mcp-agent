"""
tests/test_registry.py — Tool registry tests.

Verifies:
  - Notion is always included in the registry.
  - Gmail is only included when GMAIL_ENABLED=true.
  - Google Calendar is only included when GCAL_ENABLED=true.
  - Multiple tools can be enabled simultaneously.
"""

import pytest
from unittest.mock import patch


def _build(gmail=False, gcal=False):
    """Helper — rebuild the registry with the given flags."""
    with patch("config.GMAIL_ENABLED", gmail), \
         patch("config.GCAL_ENABLED", gcal):
        # Re-import to trigger _build_registry() with patched config
        import importlib
        import tools.registry as reg
        importlib.reload(reg)
        return reg.TOOL_REGISTRY


def test_notion_always_in_registry():
    registry = _build(gmail=False, gcal=False)
    names = [s.name for s in registry]
    assert "notion" in names


def test_gmail_excluded_by_default():
    registry = _build(gmail=False)
    names = [s.name for s in registry]
    assert "gmail" not in names


def test_gmail_included_when_enabled():
    registry = _build(gmail=True)
    names = [s.name for s in registry]
    assert "gmail" in names


def test_gcal_excluded_by_default():
    registry = _build(gcal=False)
    names = [s.name for s in registry]
    assert "google_calendar" not in names


def test_gcal_included_when_enabled():
    registry = _build(gcal=True)
    names = [s.name for s in registry]
    assert "google_calendar" in names


def test_all_tools_enabled_simultaneously():
    registry = _build(gmail=True, gcal=True)
    names = [s.name for s in registry]
    assert "notion" in names
    assert "gmail" in names
    assert "google_calendar" in names
    assert len(registry) == 3


def test_only_notion_by_default():
    registry = _build(gmail=False, gcal=False)
    assert len(registry) == 1
    assert registry[0].name == "notion"