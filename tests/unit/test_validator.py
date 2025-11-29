"""Unit tests for PlaybookValidator."""

from typing import Any, Dict

from src.playbooks import (
    DecisionBranch,
    DecisionStep,
    Playbook,
    PlaybookMetadata,
    PlaybookValidator,
    SkillStep,
    ValidationLevel,
)
from src.skills.base import Skill
from src.skills.registry import SkillRegistry


class DummySkill(Skill):
    """Dummy skill for testing."""

    name = "dummy_skill"
    version = "1.0.0"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return {"result": "ok"}


class TestValidationMessage:
    """Test suite for ValidationMessage."""

    def test_message_formatting(self) -> None:
        """Test message string formatting."""
        from src.playbooks.validator import ValidationMessage

        msg = ValidationMessage(
            level=ValidationLevel.ERROR,
            message="Test error",
            step_name="test_step",
            field="test_field",
        )

        result = str(msg)
        assert "ERROR" in result
        assert "test_step" in result
        assert "test_field" in result
        assert "Test error" in result


class TestPlaybookValidator:
    """Test suite for PlaybookValidator."""

    def test_validator_initialization(self) -> None:
        """Test validator can be initialized."""
        validator = PlaybookValidator()
        assert validator is not None
        assert validator.skill_registry is None
        assert validator.messages == []

    def test_validator_with_registry(self) -> None:
        """Test validator with skill registry."""
        registry = SkillRegistry()
        validator = PlaybookValidator(skill_registry=registry)
        assert validator.skill_registry == registry

    def test_validate_valid_playbook(self) -> None:
        """Test validation of a valid playbook."""
        playbook = Playbook(
            metadata=PlaybookMetadata(
                name="test_playbook",
                version="1.0.0",
                description="Test playbook",
            ),
            steps=[
                SkillStep(
                    name="test_step",
                    skill="test_skill",
                    input={"key": "value"},
                )
            ],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        assert is_valid is True
        assert any(m.level == ValidationLevel.SUCCESS for m in validator.messages)

    def test_validate_missing_metadata_name(self) -> None:
        """Test validation fails for missing playbook name."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="", version="1.0.0"),
            steps=[SkillStep(name="dummy", skill="dummy", input={})],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        assert is_valid is False
        assert any(
            m.level == ValidationLevel.ERROR and "name is required" in m.message
            for m in validator.messages
        )

    def test_validate_missing_metadata_version(self) -> None:
        """Test validation fails for missing version."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version=""),
            steps=[SkillStep(name="dummy", skill="dummy", input={})],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        assert is_valid is False
        assert any(
            m.level == ValidationLevel.ERROR and "version is required" in m.message
            for m in validator.messages
        )

    def test_validate_missing_description_warning(self) -> None:
        """Test validation warns for missing description."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description=""),
            steps=[SkillStep(name="dummy", skill="dummy", input={})],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        # Should be valid (warning, not error)
        assert is_valid is True
        assert any(
            m.level == ValidationLevel.WARNING and "description is missing" in m.message
            for m in validator.messages
        )

    def test_validate_unregistered_skill(self) -> None:
        """Test validation fails for unregistered skill."""
        registry = SkillRegistry()
        # Don't register any skills

        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[
                SkillStep(
                    name="test_step",
                    skill="unknown_skill",
                    input={},
                )
            ],
        )

        validator = PlaybookValidator(skill_registry=registry)
        is_valid = validator.validate(playbook)

        assert is_valid is False
        assert any(
            m.level == ValidationLevel.ERROR and "not registered" in m.message
            for m in validator.messages
        )

    def test_validate_registered_skill(self) -> None:
        """Test validation succeeds for registered skill."""
        registry = SkillRegistry()
        registry.register(DummySkill)

        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[
                SkillStep(
                    name="test_step",
                    skill="dummy_skill",
                    input={},
                    output_var="result",
                )
            ],
        )

        validator = PlaybookValidator(skill_registry=registry)
        is_valid = validator.validate(playbook)

        assert is_valid is True

    def test_validate_undefined_variable_reference(self) -> None:
        """Test validation fails for undefined variable reference."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0"),
            steps=[
                SkillStep(
                    name="test_step",
                    skill="test_skill",
                    input={"data": "{{ undefined_var }}"},
                )
            ],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        assert is_valid is False
        assert any(
            m.level == ValidationLevel.ERROR
            and "undefined_var" in m.message
            and "not defined" in m.message
            for m in validator.messages
        )

    def test_validate_defined_variable_reference(self) -> None:
        """Test validation succeeds for defined variable reference."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            variables={"defined_var": "value"},
            steps=[
                SkillStep(
                    name="test_step",
                    skill="test_skill",
                    input={"data": "{{ defined_var }}"},
                    output_var="result",
                )
            ],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        assert is_valid is True

    def test_validate_output_variable_reference(self) -> None:
        """Test validation succeeds when referencing output from previous step."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[
                SkillStep(
                    name="step1",
                    skill="skill1",
                    input={},
                    output_var="step1_output",
                ),
                SkillStep(
                    name="step2",
                    skill="skill2",
                    input={"data": "{{ step1_output }}"},
                    output_var="result",
                ),
            ],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        assert is_valid is True

    def test_validate_nested_variable_reference(self) -> None:
        """Test validation handles nested variable references."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[
                SkillStep(
                    name="step1",
                    skill="skill1",
                    input={},
                    output_var="context",
                ),
                SkillStep(
                    name="step2",
                    skill="skill2",
                    input={"data": "{{ context.field }}"},
                    output_var="result",
                ),
            ],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        assert is_valid is True

    def test_validate_invalid_condition_syntax(self) -> None:
        """Test validation fails for invalid condition syntax."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0"),
            steps=[
                DecisionStep(
                    name="decision",
                    branches=[
                        DecisionBranch(
                            condition="invalid {{ syntax",
                            steps=[],
                        )
                    ],
                )
            ],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        assert is_valid is False
        assert any(
            m.level == ValidationLevel.ERROR and "Invalid condition syntax" in m.message
            for m in validator.messages
        )

    def test_validate_valid_condition_syntax(self) -> None:
        """Test validation succeeds for valid condition syntax."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            variables={"value": 10},
            steps=[
                DecisionStep(
                    name="decision",
                    branches=[
                        DecisionBranch(
                            condition="value > 5",
                            steps=[
                                SkillStep(
                                    name="branch_step",
                                    skill="skill1",
                                    input={},
                                    output_var="result",
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        assert is_valid is True

    def test_validate_condition_variable_reference(self) -> None:
        """Test validation checks variable references in conditions."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0"),
            steps=[
                DecisionStep(
                    name="decision",
                    branches=[
                        DecisionBranch(
                            condition="undefined_var > 5",
                            steps=[],
                        )
                    ],
                )
            ],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        assert is_valid is False
        assert any(
            m.level == ValidationLevel.ERROR
            and "undefined_var" in m.message
            and "not defined" in m.message
            for m in validator.messages
        )

    def test_validate_unused_output_warning(self) -> None:
        """Test validation warns for unused output variables."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[
                SkillStep(
                    name="step1",
                    skill="skill1",
                    input={},
                    output_var="unused_output",
                )
            ],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        # Should be valid (warning, not error)
        assert is_valid is True
        assert any(
            m.level == ValidationLevel.WARNING and "never used" in m.message
            for m in validator.messages
        )

    def test_validate_nested_decision_steps(self) -> None:
        """Test validation handles nested decision steps."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            variables={"value": 10},
            steps=[
                DecisionStep(
                    name="outer_decision",
                    branches=[
                        DecisionBranch(
                            condition="value > 5",
                            steps=[
                                DecisionStep(
                                    name="inner_decision",
                                    branches=[
                                        DecisionBranch(
                                            condition="value > 8",
                                            steps=[
                                                SkillStep(
                                                    name="inner_skill",
                                                    skill="skill1",
                                                    input={},
                                                    output_var="result",
                                                )
                                            ],
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        assert is_valid is True

    def test_validate_default_branch(self) -> None:
        """Test validation handles default branches."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            variables={"value": 10},
            steps=[
                DecisionStep(
                    name="decision",
                    branches=[
                        DecisionBranch(
                            condition="value > 20",
                            steps=[],
                        )
                    ],
                    default=[
                        SkillStep(
                            name="default_skill",
                            skill="skill1",
                            input={},
                            output_var="result",
                        )
                    ],
                )
            ],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        assert is_valid is True

    def test_get_error_count(self) -> None:
        """Test get_error_count method."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="", version=""),
            steps=[SkillStep(name="dummy", skill="dummy", input={})],
        )

        validator = PlaybookValidator()
        validator.validate(playbook)

        assert validator.get_error_count() == 2  # name and version

    def test_get_warning_count(self) -> None:
        """Test get_warning_count method."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0"),
            steps=[
                SkillStep(
                    name="step1",
                    skill="skill1",
                    input={},
                    output_var="unused",
                )
            ],
        )

        validator = PlaybookValidator()
        validator.validate(playbook)

        assert validator.get_warning_count() == 2  # description + unused output

    def test_extract_template_vars_from_string(self) -> None:
        """Test extracting variables from template strings."""
        validator = PlaybookValidator()
        vars = validator._extract_template_vars("{{ var1 }} and {{ var2.field }}")

        assert "var1" in vars
        assert "var2" in vars

    def test_extract_template_vars_from_dict(self) -> None:
        """Test extracting variables from nested dict."""
        validator = PlaybookValidator()
        vars = validator._extract_template_vars(
            {"key1": "{{ var1 }}", "nested": {"key2": "{{ var2 }}"}}
        )

        assert "var1" in vars
        assert "var2" in vars

    def test_extract_template_vars_from_list(self) -> None:
        """Test extracting variables from list."""
        validator = PlaybookValidator()
        vars = validator._extract_template_vars(["{{ var1 }}", "{{ var2 }}"])

        assert "var1" in vars
        assert "var2" in vars

    def test_extract_condition_vars(self) -> None:
        """Test extracting variables from conditions."""
        validator = PlaybookValidator()
        vars = validator._extract_condition_vars("var1 > 5 and var2.field == 'test'")

        assert "var1" in vars
        assert "var2" in vars

    def test_extract_condition_vars_skips_keywords(self) -> None:
        """Test that Python keywords are skipped in condition vars."""
        validator = PlaybookValidator()
        vars = validator._extract_condition_vars("value > 5 and True or False and None")

        assert "value" in vars
        assert "True" not in vars
        assert "False" not in vars
        assert "None" not in vars
        assert "and" not in vars
        assert "or" not in vars

    def test_validate_complex_playbook(self) -> None:
        """Test validation of complex playbook with multiple steps."""
        playbook = Playbook(
            metadata=PlaybookMetadata(
                name="complex_test",
                version="1.0.0",
                description="Complex test playbook",
            ),
            variables={"input_data": "test"},
            steps=[
                SkillStep(
                    name="extract_context",
                    skill="extractor",
                    input={"text": "{{ input_data }}"},
                    output_var="context",
                ),
                SkillStep(
                    name="analyze_risks",
                    skill="risk_analyzer",
                    input={"context": "{{ context }}"},
                    output_var="risks",
                ),
                DecisionStep(
                    name="check_risk_level",
                    branches=[
                        DecisionBranch(
                            condition="risks.level == 'high'",
                            steps=[
                                SkillStep(
                                    name="escalate",
                                    skill="escalator",
                                    input={"risks": "{{ risks }}"},
                                )
                            ],
                        )
                    ],
                ),
            ],
        )

        validator = PlaybookValidator()
        is_valid = validator.validate(playbook)

        # Should be valid even with warnings
        assert is_valid is True
        # Should not have any errors
        assert validator.get_error_count() == 0
