"""Input validation decorator for skills."""

from functools import wraps
from typing import Any, Callable, Dict, Type, TypeVar, cast

from pydantic import BaseModel, ValidationError

from ..playbooks.errors import InvalidInputError

F = TypeVar("F", bound=Callable[..., Any])


def validate_input(schema: Type[BaseModel]) -> Callable[[F], F]:
    """
    Decorator to validate skill inputs against a Pydantic schema.

    Validates input data before executing the skill's execute() method.
    Raises InvalidInputError with detailed validation errors if validation fails.

    Args:
        schema: Pydantic BaseModel class to validate against

    Returns:
        Decorated function

    Example:
        ```python
        from pydantic import BaseModel
        from src.skills.base import Skill
        from src.skills.validation import validate_input

        class MySkillInput(BaseModel):
            value: str
            count: int

        class MySkill(Skill):
            name = "my_skill"
            version = "1.0.0"
            description = "Example skill with validation"

            @validate_input(MySkillInput)
            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                # input is guaranteed to be valid here
                return {"result": input["value"] * input["count"]}
        ```
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(self: Any, input: Dict[str, Any]) -> Dict[str, Any]:
            # Validate input against schema
            try:
                validated = schema(**input)
                # Replace input with validated data (converts to dict)
                validated_input = validated.model_dump()
            except ValidationError as e:
                # Raise our custom error with context
                raise InvalidInputError(
                    skill_name=self.name,
                    schema=schema,
                    input_data=input,
                    validation_error=e,
                ) from e

            # Call the original function with validated input
            result: Dict[str, Any] = await func(self, validated_input)
            return result

        return cast(F, wrapper)

    return decorator


def validate_output(schema: Type[BaseModel]) -> Callable[[F], F]:
    """
    Decorator to validate skill outputs against a Pydantic schema.

    Validates output data after executing the skill's execute() method.
    Raises ValidationError if output doesn't match schema.

    Args:
        schema: Pydantic BaseModel class to validate against

    Returns:
        Decorated function

    Example:
        ```python
        from pydantic import BaseModel
        from src.skills.base import Skill
        from src.skills.validation import validate_output

        class MySkillOutput(BaseModel):
            result: str
            confidence: float

        class MySkill(Skill):
            name = "my_skill"
            version = "1.0.0"
            description = "Example skill with output validation"

            @validate_output(MySkillOutput)
            async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
                # Must return dict matching MySkillOutput schema
                return {
                    "result": "success",
                    "confidence": 0.95
                }
        ```
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(self: Any, input: Dict[str, Any]) -> Dict[str, Any]:
            # Call the original function
            output = await func(self, input)

            # Validate output against schema
            try:
                validated = schema(**output)
                # Return validated output as dict
                result: Dict[str, Any] = validated.model_dump()
                return result
            except ValidationError as e:
                raise ValueError(
                    f"Skill '{self.name}' output validation failed: {e}"
                ) from e

        return cast(F, wrapper)

    return decorator
