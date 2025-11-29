"""Pydantic models for playbook structure validation."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class StepType(str, Enum):
    """Type of step in a playbook."""

    SKILL = "skill"
    DECISION = "decision"


class SkillStep(BaseModel):
    """A skill execution step in a playbook."""

    type: StepType = Field(default=StepType.SKILL)
    name: str = Field(..., description="Name of this step")
    skill: str = Field(..., description="Name of the skill to execute")
    input: Dict[str, Any] = Field(
        default_factory=dict, description="Input parameters for the skill"
    )
    output_var: Optional[str] = Field(None, description="Variable name to store output")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: StepType) -> StepType:
        """Ensure type is SKILL."""
        if v != StepType.SKILL:
            raise ValueError(f"SkillStep must have type='{StepType.SKILL.value}'")
        return v


class DecisionBranch(BaseModel):
    """A branch in a decision step."""

    condition: str = Field(..., description="Jinja2 template condition to evaluate")
    steps: List["Step"] = Field(
        default_factory=list, description="Steps to execute if condition is true"
    )


class DecisionStep(BaseModel):
    """A decision/branching step in a playbook."""

    type: StepType = Field(default=StepType.DECISION)
    name: str = Field(..., description="Name of this decision step")
    branches: List[DecisionBranch] = Field(
        ..., description="List of conditional branches"
    )
    default: Optional[List["Step"]] = Field(
        None, description="Default steps if no condition matches"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: StepType) -> StepType:
        """Ensure type is DECISION."""
        if v != StepType.DECISION:
            raise ValueError(f"DecisionStep must have type='{StepType.DECISION.value}'")
        return v


# Union type for all step types
Step = Union[SkillStep, DecisionStep]

# Update forward references
DecisionBranch.model_rebuild()
DecisionStep.model_rebuild()


class PlaybookMetadata(BaseModel):
    """Metadata about a playbook."""

    name: str = Field(..., description="Unique name of the playbook")
    version: str = Field(default="1.0.0", description="Semantic version")
    description: Optional[str] = Field(None, description="Human-readable description")
    author: Optional[str] = Field(None, description="Author of the playbook")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class Playbook(BaseModel):
    """
    A complete playbook definition.

    A playbook is a sequence of steps that orchestrate skills and decisions
    to accomplish a complex task in a governable, auditable way.
    """

    metadata: PlaybookMetadata = Field(..., description="Playbook metadata")
    variables: Dict[str, Any] = Field(
        default_factory=dict, description="Template variables"
    )
    steps: List[Step] = Field(..., description="Sequential steps to execute")

    @field_validator("steps")
    @classmethod
    def validate_steps_not_empty(cls, v: List[Step]) -> List[Step]:
        """Ensure playbook has at least one step."""
        if not v:
            raise ValueError("Playbook must have at least one step")
        return v

    def __repr__(self) -> str:
        return f"<Playbook name='{self.metadata.name}' version='{self.metadata.version}' steps={len(self.steps)}>"
