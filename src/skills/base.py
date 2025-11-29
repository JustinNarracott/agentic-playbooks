"""Base Skill class - foundation for all skills."""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class SkillInput(BaseModel):
    """Base class for skill inputs."""

    pass


class SkillOutput(BaseModel):
    """Base class for skill outputs."""

    pass


class SkillTrace(BaseModel):
    """Trace of a skill execution."""

    skill_name: str
    execution_id: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class Skill(ABC):
    """
    Base class for all skills.

    A Skill is an atomic capability that does one thing well.
    Skills are composed into Playbooks for complex workflows.

    Example:
        class CompanyEnrichment(Skill):
            name = "company_enrichment"
            version = "1.0.0"
            description = "Enrich company data with firmographics"

            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                company_name = input["company_name"]
                # ... do enrichment logic
                return {"firmographics": {...}, "icp_score": 8.5}
    """

    name: str = "base_skill"
    version: str = "0.0.0"
    description: str = ""

    def __init__(self) -> None:
        self._trace: Optional[SkillTrace] = None

    @abstractmethod
    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the skill with given input.

        Args:
            input: Dictionary of input parameters

        Returns:
            Dictionary of output values
        """
        pass

    async def run(self, input: Dict[str, Any]) -> tuple[Dict[str, Any], SkillTrace]:
        """
        Run the skill with tracing.

        Args:
            input: Dictionary of input parameters

        Returns:
            Tuple of (output, trace)
        """
        execution_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        self._trace = SkillTrace(
            skill_name=self.name,
            execution_id=execution_id,
            input=input,
            started_at=started_at,
        )

        try:
            output = await self.execute(input)
            completed_at = datetime.utcnow()

            self._trace.output = output
            self._trace.completed_at = completed_at
            self._trace.duration_ms = int(
                (completed_at - started_at).total_seconds() * 1000
            )

            return output, self._trace

        except Exception as e:
            self._trace.error = str(e)
            self._trace.completed_at = datetime.utcnow()
            raise

    def get_trace(self) -> Optional[SkillTrace]:
        """Get the trace from the last execution."""
        return self._trace

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} name='{self.name}' version='{self.version}'>"
        )
