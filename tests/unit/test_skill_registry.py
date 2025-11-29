"""Tests for the Skill Registry."""

from typing import Any, Dict

import pytest

from src.skills.base import Skill
from src.skills.registry import SkillRegistry


class DummySkill(Skill):
    """Dummy skill for testing."""

    name = "dummy"
    version = "1.0.0"
    description = "A dummy skill"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return {"dummy": True}


class AnotherSkill(Skill):
    """Another skill for testing."""

    name = "another"
    version = "1.0.0"
    description = "Another skill"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return {"another": True}


class TestSkillRegistry:
    """Tests for SkillRegistry."""

    def test_register_skill(self):
        """Test registering a skill."""
        registry = SkillRegistry()
        registry.register(DummySkill)

        assert "dummy" in registry
        assert registry.get("dummy") == DummySkill

    def test_register_duplicate_raises(self):
        """Test that registering duplicate raises error."""
        registry = SkillRegistry()
        registry.register(DummySkill)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(DummySkill)

    def test_get_nonexistent_returns_none(self):
        """Test that getting nonexistent skill returns None."""
        registry = SkillRegistry()
        assert registry.get("nonexistent") is None

    def test_get_or_raise(self):
        """Test get_or_raise behavior."""
        registry = SkillRegistry()
        registry.register(DummySkill)

        # Should work for registered skill
        assert registry.get_or_raise("dummy") == DummySkill

        # Should raise for unregistered
        with pytest.raises(KeyError, match="not found"):
            registry.get_or_raise("nonexistent")

    def test_list_skills(self):
        """Test listing registered skills."""
        registry = SkillRegistry()
        registry.register(DummySkill)
        registry.register(AnotherSkill)

        skills = registry.list_skills()
        assert "dummy" in skills
        assert "another" in skills
        assert len(skills) == 2

    def test_decorator_registration(self):
        """Test using register as decorator."""
        registry = SkillRegistry()

        @registry.register
        class DecoratedSkill(Skill):
            name = "decorated"
            version = "1.0.0"

            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                return {}

        assert "decorated" in registry
        assert registry.get("decorated") == DecoratedSkill

    def test_clear(self):
        """Test clearing the registry."""
        registry = SkillRegistry()
        registry.register(DummySkill)
        assert len(registry) == 1

        registry.clear()
        assert len(registry) == 0
