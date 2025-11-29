"""Tests for custom error classes."""

from pydantic import BaseModel, ValidationError

from src.playbooks.errors import (
    CheckpointError,
    InvalidInputError,
    SkillExecutionError,
    SkillNotFoundError,
    TemplateError,
)


class TestSkillNotFoundError:
    """Test SkillNotFoundError."""

    def test_error_message_with_suggestions(self):
        """Test error message includes close match suggestions."""
        available_skills = ["add_numbers", "multiply_numbers", "subtract_numbers"]

        error = SkillNotFoundError(
            skill_name="ad_numbers",  # Typo: missing 'd'
            step_name="calculate",
            available_skills=available_skills,
            playbook_name="math_playbook",
        )

        error_msg = str(error)

        # Check error message components
        assert "ad_numbers" in error_msg
        assert "calculate" in error_msg
        assert "math_playbook" in error_msg
        assert "Did you mean" in error_msg
        assert "add_numbers" in error_msg
        assert "Available skills" in error_msg
        assert "Tip: Register your skill" in error_msg

    def test_error_message_no_suggestions(self):
        """Test error message when no close matches found."""
        available_skills = ["add_numbers", "multiply_numbers"]

        error = SkillNotFoundError(
            skill_name="completely_different_skill",
            step_name="calculate",
            available_skills=available_skills,
            playbook_name="math_playbook",
        )

        error_msg = str(error)

        # Should not have suggestions section
        assert "Did you mean" not in error_msg
        # But should still list available skills
        assert "Available skills" in error_msg
        assert "add_numbers" in error_msg
        assert "multiply_numbers" in error_msg


class TestTemplateError:
    """Test TemplateError."""

    def test_error_message_with_context(self):
        """Test error message includes template context."""
        available_vars = {
            "input": {"value": 10},
            "result": 42,
            "data": {"name": "test", "count": 5},
        }

        original_error = Exception("undefined variable 'missing_var'")

        error = TemplateError(
            template_str="{{ missing_var }}",
            error=original_error,
            step_name="process_data",
            field_name="input.value",
            available_vars=available_vars,
        )

        error_msg = str(error)

        # Check error components
        assert "process_data" in error_msg
        assert "input.value" in error_msg
        assert "{{ missing_var }}" in error_msg
        assert "Available variables:" in error_msg
        assert "input:" in error_msg
        assert "result:" in error_msg
        assert "data:" in error_msg

    def test_error_message_no_variables(self):
        """Test error message when no variables available."""
        error = TemplateError(
            template_str="{{ value }}",
            error=Exception("no variables"),
            step_name="test_step",
            field_name="input",
            available_vars={},
        )

        error_msg = str(error)

        assert "(no variables available)" in error_msg

    def test_error_message_truncates_long_values(self):
        """Test that long variable values are truncated."""
        long_string = "x" * 200

        error = TemplateError(
            template_str="{{ long }}",
            error=Exception("error"),
            step_name="test",
            field_name="input",
            available_vars={"long": long_string},
        )

        error_msg = str(error)

        # Should be truncated to ~80 chars with ...
        assert "..." in error_msg
        assert len([line for line in error_msg.split("\n") if "long:" in line][0]) < 120


class TestSkillExecutionError:
    """Test SkillExecutionError."""

    def test_error_message_with_reasoning(self):
        """Test error message includes skill reasoning."""
        input_data = {"value": 10, "multiplier": 2}
        original_error = ValueError("Invalid multiplier")
        reasoning = "Attempting to multiply value by multiplier"

        error = SkillExecutionError(
            skill_name="multiply",
            step_name="calculate",
            input_data=input_data,
            original_error=original_error,
            reasoning=reasoning,
        )

        error_msg = str(error)

        # Check error components
        assert "multiply" in error_msg
        assert "calculate" in error_msg
        assert "ValueError: Invalid multiplier" in error_msg
        assert "Input data:" in error_msg
        assert "value: 10" in error_msg
        assert "multiplier: 2" in error_msg
        assert "Skill reasoning:" in error_msg
        assert reasoning in error_msg

    def test_error_message_without_reasoning(self):
        """Test error message without reasoning."""
        error = SkillExecutionError(
            skill_name="test_skill",
            step_name="test_step",
            input_data={"test": "value"},
            original_error=Exception("test error"),
            reasoning=None,
        )

        error_msg = str(error)

        # Should not have reasoning section
        assert "Skill reasoning:" not in error_msg
        # But should have other components
        assert "test_skill" in error_msg
        assert "test_step" in error_msg

    def test_format_nested_dict(self):
        """Test formatting of nested dictionaries."""
        nested_data = {
            "top": "value",
            "nested": {"inner": "data", "count": 5},
            "items": [1, 2, 3],
        }

        error = SkillExecutionError(
            skill_name="test",
            step_name="test",
            input_data=nested_data,
            original_error=Exception("error"),
        )

        error_msg = str(error)

        # Check nested formatting
        assert "top: value" in error_msg
        assert "nested:" in error_msg
        assert "inner: data" in error_msg
        assert "items: [3 items]" in error_msg


class TestInvalidInputError:
    """Test InvalidInputError."""

    def test_error_message_with_validation_errors(self):
        """Test error message includes Pydantic validation errors."""

        class TestSchema(BaseModel):
            name: str
            age: int

        input_data = {"name": "test", "age": "not_a_number"}

        try:
            TestSchema(**input_data)
        except ValidationError as e:
            error = InvalidInputError(
                skill_name="validate_person",
                schema=TestSchema,
                input_data=input_data,
                validation_error=e,
            )

            error_msg = str(error)

            # Check error components
            assert "validate_person" in error_msg
            assert "TestSchema" in error_msg
            assert "Validation errors:" in error_msg
            assert "age" in error_msg
            assert "Input data:" in error_msg

    def test_error_preserves_original_validation_error(self):
        """Test that original ValidationError is preserved."""

        class TestSchema(BaseModel):
            required_field: str

        input_data = {}

        try:
            TestSchema(**input_data)
        except ValidationError as e:
            error = InvalidInputError(
                skill_name="test",
                schema=TestSchema,
                input_data=input_data,
                validation_error=e,
            )

            assert error.validation_error == e
            assert error.schema == TestSchema


class TestCheckpointError:
    """Test CheckpointError."""

    def test_error_message_save_operation(self):
        """Test error message for save operation."""
        original_error = OSError("Disk full")

        error = CheckpointError(
            operation="save",
            execution_id="abc-123",
            original_error=original_error,
        )

        error_msg = str(error)

        assert "save" in error_msg
        assert "abc-123" in error_msg
        assert "OSError: Disk full" in error_msg

    def test_error_message_load_operation(self):
        """Test error message for load operation."""
        original_error = FileNotFoundError("File not found")

        error = CheckpointError(
            operation="load",
            execution_id="xyz-789",
            original_error=original_error,
        )

        error_msg = str(error)

        assert "load" in error_msg
        assert "xyz-789" in error_msg
        assert "FileNotFoundError" in error_msg
