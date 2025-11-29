"""Unit tests for PlaybookLoader."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from src.playbooks.loader import PlaybookLoader, PlaybookLoadError
from src.playbooks.models import (
    DecisionStep,
    Playbook,
    SkillStep,
    StepType,
)


class TestPlaybookLoader:
    """Test suite for PlaybookLoader."""

    @pytest.fixture
    def loader(self) -> PlaybookLoader:
        """Create a PlaybookLoader instance."""
        return PlaybookLoader()

    @pytest.fixture
    def simple_playbook_yaml(self) -> str:
        """A simple valid playbook YAML."""
        return """
metadata:
  name: test_playbook
  version: 1.0.0
  description: A test playbook
  author: Test Author
  tags:
    - test
    - sample

variables:
  max_retries: 3
  timeout: 30

steps:
  - type: skill
    name: fetch_data
    skill: http_request
    input:
      url: https://api.example.com/data
      method: GET
    output_var: api_response

  - type: skill
    name: process_data
    skill: data_processor
    input:
      data: "{{ api_response }}"
    output_var: processed
"""

    @pytest.fixture
    def decision_playbook_yaml(self) -> str:
        """A playbook with decision steps."""
        return """
metadata:
  name: decision_playbook
  version: 1.0.0

steps:
  - type: skill
    name: check_score
    skill: score_calculator
    input:
      value: 85
    output_var: score

  - type: decision
    name: score_routing
    branches:
      - condition: "{{ score > 80 }}"
        steps:
          - type: skill
            name: high_score_action
            skill: send_notification
            input:
              message: High score achieved

      - condition: "{{ score > 50 }}"
        steps:
          - type: skill
            name: medium_score_action
            skill: send_email
            input:
              subject: Medium score

    default:
      - type: skill
        name: low_score_action
        skill: log_message
        input:
          message: Low score
"""

    def test_load_from_string_simple(
        self, loader: PlaybookLoader, simple_playbook_yaml: str
    ) -> None:
        """Test loading a simple playbook from string."""
        playbook = loader.load_from_string(simple_playbook_yaml)

        assert isinstance(playbook, Playbook)
        assert playbook.metadata.name == "test_playbook"
        assert playbook.metadata.version == "1.0.0"
        assert playbook.metadata.description == "A test playbook"
        assert playbook.metadata.author == "Test Author"
        assert "test" in playbook.metadata.tags
        assert playbook.variables["max_retries"] == 3
        assert len(playbook.steps) == 2

    def test_load_from_string_with_template_variables(
        self, loader: PlaybookLoader
    ) -> None:
        """Test loading with Jinja2 template variables."""
        yaml_with_vars = """
metadata:
  name: {{ playbook_name }}
  version: 1.0.0

variables:
  api_key: {{ api_key }}

steps:
  - type: skill
    name: call_api
    skill: http_request
    input:
      url: {{ api_url }}
"""
        variables = {
            "playbook_name": "dynamic_playbook",
            "api_key": "secret123",
            "api_url": "https://api.test.com",
        }

        playbook = loader.load_from_string(yaml_with_vars, variables)

        assert playbook.metadata.name == "dynamic_playbook"
        assert playbook.variables["api_key"] == "secret123"
        assert playbook.steps[0].input["url"] == "https://api.test.com"

    def test_load_from_file(
        self, loader: PlaybookLoader, simple_playbook_yaml: str
    ) -> None:
        """Test loading from a file."""
        with NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(simple_playbook_yaml)
            temp_path = Path(f.name)

        try:
            playbook = loader.load_from_file(temp_path)
            assert playbook.metadata.name == "test_playbook"
        finally:
            temp_path.unlink()

    def test_load_from_file_not_found(self, loader: PlaybookLoader) -> None:
        """Test loading from non-existent file."""
        with pytest.raises(PlaybookLoadError, match="Playbook file not found"):
            loader.load_from_file("nonexistent.yaml")

    def test_load_from_file_is_directory(
        self, loader: PlaybookLoader, tmp_path: Path
    ) -> None:
        """Test loading from directory instead of file."""
        with pytest.raises(PlaybookLoadError, match="Path is not a file"):
            loader.load_from_file(tmp_path)

    def test_load_skill_steps(
        self, loader: PlaybookLoader, simple_playbook_yaml: str
    ) -> None:
        """Test that skill steps are parsed correctly."""
        playbook = loader.load_from_string(simple_playbook_yaml)

        step1 = playbook.steps[0]
        assert isinstance(step1, SkillStep)
        assert step1.type == StepType.SKILL
        assert step1.name == "fetch_data"
        assert step1.skill == "http_request"
        assert step1.output_var == "api_response"
        assert "url" in step1.input

        step2 = playbook.steps[1]
        assert isinstance(step2, SkillStep)
        assert step2.name == "process_data"
        assert step2.skill == "data_processor"

    def test_load_decision_steps(
        self, loader: PlaybookLoader, decision_playbook_yaml: str
    ) -> None:
        """Test that decision steps are parsed correctly."""
        playbook = loader.load_from_string(decision_playbook_yaml)

        assert len(playbook.steps) == 2
        decision_step = playbook.steps[1]

        assert isinstance(decision_step, DecisionStep)
        assert decision_step.type == StepType.DECISION
        assert decision_step.name == "score_routing"
        assert len(decision_step.branches) == 2

        # Check first branch
        branch1 = decision_step.branches[0]
        assert branch1.condition == "{{ score > 80 }}"
        assert len(branch1.steps) == 1
        assert branch1.steps[0].name == "high_score_action"

        # Check default branch
        assert decision_step.default is not None
        assert len(decision_step.default) == 1
        assert decision_step.default[0].name == "low_score_action"

    def test_invalid_yaml(self, loader: PlaybookLoader) -> None:
        """Test loading invalid YAML."""
        invalid_yaml = """
metadata:
  name: test
  - invalid
    - structure
"""
        with pytest.raises(PlaybookLoadError, match="Failed to parse YAML"):
            loader.load_from_string(invalid_yaml)

    def test_missing_metadata(self, loader: PlaybookLoader) -> None:
        """Test playbook without metadata."""
        yaml_no_metadata = """
steps:
  - type: skill
    name: test
    skill: test_skill
"""
        with pytest.raises(PlaybookLoadError, match="must have 'metadata' section"):
            loader.load_from_string(yaml_no_metadata)

    def test_missing_steps(self, loader: PlaybookLoader) -> None:
        """Test playbook without steps."""
        yaml_no_steps = """
metadata:
  name: test
  version: 1.0.0
"""
        with pytest.raises(PlaybookLoadError, match="must have 'steps' section"):
            loader.load_from_string(yaml_no_steps)

    def test_empty_steps(self, loader: PlaybookLoader) -> None:
        """Test playbook with empty steps list."""
        yaml_empty_steps = """
metadata:
  name: test
  version: 1.0.0
steps: []
"""
        with pytest.raises(PlaybookLoadError, match="must have at least one step"):
            loader.load_from_string(yaml_empty_steps)

    def test_invalid_step_type(self, loader: PlaybookLoader) -> None:
        """Test step with invalid type."""
        yaml_invalid_type = """
metadata:
  name: test
  version: 1.0.0
steps:
  - type: invalid_type
    name: test
"""
        with pytest.raises(PlaybookLoadError, match="unknown type"):
            loader.load_from_string(yaml_invalid_type)

    def test_step_missing_type(self, loader: PlaybookLoader) -> None:
        """Test step without type field."""
        yaml_no_type = """
metadata:
  name: test
  version: 1.0.0
steps:
  - name: test
    skill: test_skill
"""
        with pytest.raises(PlaybookLoadError, match="must have a 'type' field"):
            loader.load_from_string(yaml_no_type)

    def test_skill_step_missing_required_field(self, loader: PlaybookLoader) -> None:
        """Test skill step missing required field."""
        yaml_missing_skill = """
metadata:
  name: test
  version: 1.0.0
steps:
  - type: skill
    name: test
"""
        with pytest.raises(PlaybookLoadError, match="validation failed"):
            loader.load_from_string(yaml_missing_skill)

    def test_decision_step_missing_branches(self, loader: PlaybookLoader) -> None:
        """Test decision step without branches."""
        yaml_no_branches = """
metadata:
  name: test
  version: 1.0.0
steps:
  - type: decision
    name: test_decision
"""
        with pytest.raises(PlaybookLoadError, match="validation failed"):
            loader.load_from_string(yaml_no_branches)

    def test_template_syntax_error(self, loader: PlaybookLoader) -> None:
        """Test YAML with invalid Jinja2 syntax when template processing is enabled."""
        yaml_bad_template = """
metadata:
  name: "{{ unclosed "
  version: 1.0.0
steps:
  - type: skill
    name: test
    skill: test_skill
"""
        # When variables dict is provided, templates are processed and syntax errors are caught
        with pytest.raises(PlaybookLoadError, match="Template syntax error"):
            loader.load_from_string(yaml_bad_template, variables={"some": "var"})

    def test_undefined_template_variable(self, loader: PlaybookLoader) -> None:
        """Test that undefined variables become None and fail validation."""
        yaml_undefined_var = """
metadata:
  name: {{ undefined_var }}
  version: 1.0.0
steps:
  - type: skill
    name: test
    skill: test_skill
"""
        # ChainableUndefined renders undefined bare vars as None (not in quotes),
        # which fails Pydantic validation for required string fields
        with pytest.raises(PlaybookLoadError, match="validation failed"):
            loader.load_from_string(yaml_undefined_var, variables={"other": "value"})

    def test_load_from_dict(self, loader: PlaybookLoader) -> None:
        """Test loading from dictionary."""
        data = {
            "metadata": {
                "name": "dict_playbook",
                "version": "1.0.0",
            },
            "steps": [
                {
                    "type": "skill",
                    "name": "test_step",
                    "skill": "test_skill",
                }
            ],
        }

        playbook = loader.load_from_dict(data)
        assert playbook.metadata.name == "dict_playbook"
        assert len(playbook.steps) == 1

    def test_nested_decision_steps(self, loader: PlaybookLoader) -> None:
        """Test decision steps with nested decisions."""
        yaml_nested = """
metadata:
  name: nested_decisions
  version: 1.0.0

steps:
  - type: decision
    name: outer_decision
    branches:
      - condition: "{{ outer_condition }}"
        steps:
          - type: decision
            name: inner_decision
            branches:
              - condition: "{{ inner_condition }}"
                steps:
                  - type: skill
                    name: nested_skill
                    skill: deep_action
"""
        playbook = loader.load_from_string(yaml_nested)

        outer_decision = playbook.steps[0]
        assert isinstance(outer_decision, DecisionStep)

        inner_steps = outer_decision.branches[0].steps
        assert len(inner_steps) == 1

        inner_decision = inner_steps[0]
        assert isinstance(inner_decision, DecisionStep)
        assert inner_decision.name == "inner_decision"

    def test_playbook_repr(
        self, loader: PlaybookLoader, simple_playbook_yaml: str
    ) -> None:
        """Test Playbook __repr__ method."""
        playbook = loader.load_from_string(simple_playbook_yaml)
        repr_str = repr(playbook)

        assert "Playbook" in repr_str
        assert "test_playbook" in repr_str
        assert "1.0.0" in repr_str
        assert "steps=2" in repr_str

    def test_default_values(self, loader: PlaybookLoader) -> None:
        """Test that default values are set correctly."""
        minimal_yaml = """
metadata:
  name: minimal

steps:
  - type: skill
    name: test
    skill: test_skill
"""
        playbook = loader.load_from_string(minimal_yaml)

        # Check default metadata values
        assert playbook.metadata.version == "1.0.0"
        assert playbook.metadata.description is None
        assert playbook.metadata.author is None
        assert playbook.metadata.tags == []

        # Check default step values
        step = playbook.steps[0]
        assert step.input == {}
        assert step.output_var is None

    def test_variables_optional(self, loader: PlaybookLoader) -> None:
        """Test that variables section is optional."""
        yaml_no_vars = """
metadata:
  name: no_vars
  version: 1.0.0

steps:
  - type: skill
    name: test
    skill: test_skill
"""
        playbook = loader.load_from_string(yaml_no_vars)
        assert playbook.variables == {}
