"""Unit tests for PlaybookEngine."""

from typing import Any, Dict

import pytest

from src.playbooks.engine import (
    ExecutionContext,
    PlaybookEngine,
    PlaybookExecutionError,
)
from src.playbooks.models import (
    DecisionBranch,
    DecisionStep,
    Playbook,
    PlaybookMetadata,
    SkillStep,
)
from src.skills.base import Skill
from src.skills.registry import SkillRegistry


# Test Skills
class AddNumbersSkill(Skill):
    """Test skill that adds two numbers."""

    name = "add_numbers"
    version = "1.0.0"
    description = "Adds two numbers"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """Add two numbers."""
        return {"result": input["a"] + input["b"]}


class MultiplySkill(Skill):
    """Test skill that multiplies two numbers."""

    name = "multiply"
    version = "1.0.0"
    description = "Multiplies two numbers"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """Multiply two numbers."""
        return {"result": input["a"] * input["b"]}


class GreetingSkill(Skill):
    """Test skill that creates a greeting."""

    name = "greeting"
    version = "1.0.0"
    description = "Creates a greeting"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """Create greeting."""
        name = input.get("name", "World")
        return {"message": f"Hello, {name}!"}


class ErrorSkill(Skill):
    """Test skill that always raises an error."""

    name = "error_skill"
    version = "1.0.0"
    description = "Always fails"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """Raise an error."""
        raise ValueError("Intentional error for testing")


@pytest.fixture
def skill_registry() -> SkillRegistry:
    """Create a skill registry with test skills."""
    registry = SkillRegistry()
    registry.register(AddNumbersSkill)
    registry.register(MultiplySkill)
    registry.register(GreetingSkill)
    registry.register(ErrorSkill)
    return registry


@pytest.fixture
def engine(skill_registry: SkillRegistry) -> PlaybookEngine:
    """Create a PlaybookEngine instance."""
    return PlaybookEngine(skill_registry)


class TestExecutionContext:
    """Test suite for ExecutionContext."""

    def test_set_and_get_variable(self) -> None:
        """Test setting and getting variables."""
        context = ExecutionContext()
        context.set_variable("x", 10)
        assert context.get_variable("x") == 10

    def test_initial_variables(self) -> None:
        """Test initialization with variables."""
        context = ExecutionContext({"a": 1, "b": 2})
        assert context.get_variable("a") == 1
        assert context.get_variable("b") == 2

    def test_evaluate_condition_true(self) -> None:
        """Test evaluating a true condition."""
        context = ExecutionContext({"score": 85})
        assert context.evaluate_condition("score > 80") is True

    def test_evaluate_condition_false(self) -> None:
        """Test evaluating a false condition."""
        context = ExecutionContext({"score": 75})
        assert context.evaluate_condition("score > 80") is False

    def test_evaluate_condition_complex(self) -> None:
        """Test evaluating complex conditions."""
        context = ExecutionContext({"x": 10, "y": 20})
        assert context.evaluate_condition("x + y > 25") is True
        assert context.evaluate_condition("x == 10 and y == 20") is True

    def test_evaluate_condition_invalid_syntax(self) -> None:
        """Test invalid condition syntax."""
        context = ExecutionContext()
        with pytest.raises(PlaybookExecutionError, match="Invalid condition syntax"):
            context.evaluate_condition("{{ invalid")

    def test_render_template(self) -> None:
        """Test rendering a template."""
        context = ExecutionContext({"name": "Alice"})
        result = context.render_template("Hello, {{ name }}!")
        assert result == "Hello, Alice!"

    def test_render_dict(self) -> None:
        """Test rendering templates in a dictionary."""
        context = ExecutionContext({"x": 10, "y": 20})
        data = {"a": "{{ x }}", "b": "{{ y }}", "c": "plain"}
        result = context.render_dict(data)
        assert result["a"] == 10  # Numeric types are preserved
        assert result["b"] == 20  # Numeric types are preserved
        assert result["c"] == "plain"

    def test_render_dict_nested(self) -> None:
        """Test rendering nested dictionaries."""
        context = ExecutionContext({"value": 42})
        data = {"nested": {"key": "{{ value }}"}}
        result = context.render_dict(data)
        assert result["nested"]["key"] == 42  # Numeric types are preserved


class TestPlaybookEngine:
    """Test suite for PlaybookEngine."""

    @pytest.mark.asyncio
    async def test_execute_simple_skill(
        self, engine: PlaybookEngine, skill_registry: SkillRegistry
    ) -> None:
        """Test executing a simple playbook with one skill."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="simple_test"),
            steps=[
                SkillStep(
                    name="add",
                    skill="add_numbers",
                    input={"a": 5, "b": 3},
                    output_var="sum",
                )
            ],
        )

        trace = await engine.execute(playbook)

        assert trace.success is True
        assert trace.error is None
        assert len(trace.steps) == 1
        assert trace.final_context["sum"]["result"] == 8
        assert trace.steps[0].skill_trace is not None

    @pytest.mark.asyncio
    async def test_execute_multiple_skills(
        self, engine: PlaybookEngine, skill_registry: SkillRegistry
    ) -> None:
        """Test executing multiple skills in sequence."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="multi_step"),
            steps=[
                SkillStep(
                    name="add",
                    skill="add_numbers",
                    input={"a": 5, "b": 3},
                    output_var="sum",
                ),
                SkillStep(
                    name="multiply",
                    skill="multiply",
                    input={"a": "{{ sum.result }}", "b": 2},
                    output_var="product",
                ),
            ],
        )

        trace = await engine.execute(playbook)

        assert trace.success is True
        assert len(trace.steps) == 2
        assert trace.final_context["sum"]["result"] == 8
        assert trace.final_context["product"]["result"] == 16

    @pytest.mark.asyncio
    async def test_execute_with_initial_context(
        self, engine: PlaybookEngine, skill_registry: SkillRegistry
    ) -> None:
        """Test executing with initial context variables."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="with_context"),
            steps=[
                SkillStep(
                    name="greet",
                    skill="greeting",
                    input={"name": "{{ user_name }}"},
                    output_var="greeting",
                )
            ],
        )

        trace = await engine.execute(playbook, initial_context={"user_name": "Bob"})

        assert trace.success is True
        assert trace.final_context["greeting"]["message"] == "Hello, Bob!"

    @pytest.mark.asyncio
    async def test_execute_decision_true_branch(
        self, engine: PlaybookEngine, skill_registry: SkillRegistry
    ) -> None:
        """Test decision step taking true branch."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="decision_test"),
            steps=[
                SkillStep(
                    name="calculate",
                    skill="add_numbers",
                    input={"a": 50, "b": 50},
                    output_var="total",
                ),
                DecisionStep(
                    name="check_total",
                    branches=[
                        DecisionBranch(
                            condition="total.result > 80",
                            steps=[
                                SkillStep(
                                    name="high_greeting",
                                    skill="greeting",
                                    input={"name": "High Score"},
                                    output_var="message",
                                )
                            ],
                        )
                    ],
                ),
            ],
        )

        trace = await engine.execute(playbook)

        assert trace.success is True
        assert len(trace.steps) == 2
        assert trace.steps[1].decision_taken == "branch_0: total.result > 80"
        assert len(trace.steps[1].nested_steps) == 1
        assert trace.final_context["message"]["message"] == "Hello, High Score!"

    @pytest.mark.asyncio
    async def test_execute_decision_default_branch(
        self, engine: PlaybookEngine, skill_registry: SkillRegistry
    ) -> None:
        """Test decision step taking default branch."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="decision_default"),
            steps=[
                SkillStep(
                    name="calculate",
                    skill="add_numbers",
                    input={"a": 10, "b": 20},
                    output_var="total",
                ),
                DecisionStep(
                    name="check_total",
                    branches=[
                        DecisionBranch(
                            condition="total.result > 100",
                            steps=[
                                SkillStep(
                                    name="high_greeting",
                                    skill="greeting",
                                    input={"name": "High"},
                                )
                            ],
                        )
                    ],
                    default=[
                        SkillStep(
                            name="low_greeting",
                            skill="greeting",
                            input={"name": "Low"},
                            output_var="message",
                        )
                    ],
                ),
            ],
        )

        trace = await engine.execute(playbook)

        assert trace.success is True
        assert trace.steps[1].decision_taken == "default"
        assert len(trace.steps[1].nested_steps) == 1
        assert trace.final_context["message"]["message"] == "Hello, Low!"

    @pytest.mark.asyncio
    async def test_execute_decision_multiple_branches(
        self, engine: PlaybookEngine, skill_registry: SkillRegistry
    ) -> None:
        """Test decision with multiple branches."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="multi_branch"),
            steps=[
                SkillStep(
                    name="calculate",
                    skill="add_numbers",
                    input={"a": 30, "b": 30},
                    output_var="score",
                ),
                DecisionStep(
                    name="categorize",
                    branches=[
                        DecisionBranch(
                            condition="score.result > 80",
                            steps=[
                                SkillStep(
                                    name="high",
                                    skill="greeting",
                                    input={"name": "High"},
                                    output_var="category",
                                )
                            ],
                        ),
                        DecisionBranch(
                            condition="score.result > 40",
                            steps=[
                                SkillStep(
                                    name="medium",
                                    skill="greeting",
                                    input={"name": "Medium"},
                                    output_var="category",
                                )
                            ],
                        ),
                    ],
                    default=[
                        SkillStep(
                            name="low",
                            skill="greeting",
                            input={"name": "Low"},
                            output_var="category",
                        )
                    ],
                ),
            ],
        )

        trace = await engine.execute(playbook)

        assert trace.success is True
        assert trace.steps[1].decision_taken == "branch_1: score.result > 40"
        assert trace.final_context["category"]["message"] == "Hello, Medium!"

    @pytest.mark.asyncio
    async def test_execute_skill_not_found(
        self, engine: PlaybookEngine, skill_registry: SkillRegistry
    ) -> None:
        """Test error when skill is not found."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="missing_skill"),
            steps=[
                SkillStep(
                    name="test",
                    skill="nonexistent_skill",
                    input={},
                    output_var="result",
                )
            ],
        )

        with pytest.raises(PlaybookExecutionError, match="Skill not found"):
            await engine.execute(playbook)

    @pytest.mark.asyncio
    async def test_execute_skill_error(
        self, engine: PlaybookEngine, skill_registry: SkillRegistry
    ) -> None:
        """Test handling of skill execution error."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="error_test"),
            steps=[
                SkillStep(
                    name="fail", skill="error_skill", input={}, output_var="result"
                )
            ],
        )

        with pytest.raises(PlaybookExecutionError, match="Playbook execution failed"):
            await engine.execute(playbook)

    @pytest.mark.asyncio
    async def test_execution_trace_timing(
        self, engine: PlaybookEngine, skill_registry: SkillRegistry
    ) -> None:
        """Test that execution trace captures timing information."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="timing_test"),
            steps=[
                SkillStep(
                    name="add",
                    skill="add_numbers",
                    input={"a": 1, "b": 1},
                    output_var="result",
                )
            ],
        )

        trace = await engine.execute(playbook)

        assert trace.started_at is not None
        assert trace.completed_at is not None
        assert trace.duration_ms is not None
        assert trace.duration_ms >= 0

        step_trace = trace.steps[0]
        assert step_trace.started_at is not None
        assert step_trace.completed_at is not None
        assert step_trace.duration_ms is not None

    @pytest.mark.asyncio
    async def test_execute_with_playbook_variables(
        self, engine: PlaybookEngine, skill_registry: SkillRegistry
    ) -> None:
        """Test that playbook variables are available in context."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="var_test"),
            variables={"multiplier": 3},
            steps=[
                SkillStep(
                    name="multiply",
                    skill="multiply",
                    input={"a": 5, "b": "{{ multiplier }}"},
                    output_var="result",
                )
            ],
        )

        trace = await engine.execute(playbook)

        assert trace.success is True
        assert trace.final_context["result"]["result"] == 15

    @pytest.mark.asyncio
    async def test_initial_context_overrides_playbook_variables(
        self, engine: PlaybookEngine, skill_registry: SkillRegistry
    ) -> None:
        """Test that initial context overrides playbook variables."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="override_test"),
            variables={"value": 10},
            steps=[
                SkillStep(
                    name="add",
                    skill="add_numbers",
                    input={"a": "{{ value }}", "b": 5},
                    output_var="result",
                )
            ],
        )

        trace = await engine.execute(playbook, initial_context={"value": 20})

        assert trace.success is True
        assert trace.final_context["result"]["result"] == 25  # 20 + 5, not 10 + 5

    @pytest.mark.asyncio
    async def test_nested_decision_steps(
        self, engine: PlaybookEngine, skill_registry: SkillRegistry
    ) -> None:
        """Test nested decision steps."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="nested_decision"),
            steps=[
                SkillStep(
                    name="get_score",
                    skill="add_numbers",
                    input={"a": 45, "b": 45},
                    output_var="score",
                ),
                DecisionStep(
                    name="outer_check",
                    branches=[
                        DecisionBranch(
                            condition="score.result > 50",
                            steps=[
                                DecisionStep(
                                    name="inner_check",
                                    branches=[
                                        DecisionBranch(
                                            condition="score.result > 80",
                                            steps=[
                                                SkillStep(
                                                    name="very_high",
                                                    skill="greeting",
                                                    input={"name": "Very High"},
                                                    output_var="final",
                                                )
                                            ],
                                        )
                                    ],
                                    default=[
                                        SkillStep(
                                            name="high",
                                            skill="greeting",
                                            input={"name": "High"},
                                            output_var="final",
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                ),
            ],
        )

        trace = await engine.execute(playbook)

        assert trace.success is True
        assert trace.steps[1].decision_taken == "branch_0: score.result > 50"
        # The nested decision should have taken the high branch (90 > 80)
        assert trace.final_context["final"]["message"] == "Hello, Very High!"
