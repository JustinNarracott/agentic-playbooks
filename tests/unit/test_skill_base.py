"""Tests for the base Skill class."""

from typing import Any, Dict

import pytest

from src.skills.base import Skill


class EchoSkill(Skill):
    """Simple test skill that echoes input."""

    name = "echo"
    version = "1.0.0"
    description = "Echoes input back as output"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return {"echoed": input}


class FailingSkill(Skill):
    """Skill that always fails."""

    name = "failing"
    version = "1.0.0"
    description = "Always fails"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("Intentional failure")


class TestSkill:
    """Tests for Skill base class."""

    @pytest.mark.asyncio
    async def test_skill_execute(self):
        """Test basic skill execution."""
        skill = EchoSkill()
        output, trace = await skill.run({"message": "hello"})

        assert output == {"echoed": {"message": "hello"}}
        assert trace.skill_name == "echo"
        assert trace.output == output
        assert trace.error is None

    @pytest.mark.asyncio
    async def test_skill_trace_timing(self):
        """Test that trace captures timing."""
        skill = EchoSkill()
        output, trace = await skill.run({"message": "hello"})

        assert trace.started_at is not None
        assert trace.completed_at is not None
        assert trace.duration_ms is not None
        assert trace.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_skill_failure_captured(self):
        """Test that failures are captured in trace."""
        skill = FailingSkill()

        with pytest.raises(ValueError, match="Intentional failure"):
            await skill.run({"any": "input"})

        trace = skill.get_trace()
        assert trace is not None
        assert trace.error == "Intentional failure"
        assert trace.output is None

    def test_skill_repr(self):
        """Test skill string representation."""
        skill = EchoSkill()
        assert repr(skill) == "<EchoSkill name='echo' version='1.0.0'>"
