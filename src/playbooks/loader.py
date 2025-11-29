"""PlaybookLoader - loads and validates playbook definitions from YAML files."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from jinja2 import Environment, TemplateSyntaxError
from pydantic import ValidationError

from .models import DecisionStep, Playbook, SkillStep, Step, StepType


class PlaybookLoadError(Exception):
    """Raised when a playbook cannot be loaded or validated."""

    pass


class PlaybookLoader:
    """
    Loads playbook definitions from YAML files.

    The loader handles:
    - YAML parsing
    - Jinja2 template variable substitution
    - Pydantic validation of playbook structure
    - Support for skill and decision step types

    Example:
        loader = PlaybookLoader()
        playbook = loader.load_from_file("playbooks/lead_enrichment.yaml")

        # With custom variables
        playbook = loader.load_from_file(
            "playbooks/template.yaml",
            variables={"max_retries": 3}
        )
    """

    def __init__(self) -> None:
        """Initialize the PlaybookLoader with a Jinja2 environment."""
        from jinja2 import ChainableUndefined

        self._jinja_env = Environment(
            autoescape=False,
            undefined=ChainableUndefined,  # Keep undefined variables as-is for runtime evaluation
        )

    def load_from_file(
        self, file_path: Union[str, Path], variables: Optional[Dict[str, Any]] = None
    ) -> Playbook:
        """
        Load a playbook from a YAML file.

        Args:
            file_path: Path to the YAML file
            variables: Optional template variables to substitute

        Returns:
            Validated Playbook instance

        Raises:
            PlaybookLoadError: If file cannot be read, parsed, or validated
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise PlaybookLoadError(f"Playbook file not found: {file_path}")

        if not file_path.is_file():
            raise PlaybookLoadError(f"Path is not a file: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise PlaybookLoadError(f"Failed to read file {file_path}: {e}")

        return self.load_from_string(content, variables)

    def load_from_string(
        self, yaml_content: str, variables: Optional[Dict[str, Any]] = None
    ) -> Playbook:
        """
        Load a playbook from a YAML string.

        Args:
            yaml_content: YAML content as string
            variables: Optional template variables to substitute in metadata/config only

        Returns:
            Validated Playbook instance

        Raises:
            PlaybookLoadError: If YAML cannot be parsed or validated
        """
        # Process Jinja2 template variables if provided
        # Note: This only substitutes variables at load-time. Runtime template variables
        # (in step inputs, decision conditions, etc.) are preserved for execution time.
        if variables:
            processed_content = self._process_template(yaml_content, variables)
        else:
            processed_content = yaml_content

        # Parse YAML
        try:
            data = yaml.safe_load(processed_content)
        except yaml.YAMLError as e:
            raise PlaybookLoadError(f"Failed to parse YAML: {e}")

        if not isinstance(data, dict):
            raise PlaybookLoadError("YAML content must be a dictionary")

        # Load and validate using Pydantic
        return self.load_from_dict(data)

    def load_from_dict(self, data: Dict[str, Any]) -> Playbook:
        """
        Load a playbook from a dictionary.

        Args:
            data: Dictionary representation of playbook

        Returns:
            Validated Playbook instance

        Raises:
            PlaybookLoadError: If validation fails
        """
        try:
            # Ensure metadata exists
            if "metadata" not in data:
                raise PlaybookLoadError("Playbook must have 'metadata' section")

            # Ensure steps exist
            if "steps" not in data:
                raise PlaybookLoadError("Playbook must have 'steps' section")

            # Parse steps with proper type discrimination
            steps = self._parse_steps(data["steps"])

            # Build playbook data
            playbook_data = {
                "metadata": data["metadata"],
                "variables": data.get("variables", {}),
                "steps": steps,
            }

            return Playbook(**playbook_data)

        except ValidationError as e:
            raise PlaybookLoadError(f"Playbook validation failed: {e}")

    def _parse_steps(self, steps_data: Any) -> List[Step]:
        """
        Parse steps from raw data, handling type discrimination.

        Args:
            steps_data: Raw steps data from YAML

        Returns:
            List of validated Step objects

        Raises:
            PlaybookLoadError: If steps cannot be parsed
        """
        if not isinstance(steps_data, list):
            raise PlaybookLoadError("'steps' must be a list")

        parsed_steps: List[Step] = []

        for i, step_data in enumerate(steps_data):
            if not isinstance(step_data, dict):
                raise PlaybookLoadError(f"Step {i} must be a dictionary")

            if "type" not in step_data:
                raise PlaybookLoadError(f"Step {i} must have a 'type' field")

            step_type = step_data["type"]

            try:
                if step_type == StepType.SKILL.value:
                    step = SkillStep(**step_data)
                elif step_type == StepType.DECISION.value:
                    # Recursively parse branches
                    if "branches" in step_data:
                        for branch in step_data["branches"]:
                            if "steps" in branch:
                                branch["steps"] = self._parse_steps(branch["steps"])

                    # Parse default steps if present
                    if "default" in step_data and step_data["default"]:
                        step_data["default"] = self._parse_steps(step_data["default"])

                    step = DecisionStep(**step_data)
                else:
                    raise PlaybookLoadError(
                        f"Step {i} has unknown type '{step_type}'. "
                        f"Must be one of: {[t.value for t in StepType]}"
                    )

                parsed_steps.append(step)

            except ValidationError as e:
                raise PlaybookLoadError(f"Step {i} validation failed: {e}")

        return parsed_steps

    def _process_template(self, content: str, variables: Dict[str, Any]) -> str:
        """
        Process Jinja2 template variables in content.

        Args:
            content: Content with Jinja2 templates
            variables: Variables to substitute

        Returns:
            Processed content with variables substituted

        Raises:
            PlaybookLoadError: If template processing fails
        """
        try:
            template = self._jinja_env.from_string(content)
            return template.render(**variables)
        except TemplateSyntaxError as e:
            raise PlaybookLoadError(f"Template syntax error: {e}")
        except Exception as e:
            raise PlaybookLoadError(f"Template processing failed: {e}")
