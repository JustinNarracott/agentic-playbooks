"""PlaybookValidator - validates playbook definitions before execution."""

import argparse
import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from jinja2 import Environment, TemplateSyntaxError

from .loader import PlaybookLoader
from .models import DecisionStep, Playbook, SkillStep, Step


class ValidationLevel(Enum):
    """Validation message severity levels."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    SUCCESS = "SUCCESS"


@dataclass
class ValidationMessage:
    """A validation message with level and context."""

    level: ValidationLevel
    message: str
    step_name: Optional[str] = None
    field: Optional[str] = None

    def __str__(self) -> str:
        """Format message with color codes."""
        colors = {
            ValidationLevel.ERROR: "\033[91m",  # Red
            ValidationLevel.WARNING: "\033[93m",  # Yellow
            ValidationLevel.INFO: "\033[94m",  # Blue
            ValidationLevel.SUCCESS: "\033[92m",  # Green
        }
        reset = "\033[0m"
        color = colors.get(self.level, "")

        prefix = f"[{self.level.value}]"
        if self.step_name:
            prefix += f" Step '{self.step_name}'"
        if self.field:
            prefix += f" ({self.field})"

        return f"{color}{prefix}: {self.message}{reset}"


class PlaybookValidator:
    """
    Validate playbook definitions before execution.

    Checks:
    - Metadata completeness
    - Skill registration (optional)
    - Variable references
    - Decision condition syntax
    - Data flow analysis
    """

    def __init__(self, skill_registry: Optional[Any] = None) -> None:
        """
        Initialize validator.

        Args:
            skill_registry: Optional skill registry to validate against
        """
        self.skill_registry = skill_registry
        self.messages: List[ValidationMessage] = []
        self._jinja_env = Environment()

    def validate(self, playbook: Playbook) -> bool:
        """
        Validate a playbook.

        Args:
            playbook: The playbook to validate

        Returns:
            True if valid (no errors), False otherwise
        """
        self.messages = []

        # Run all validation checks
        self._validate_metadata(playbook)
        self._validate_skills(playbook)
        self._validate_variables(playbook)
        self._validate_conditions(playbook)
        self._validate_data_flow(playbook)

        # Check if any errors
        has_errors = any(m.level == ValidationLevel.ERROR for m in self.messages)

        if not has_errors and not self.messages:
            self.messages.append(
                ValidationMessage(
                    level=ValidationLevel.SUCCESS,
                    message="Playbook validation passed",
                )
            )

        return not has_errors

    def _validate_metadata(self, playbook: Playbook) -> None:
        """Validate playbook metadata."""
        metadata = playbook.metadata

        if not metadata.name or metadata.name.strip() == "":
            self.messages.append(
                ValidationMessage(
                    level=ValidationLevel.ERROR,
                    message="Playbook name is required",
                    field="metadata.name",
                )
            )

        if not metadata.version or metadata.version.strip() == "":
            self.messages.append(
                ValidationMessage(
                    level=ValidationLevel.ERROR,
                    message="Playbook version is required",
                    field="metadata.version",
                )
            )

        if not metadata.description or metadata.description.strip() == "":
            self.messages.append(
                ValidationMessage(
                    level=ValidationLevel.WARNING,
                    message="Playbook description is missing",
                    field="metadata.description",
                )
            )

    def _validate_skills(self, playbook: Playbook) -> None:
        """Validate skill steps reference registered skills."""
        if self.skill_registry is None:
            return  # Skip if no registry provided

        for step in self._get_all_steps(playbook.steps):
            if isinstance(step, SkillStep):
                if step.skill not in self.skill_registry:
                    self.messages.append(
                        ValidationMessage(
                            level=ValidationLevel.ERROR,
                            message=f"Skill '{step.skill}' is not registered",
                            step_name=step.name,
                            field="skill",
                        )
                    )

    def _validate_variables(self, playbook: Playbook) -> None:
        """Validate variable references in templates."""
        # Collect defined variables
        defined_vars: Set[str] = set()

        # Playbook variables
        if playbook.variables:
            defined_vars.update(playbook.variables.keys())

        # Process steps to track output variables and check input references
        for step in self._get_all_steps(playbook.steps):
            if isinstance(step, SkillStep):
                # Check input variable references
                if step.input:
                    self._check_template_vars(
                        step.input, defined_vars, step.name, "input"
                    )

                # Add output variable to defined set
                if step.output_var:
                    defined_vars.add(step.output_var)

            elif isinstance(step, DecisionStep):
                # Check condition variable references
                for i, branch in enumerate(step.branches):
                    self._check_condition_vars(
                        branch.condition, defined_vars, step.name, f"branches[{i}]"
                    )

    def _validate_conditions(self, playbook: Playbook) -> None:
        """Validate decision condition syntax."""
        for step in self._get_all_steps(playbook.steps):
            if isinstance(step, DecisionStep):
                for i, branch in enumerate(step.branches):
                    try:
                        # Try to parse condition as Jinja2 template
                        self._jinja_env.from_string(f"{{{{ {branch.condition} }}}}")
                    except TemplateSyntaxError as e:
                        self.messages.append(
                            ValidationMessage(
                                level=ValidationLevel.ERROR,
                                message=f"Invalid condition syntax: {e}",
                                step_name=step.name,
                                field=f"branches[{i}].condition",
                            )
                        )

    def _validate_data_flow(self, playbook: Playbook) -> None:
        """Analyze data flow and detect unused outputs."""
        # Collect all output variables
        output_vars: Dict[str, str] = {}  # var_name -> step_name

        for step in self._get_all_steps(playbook.steps):
            if isinstance(step, SkillStep) and step.output_var:
                output_vars[step.output_var] = step.name

        # Collect all referenced variables
        referenced_vars: Set[str] = set()

        for step in self._get_all_steps(playbook.steps):
            if isinstance(step, SkillStep) and step.input:
                referenced_vars.update(self._extract_template_vars(step.input))
            elif isinstance(step, DecisionStep):
                for branch in step.branches:
                    referenced_vars.update(
                        self._extract_condition_vars(branch.condition)
                    )

        # Check for unused outputs
        for var_name, step_name in output_vars.items():
            if var_name not in referenced_vars:
                self.messages.append(
                    ValidationMessage(
                        level=ValidationLevel.WARNING,
                        message=f"Output variable '{var_name}' is never used",
                        step_name=step_name,
                        field="output_var",
                    )
                )

    def _get_all_steps(self, steps: List[Step]) -> List[Step]:
        """Recursively get all steps including nested ones."""
        all_steps: List[Step] = []

        for step in steps:
            all_steps.append(step)

            if isinstance(step, DecisionStep):
                for branch in step.branches:
                    if branch.steps:
                        all_steps.extend(self._get_all_steps(branch.steps))
                if step.default:
                    all_steps.extend(self._get_all_steps(step.default))

        return all_steps

    def _extract_template_vars(self, obj: Any) -> Set[str]:
        """Extract variable names from templates in an object."""
        vars: Set[str] = set()

        if isinstance(obj, str):
            # Find {{ var }} patterns
            matches = re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_\.]*)", obj)
            for match in matches:
                # Extract root variable name (before first dot)
                root_var = match.split(".")[0]
                vars.add(root_var)

        elif isinstance(obj, dict):
            for value in obj.values():
                vars.update(self._extract_template_vars(value))

        elif isinstance(obj, list):
            for item in obj:
                vars.update(self._extract_template_vars(item))

        return vars

    def _extract_condition_vars(self, condition: str) -> Set[str]:
        """Extract variable names from a decision condition."""
        # Remove string literals first to avoid treating them as variables
        # Remove single-quoted strings
        cleaned = re.sub(r"'[^']*'", "", condition)
        # Remove double-quoted strings
        cleaned = re.sub(r'"[^"]*"', "", cleaned)

        # Similar to template vars, but conditions are already expressions
        vars: Set[str] = set()
        matches = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_\.]*)\b", cleaned)
        for match in matches:
            # Skip Python keywords and operators
            if match not in ["True", "False", "None", "and", "or", "not", "in", "is"]:
                root_var = match.split(".")[0]
                vars.add(root_var)
        return vars

    def _check_template_vars(
        self, obj: Any, defined_vars: Set[str], step_name: str, field: str
    ) -> None:
        """Check if template variables are defined."""
        referenced_vars = self._extract_template_vars(obj)

        for var in referenced_vars:
            if var not in defined_vars:
                self.messages.append(
                    ValidationMessage(
                        level=ValidationLevel.ERROR,
                        message=f"Variable '{var}' is referenced but not defined",
                        step_name=step_name,
                        field=field,
                    )
                )

    def _check_condition_vars(
        self, condition: str, defined_vars: Set[str], step_name: str, field: str
    ) -> None:
        """Check if condition variables are defined."""
        referenced_vars = self._extract_condition_vars(condition)

        for var in referenced_vars:
            if var not in defined_vars:
                self.messages.append(
                    ValidationMessage(
                        level=ValidationLevel.ERROR,
                        message=f"Variable '{var}' in condition is not defined",
                        step_name=step_name,
                        field=field,
                    )
                )

    def print_messages(self, show_info: bool = True) -> None:
        """
        Print validation messages to console.

        Args:
            show_info: Whether to show INFO level messages
        """
        for msg in self.messages:
            if not show_info and msg.level == ValidationLevel.INFO:
                continue
            print(msg)

    def get_error_count(self) -> int:
        """Get count of error messages."""
        return sum(1 for m in self.messages if m.level == ValidationLevel.ERROR)

    def get_warning_count(self) -> int:
        """Get count of warning messages."""
        return sum(1 for m in self.messages if m.level == ValidationLevel.WARNING)


def main() -> None:
    """CLI entry point for playbook validation."""
    parser = argparse.ArgumentParser(
        description="Validate playbook YAML files before execution"
    )
    parser.add_argument("playbook", help="Path to playbook YAML file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show execution plan without validating",
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )
    parser.add_argument(
        "--show-info", action="store_true", help="Show INFO level messages"
    )

    args = parser.parse_args()

    try:
        # Load playbook
        loader = PlaybookLoader()
        playbook = loader.load_from_file(args.playbook)

        if args.dry_run:
            # Show execution plan
            print(f"\nPlaybook: {playbook.metadata.name} v{playbook.metadata.version}")
            if playbook.metadata.description:
                print(f"Description: {playbook.metadata.description}")
            print(f"\nExecution Plan ({len(playbook.steps)} steps):\n")

            for i, step in enumerate(playbook.steps, 1):
                if isinstance(step, SkillStep):
                    print(f"{i}. [SKILL] {step.name}")
                    print(f"   Skill: {step.skill}")
                    if step.output_var:
                        print(f"   Output: {step.output_var}")
                elif isinstance(step, DecisionStep):
                    print(f"{i}. [DECISION] {step.name}")
                    print(f"   Branches: {len(step.branches)}")
                    for j, branch in enumerate(step.branches):
                        print(f"     {j + 1}. {branch.condition}")
                    if step.default:
                        print(f"     default: {len(step.default)} steps")

            sys.exit(0)

        # Validate playbook
        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        # Print messages
        validator.print_messages(show_info=args.show_info)

        # Print summary
        error_count = validator.get_error_count()
        warning_count = validator.get_warning_count()

        if error_count > 0 or warning_count > 0:
            print(
                f"\nValidation Summary: {error_count} error(s), {warning_count} warning(s)"
            )

        # Exit with appropriate code
        sys.exit(0 if is_valid else 1)

    except Exception as e:
        print(f"\033[91mError: {e}\033[0m", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
