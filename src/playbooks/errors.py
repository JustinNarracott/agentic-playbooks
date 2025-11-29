"""Custom exceptions for playbook execution with enhanced error context."""

from difflib import get_close_matches
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError


class PlaybookExecutionError(Exception):
    """Base exception for playbook execution errors."""

    pass


class SkillNotFoundError(PlaybookExecutionError):
    """
    Raised when a skill is not found in the registry.

    Provides suggestions for close matches and lists available skills.
    """

    def __init__(
        self,
        skill_name: str,
        step_name: str,
        available_skills: List[str],
        playbook_name: str,
    ):
        """
        Initialize SkillNotFoundError.

        Args:
            skill_name: The skill name that was not found
            step_name: The step where the error occurred
            available_skills: List of all registered skill names
            playbook_name: The playbook being executed
        """
        self.skill_name = skill_name
        self.step_name = step_name
        self.available_skills = available_skills
        self.playbook_name = playbook_name

        # Find close matches using Levenshtein distance
        suggestions = get_close_matches(skill_name, available_skills, n=3, cutoff=0.6)

        message = f"Skill '{skill_name}' not found in registry\n"
        message += f"  Playbook: {playbook_name}\n"
        message += f"  Step: {step_name}\n\n"

        if suggestions:
            message += "Did you mean one of these?\n"
            for suggestion in suggestions:
                message += f"  - {suggestion}\n"
            message += "\n"

        message += f"Available skills ({len(available_skills)}):\n"
        for skill in sorted(available_skills):
            message += f"  - {skill}\n"

        message += "\nTip: Register your skill with:\n"
        message += "  registry = SkillRegistry.get_instance()\n"
        message += "  registry.register(YourSkillClass)\n"

        super().__init__(message)


class TemplateError(PlaybookExecutionError):
    """
    Raised when a Jinja2 template fails to render.

    Provides template context and available variables to aid debugging.
    """

    def __init__(
        self,
        template_str: str,
        error: Exception,
        step_name: str,
        field_name: str,
        available_vars: Dict[str, Any],
    ):
        """
        Initialize TemplateError.

        Args:
            template_str: The template string that failed
            error: The original exception
            step_name: The step where the error occurred
            field_name: The field name containing the template
            available_vars: Dictionary of variables available for templating
        """
        self.template_str = template_str
        self.original_error = error
        self.step_name = step_name
        self.field_name = field_name
        self.available_vars = available_vars

        message = f"Template error in step '{step_name}', field '{field_name}'\n"
        message += f"  Template: {template_str}\n"
        message += f"  Error: {type(error).__name__}: {error}\n\n"

        message += "Available variables:\n"
        if available_vars:
            for key, value in sorted(available_vars.items()):
                # Truncate long values for readability
                value_str = str(value)
                if len(value_str) > 80:
                    value_preview = value_str[:77] + "..."
                else:
                    value_preview = value_str

                # Show type for objects
                if isinstance(value, dict):
                    message += f"  - {key}: dict with {len(value)} keys\n"
                elif isinstance(value, list):
                    message += f"  - {key}: list with {len(value)} items\n"
                else:
                    message += f"  - {key}: {value_preview}\n"
        else:
            message += "  (no variables available)\n"

        message += "\nTip: Check variable names and ensure data is available from previous steps.\n"

        super().__init__(message)


class SkillExecutionError(PlaybookExecutionError):
    """
    Raised when a skill's execute() method fails.

    Includes full execution trace and input data for debugging.
    """

    def __init__(
        self,
        skill_name: str,
        step_name: str,
        input_data: Dict[str, Any],
        original_error: Exception,
        reasoning: Optional[str] = None,
    ):
        """
        Initialize SkillExecutionError.

        Args:
            skill_name: The skill that failed
            step_name: The step where the error occurred
            input_data: The input data passed to the skill
            original_error: The original exception raised by the skill
            reasoning: Optional reasoning from the skill trace
        """
        self.skill_name = skill_name
        self.step_name = step_name
        self.input_data = input_data
        self.original_error = original_error
        self.reasoning = reasoning

        message = f"Skill execution failed: {skill_name}\n"
        message += f"  Step: {step_name}\n"
        message += f"  Error: {type(original_error).__name__}: {original_error}\n\n"

        message += "Input data:\n"
        message += self._format_dict(input_data, indent=2)
        message += "\n"

        if reasoning:
            message += "\nSkill reasoning:\n"
            message += f"  {reasoning}\n"

        message += (
            "\nTip: Check the skill's execute() method and input data validation.\n"
        )

        super().__init__(message)

    def _format_dict(self, d: Dict[str, Any], indent: int = 0) -> str:
        """Format dictionary for readable error messages."""
        lines = []
        prefix = " " * indent

        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._format_dict(value, indent + 2))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}: [{len(value)} items]")
            else:
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:97] + "..."
                lines.append(f"{prefix}{key}: {value_str}")

        return "\n".join(lines)


class InvalidInputError(PlaybookExecutionError):
    """
    Raised when skill input validation fails.

    Provides detailed Pydantic validation errors.
    """

    def __init__(
        self,
        skill_name: str,
        schema: Type[BaseModel],
        input_data: Dict[str, Any],
        validation_error: ValidationError,
    ):
        """
        Initialize InvalidInputError.

        Args:
            skill_name: The skill that failed validation
            schema: The Pydantic schema used for validation
            input_data: The input data that failed validation
            validation_error: The Pydantic ValidationError
        """
        self.skill_name = skill_name
        self.schema = schema
        self.input_data = input_data
        self.validation_error = validation_error

        message = f"Invalid input for skill '{skill_name}'\n"
        message += f"  Schema: {schema.__name__}\n\n"

        message += "Validation errors:\n"
        for error in validation_error.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            message += f"  - {field}: {error['msg']}\n"

        message += "\nInput data:\n"
        for key, value in input_data.items():
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."
            message += f"  {key}: {value_str}\n"

        message += "\nTip: Check input data types and required fields.\n"

        super().__init__(message)


class CheckpointError(PlaybookExecutionError):
    """
    Raised when checkpoint save/load operations fail.
    """

    def __init__(self, operation: str, execution_id: str, original_error: Exception):
        """
        Initialize CheckpointError.

        Args:
            operation: The operation that failed (save/load)
            execution_id: The execution ID
            original_error: The original exception
        """
        self.operation = operation
        self.execution_id = execution_id
        self.original_error = original_error

        message = f"Checkpoint {operation} failed for execution '{execution_id}'\n"
        message += f"  Error: {type(original_error).__name__}: {original_error}\n"

        super().__init__(message)
