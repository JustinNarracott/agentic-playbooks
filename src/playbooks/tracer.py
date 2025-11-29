"""ExecutionTracer - captures and exports execution traces."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..skills.base import SkillTrace


class StepTrace:
    """
    Trace of a single step execution.

    Captures all relevant information about a step's execution including
    timing, inputs/outputs, decisions, and any errors.
    """

    def __init__(
        self,
        step_name: str,
        step_type: str,
        started_at: datetime,
    ) -> None:
        """
        Initialize step trace.

        Args:
            step_name: Name of the step
            step_type: Type of step (skill, decision, etc.)
            started_at: When step execution started
        """
        self.step_name = step_name
        self.step_type = step_type
        self.started_at = started_at
        self.completed_at: Optional[datetime] = None
        self.duration_ms: Optional[int] = None
        self.skill_trace: Optional[SkillTrace] = None
        self.decision_taken: Optional[str] = None
        self.error: Optional[str] = None
        self.nested_steps: List["StepTrace"] = []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert step trace to dictionary for JSON serialization.

        Returns:
            Dictionary representation of step trace
        """
        result: Dict[str, Any] = {
            "step_name": self.step_name,
            "step_type": self.step_type,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "duration_ms": self.duration_ms,
            "decision_taken": self.decision_taken,
            "error": self.error,
        }

        # Add skill trace if present
        if self.skill_trace:
            result["skill_trace"] = {
                "skill_name": self.skill_trace.skill_name,
                "execution_id": self.skill_trace.execution_id,
                "input": self.skill_trace.input,
                "output": self.skill_trace.output,
                "reasoning": self.skill_trace.reasoning,
                "started_at": self.skill_trace.started_at.isoformat(),
                "completed_at": (
                    self.skill_trace.completed_at.isoformat()
                    if self.skill_trace.completed_at
                    else None
                ),
                "duration_ms": self.skill_trace.duration_ms,
                "error": self.skill_trace.error,
            }

        # Add nested steps if present
        if self.nested_steps:
            result["nested_steps"] = [step.to_dict() for step in self.nested_steps]

        return result


class ExecutionTrace:
    """
    Complete trace of playbook execution.

    Captures the entire execution flow including all steps, timing,
    final context, and success/error status.
    """

    def __init__(self, playbook_name: str, execution_id: str) -> None:
        """
        Initialize execution trace.

        Args:
            playbook_name: Name of the playbook being executed
            execution_id: Unique identifier for this execution
        """
        self.playbook_name = playbook_name
        self.execution_id = execution_id
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.duration_ms: Optional[int] = None
        self.steps: List[StepTrace] = []
        self.final_context: Dict[str, Any] = {}
        self.error: Optional[str] = None
        self.success: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert execution trace to dictionary for JSON serialization.

        Returns:
            Dictionary representation of execution trace
        """
        return {
            "playbook_name": self.playbook_name,
            "execution_id": self.execution_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "steps": [step.to_dict() for step in self.steps],
            "final_context": self.final_context,
        }

    def to_json(self, indent: Optional[int] = 2) -> str:
        """
        Export execution trace as JSON string.

        Args:
            indent: Number of spaces for indentation (None for compact JSON)

        Returns:
            JSON string representation of execution trace
        """
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, filepath: str, indent: Optional[int] = 2) -> None:
        """
        Save execution trace to a JSON file.

        Args:
            filepath: Path to save the JSON file
            indent: Number of spaces for indentation
        """
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json(indent=indent))


class ExecutionTracer:
    """
    Tracer for capturing playbook execution traces.

    This class provides utilities for working with execution traces,
    including creation, management, and export functionality.
    """

    @staticmethod
    def create_trace(playbook_name: str, execution_id: str) -> ExecutionTrace:
        """
        Create a new execution trace.

        Args:
            playbook_name: Name of the playbook
            execution_id: Unique execution identifier

        Returns:
            New ExecutionTrace instance
        """
        return ExecutionTrace(playbook_name, execution_id)

    @staticmethod
    def create_step_trace(
        step_name: str, step_type: str, started_at: Optional[datetime] = None
    ) -> StepTrace:
        """
        Create a new step trace.

        Args:
            step_name: Name of the step
            step_type: Type of the step
            started_at: Start time (defaults to now)

        Returns:
            New StepTrace instance
        """
        if started_at is None:
            started_at = datetime.utcnow()
        return StepTrace(step_name, step_type, started_at)

    @staticmethod
    def load_from_json(json_str: str) -> Dict[str, Any]:
        """
        Load execution trace from JSON string.

        Args:
            json_str: JSON string representation

        Returns:
            Dictionary representation of the trace
        """
        result: Dict[str, Any] = json.loads(json_str)
        return result

    @staticmethod
    def load_from_file(filepath: str) -> Dict[str, Any]:
        """
        Load execution trace from JSON file.

        Args:
            filepath: Path to the JSON file

        Returns:
            Dictionary representation of the trace
        """
        with open(filepath, "r", encoding="utf-8") as f:
            result: Dict[str, Any] = json.load(f)
            return result
