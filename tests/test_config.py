"""
tests/test_config.py — Config validation tests.

Ensures validate() raises clearly when required secrets are absent
and passes silently when they are present.
"""

import pytest
from unittest.mock import patch


def test_validate_passes_when_all_keys_present():
    with patch("config.OPENAI_API_KEY", "sk-test"), \
         patch("config.NOTION_API_KEY", "ntn_test"):
        import config
        config.validate()  # should not raise


def test_validate_raises_when_openai_key_missing():
    with patch("config.OPENAI_API_KEY", ""), \
         patch("config.NOTION_API_KEY", "ntn_test"):
        import config
        with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
            config.validate()


def test_validate_raises_when_notion_key_missing():
    with patch("config.OPENAI_API_KEY", "sk-test"), \
         patch("config.NOTION_API_KEY", ""):
        import config
        with pytest.raises(EnvironmentError, match="NOTION_API_KEY"):
            config.validate()


def test_validate_raises_when_both_keys_missing():
    with patch("config.OPENAI_API_KEY", ""), \
         patch("config.NOTION_API_KEY", ""):
        import config
        with pytest.raises(EnvironmentError) as exc_info:
            config.validate()
        assert "OPENAI_API_KEY" in str(exc_info.value)
        assert "NOTION_API_KEY" in str(exc_info.value)
