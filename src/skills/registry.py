"""Skill Registry - registration and discovery of skills."""

from typing import Dict, Optional, Type

from .base import Skill


class SkillRegistry:
    """
    Registry for skill classes.

    Allows registration and lookup of skills by name.

    Example:
        registry = SkillRegistry()

        @registry.register
        class MySkill(Skill):
            name = "my_skill"
            ...

        # Later
        skill_class = registry.get("my_skill")
        skill = skill_class()
        output, trace = await skill.run({"input": "value"})
    """

    _instance: Optional["SkillRegistry"] = None

    def __init__(self) -> None:
        self._skills: Dict[str, Type[Skill]] = {}

    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        """Get the global registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, skill_class: Type[Skill]) -> Type[Skill]:
        """
        Register a skill class.

        Can be used as a decorator:
            @registry.register
            class MySkill(Skill):
                ...

        Or called directly:
            registry.register(MySkill)
        """
        if not issubclass(skill_class, Skill):
            raise TypeError(f"{skill_class} must be a subclass of Skill")

        name = skill_class.name
        if name in self._skills:
            raise ValueError(f"Skill '{name}' is already registered")

        self._skills[name] = skill_class
        return skill_class

    def get(self, name: str) -> Optional[Type[Skill]]:
        """Get a skill class by name."""
        return self._skills.get(name)

    def get_or_raise(self, name: str) -> Type[Skill]:
        """Get a skill class by name, raising if not found."""
        skill_class = self.get(name)
        if skill_class is None:
            raise KeyError(f"Skill '{name}' not found in registry")
        return skill_class

    def list_skills(self) -> list[str]:
        """List all registered skill names."""
        return list(self._skills.keys())

    def clear(self) -> None:
        """Clear all registered skills (mainly for testing)."""
        self._skills.clear()

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def __len__(self) -> int:
        return len(self._skills)


# Global registry instance
_global_registry = SkillRegistry()


def skill(cls: Type[Skill]) -> Type[Skill]:
    """
    Decorator to register a skill with the global registry.

    Example:
        @skill
        class MySkill(Skill):
            name = "my_skill"
            ...
    """
    return _global_registry.register(cls)


def get_skill(name: str) -> Type[Skill]:
    """Get a skill from the global registry."""
    return _global_registry.get_or_raise(name)


def list_skills() -> list[str]:
    """List all skills in the global registry."""
    return _global_registry.list_skills()
