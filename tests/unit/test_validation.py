"""Tests for input validation decorator."""

from typing import Any, Dict

import pytest
from pydantic import BaseModel, Field

from src.playbooks.errors import InvalidInputError
from src.skills.base import Skill
from src.skills.validation import validate_input, validate_output


class TestValidateInput:
    """Test validate_input decorator."""

    def test_valid_input(self):
        """Test that valid input passes validation."""

        class InputSchema(BaseModel):
            name: str
            age: int

        class TestSkill(Skill):
            name = "test_skill"
            version = "1.0.0"
            description = "Test skill"

            @validate_input(InputSchema)
            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                return {"result": f"{input['name']} is {input['age']}"}

        skill = TestSkill()

        @pytest.mark.asyncio
        async def run_test():
            output, _ = await skill.run({"name": "Alice", "age": 30})
            assert output["result"] == "Alice is 30"

        import asyncio

        asyncio.run(run_test())

    def test_invalid_input_type(self):
        """Test that invalid input type raises InvalidInputError."""

        class InputSchema(BaseModel):
            name: str
            age: int

        class TestSkill(Skill):
            name = "test_skill"
            version = "1.0.0"
            description = "Test skill"

            @validate_input(InputSchema)
            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                return {"result": "success"}

        skill = TestSkill()

        @pytest.mark.asyncio
        async def run_test():
            with pytest.raises(InvalidInputError) as exc_info:
                await skill.run({"name": "Alice", "age": "not_a_number"})

            error = exc_info.value
            assert error.skill_name == "test_skill"
            assert error.schema == InputSchema
            assert "age" in str(error)

        import asyncio

        asyncio.run(run_test())

    def test_missing_required_field(self):
        """Test that missing required field raises InvalidInputError."""

        class InputSchema(BaseModel):
            required_field: str

        class TestSkill(Skill):
            name = "test_skill"
            version = "1.0.0"
            description = "Test skill"

            @validate_input(InputSchema)
            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                return {"result": "success"}

        skill = TestSkill()

        @pytest.mark.asyncio
        async def run_test():
            with pytest.raises(InvalidInputError) as exc_info:
                await skill.run({})

            error = exc_info.value
            assert "required_field" in str(error)

        import asyncio

        asyncio.run(run_test())

    def test_default_values(self):
        """Test that default values work correctly."""

        class InputSchema(BaseModel):
            name: str
            age: int = 18

        class TestSkill(Skill):
            name = "test_skill"
            version = "1.0.0"
            description = "Test skill"

            @validate_input(InputSchema)
            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                return {"age": input["age"]}

        skill = TestSkill()

        @pytest.mark.asyncio
        async def run_test():
            output, _ = await skill.run({"name": "Alice"})
            assert output["age"] == 18

        import asyncio

        asyncio.run(run_test())

    def test_validated_input_converted_to_dict(self):
        """Test that validated input is converted back to dict."""

        class InputSchema(BaseModel):
            value: int

        class TestSkill(Skill):
            name = "test_skill"
            version = "1.0.0"
            description = "Test skill"

            @validate_input(InputSchema)
            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                # Input should be a dict, not Pydantic model
                assert isinstance(input, dict)
                return {"result": input["value"] * 2}

        skill = TestSkill()

        @pytest.mark.asyncio
        async def run_test():
            output, _ = await skill.run({"value": 5})
            assert output["result"] == 10

        import asyncio

        asyncio.run(run_test())

    def test_complex_validation(self):
        """Test validation with complex schema."""

        class Address(BaseModel):
            street: str
            city: str
            zip_code: str = Field(pattern=r"^\d{5}$")

        class InputSchema(BaseModel):
            name: str
            addresses: list[Address]

        class TestSkill(Skill):
            name = "test_skill"
            version = "1.0.0"
            description = "Test skill"

            @validate_input(InputSchema)
            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                return {"address_count": len(input["addresses"])}

        skill = TestSkill()

        @pytest.mark.asyncio
        async def run_test():
            output, _ = await skill.run(
                {
                    "name": "Alice",
                    "addresses": [
                        {"street": "123 Main", "city": "NYC", "zip_code": "12345"}
                    ],
                }
            )
            assert output["address_count"] == 1

        import asyncio

        asyncio.run(run_test())

    def test_invalid_complex_validation(self):
        """Test validation failure with complex schema."""

        class Address(BaseModel):
            zip_code: str = Field(pattern=r"^\d{5}$")

        class InputSchema(BaseModel):
            address: Address

        class TestSkill(Skill):
            name = "test_skill"
            version = "1.0.0"
            description = "Test skill"

            @validate_input(InputSchema)
            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                return {}

        skill = TestSkill()

        @pytest.mark.asyncio
        async def run_test():
            with pytest.raises(InvalidInputError) as exc_info:
                await skill.run({"address": {"zip_code": "invalid"}})

            assert "zip_code" in str(exc_info.value)

        import asyncio

        asyncio.run(run_test())


class TestValidateOutput:
    """Test validate_output decorator."""

    def test_valid_output(self):
        """Test that valid output passes validation."""

        class OutputSchema(BaseModel):
            result: str
            count: int

        class TestSkill(Skill):
            name = "test_skill"
            version = "1.0.0"
            description = "Test skill"

            @validate_output(OutputSchema)
            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                return {"result": "success", "count": 42}

        skill = TestSkill()

        @pytest.mark.asyncio
        async def run_test():
            output, _ = await skill.run({})
            assert output["result"] == "success"
            assert output["count"] == 42

        import asyncio

        asyncio.run(run_test())

    def test_invalid_output(self):
        """Test that invalid output raises ValidationError."""

        class OutputSchema(BaseModel):
            result: str
            count: int

        class TestSkill(Skill):
            name = "test_skill"
            version = "1.0.0"
            description = "Test skill"

            @validate_output(OutputSchema)
            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                # Missing required 'count' field
                return {"result": "success"}

        skill = TestSkill()

        @pytest.mark.asyncio
        async def run_test():
            with pytest.raises(ValueError) as exc_info:
                await skill.run({})

            assert "output validation failed" in str(exc_info.value)

        import asyncio

        asyncio.run(run_test())

    def test_combined_validation(self):
        """Test using both input and output validation together."""

        class InputSchema(BaseModel):
            value: int

        class OutputSchema(BaseModel):
            doubled: int

        class TestSkill(Skill):
            name = "test_skill"
            version = "1.0.0"
            description = "Test skill"

            @validate_input(InputSchema)
            @validate_output(OutputSchema)
            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                return {"doubled": input["value"] * 2}

        skill = TestSkill()

        @pytest.mark.asyncio
        async def run_test():
            output, _ = await skill.run({"value": 5})
            assert output["doubled"] == 10

        import asyncio

        asyncio.run(run_test())
