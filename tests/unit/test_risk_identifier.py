"""Unit tests for RiskIdentifier skill."""

import os
from unittest.mock import patch

import pytest

from src.modules.governance.skills.risk_identifier import (
    RiskIdentifier,
)


class TestRiskIdentifier:
    """Test suite for RiskIdentifier skill."""

    def test_skill_metadata(self) -> None:
        """Test skill has correct metadata."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = RiskIdentifier()

            assert skill.name == "risk_identifier"
            assert skill.version == "1.0.0"
            assert (
                skill.description
                == "Analyze decision context to identify and assess risks"
            )

    def test_initialization_requires_api_key(self) -> None:
        """Test that initialization requires OPENAI_API_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                RiskIdentifier()
