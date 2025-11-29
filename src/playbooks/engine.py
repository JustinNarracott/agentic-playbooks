"""PlaybookEngine - executes playbooks with skills and decision logic."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from jinja2 import Environment, TemplateSyntaxError

from ..skills.base import Skill
from ..skills.registry import SkillRegistry
from .models import DecisionStep, Playbook, SkillStep, Step
from .tracer import ExecutionTrace, StepTrace


class ExecutionContext:
    """
    Context for playbook execution.

    Tracks variables and state throughout execution.
    """

    def __init__(self, initial_variables: Optional[Dict[str, Any]] = None) -> None:
        """Initialize execution context with optional initial variables."""
        self.variables: Dict[str, Any] = initial_variables or {}
        self._jinja_env = Environment(autoescape=False)

    def set_variable(self, name: str, value: Any) -> None:
        """Set a variable in the context."""
        self.variables[name] = value

    def get_variable(self, name: str) -> Any:
        """Get a variable from the context."""
        return self.variables.get(name)

    def evaluate_condition(self, condition: str) -> bool:
        """
        Evaluate a Jinja2 condition template.

        Args:
            condition: Jinja2 template condition string

        Returns:
            Boolean result of condition evaluation

        Raises:
            PlaybookExecutionError: If condition cannot be evaluated
        """
        try:
            template = self._jinja_env.from_string("{{ " + condition + " }}")
            result = template.render(**self.variables)
            # Convert string result to boolean
            if isinstance(result, str):
                result = result.strip().lower()
                return result not in ("false", "0", "", "none")
            return bool(result)
        except TemplateSyntaxError as e:
            raise PlaybookExecutionError(f"Invalid condition syntax: {e}")
        except Exception as e:
            raise PlaybookExecutionError(f"Failed to evaluate condition: {e}")

    def render_template(self, template_str: str) -> Any:
        """
        Render a Jinja2 template string with current context variables.

        Args:
            template_str: Template string to render

        Returns:
            Rendered result, attempting to preserve numeric types
        """
        try:
            template = self._jinja_env.from_string(str(template_str))
            result = template.render(**self.variables)

            # Try to preserve numeric types if the result looks numeric
            if isinstance(result, str):
                # Try to convert to int
                try:
                    if "." not in result:
                        return int(result)
                except (ValueError, TypeError):
                    pass

                # Try to convert to float
                try:
                    return float(result)
                except (ValueError, TypeError):
                    pass

            return result
        except Exception:
            # If rendering fails, return original value
            return template_str

    def render_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively render all template strings in a dictionary.

        Args:
            data: Dictionary potentially containing template strings

        Returns:
            Dictionary with all templates rendered
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.render_template(value)
            elif isinstance(value, dict):
                result[key] = self.render_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.render_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result


class PlaybookExecutionError(Exception):
    """Raised when playbook execution fails."""

    pass


class PlaybookEngine:
    """
    Executes playbooks with skills and decision logic.

    The engine handles:
    - Executing skill steps via SkillRegistry
    - Evaluating decision conditions with Jinja2
    - Passing outputs between steps via ExecutionContext
    - Generating comprehensive execution traces
    """

    def __init__(self, skill_registry: Optional[SkillRegistry] = None) -> None:
        """
        Initialize the PlaybookEngine.

        Args:
            skill_registry: Optional SkillRegistry instance. If not provided,
                          uses the global singleton instance.
        """
        self.skill_registry = skill_registry or SkillRegistry.get_instance()

    async def execute(
        self,
        playbook: Playbook,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionTrace:
        """
        Execute a playbook.

        Args:
            playbook: The playbook to execute
            initial_context: Optional initial context variables

        Returns:
            ExecutionTrace with complete execution details

        Raises:
            PlaybookExecutionError: If execution fails
        """
        execution_id = str(uuid.uuid4())
        trace = ExecutionTrace(playbook.metadata.name, execution_id)

        # Merge playbook variables with initial context
        context_vars = {**playbook.variables, **(initial_context or {})}
        context = ExecutionContext(context_vars)

        try:
            # Execute all steps
            for step in playbook.steps:
                await self._execute_step(step, context, trace.steps)

            trace.success = True

        except Exception as e:
            trace.error = str(e)
            trace.success = False
            raise PlaybookExecutionError(f"Playbook execution failed: {e}")

        finally:
            trace.completed_at = datetime.utcnow()
            trace.duration_ms = int(
                (trace.completed_at - trace.started_at).total_seconds() * 1000
            )
            trace.final_context = context.variables.copy()

        return trace

    async def _execute_step(
        self,
        step: Step,
        context: ExecutionContext,
        traces: List[StepTrace],
    ) -> None:
        """
        Execute a single step (skill or decision).

        Args:
            step: The step to execute
            context: Current execution context
            traces: List to append step trace to
        """
        if isinstance(step, SkillStep):
            await self._execute_skill_step(step, context, traces)
        elif isinstance(step, DecisionStep):
            await self._execute_decision_step(step, context, traces)
        else:
            raise PlaybookExecutionError(f"Unknown step type: {type(step)}")

    async def _execute_skill_step(
        self,
        step: SkillStep,
        context: ExecutionContext,
        traces: List[StepTrace],
    ) -> None:
        """
        Execute a skill step.

        Args:
            step: The skill step to execute
            context: Current execution context
            traces: List to append step trace to

        Raises:
            PlaybookExecutionError: If skill not found or execution fails
        """
        step_trace = StepTrace(
            step_name=step.name,
            step_type="skill",
            started_at=datetime.utcnow(),
        )
        traces.append(step_trace)

        try:
            # Get skill from registry
            skill_class = self.skill_registry.get(step.skill)
            if skill_class is None:
                raise PlaybookExecutionError(f"Skill not found: {step.skill}")

            # Instantiate skill
            skill: Skill = skill_class()

            # Render input templates with current context
            rendered_input = context.render_dict(step.input)

            # Execute skill
            output, skill_trace = await skill.run(rendered_input)

            # Store output in context if output_var specified
            if step.output_var:
                context.set_variable(step.output_var, output)

            # Record trace
            step_trace.skill_trace = skill_trace
            step_trace.completed_at = datetime.utcnow()
            step_trace.duration_ms = int(
                (step_trace.completed_at - step_trace.started_at).total_seconds() * 1000
            )

        except Exception as e:
            step_trace.error = str(e)
            step_trace.completed_at = datetime.utcnow()
            raise

    async def _execute_decision_step(
        self,
        step: DecisionStep,
        context: ExecutionContext,
        traces: List[StepTrace],
    ) -> None:
        """
        Execute a decision step.

        Args:
            step: The decision step to execute
            context: Current execution context
            traces: List to append step trace to
        """
        step_trace = StepTrace(
            step_name=step.name,
            step_type="decision",
            started_at=datetime.utcnow(),
        )
        traces.append(step_trace)

        try:
            # Evaluate branches in order
            branch_taken = False
            for i, branch in enumerate(step.branches):
                if context.evaluate_condition(branch.condition):
                    step_trace.decision_taken = f"branch_{i}: {branch.condition}"
                    # Execute branch steps
                    for branch_step in branch.steps:
                        await self._execute_step(
                            branch_step, context, step_trace.nested_steps
                        )
                    branch_taken = True
                    break

            # Execute default if no branch matched
            if not branch_taken and step.default:
                step_trace.decision_taken = "default"
                for default_step in step.default:
                    await self._execute_step(
                        default_step, context, step_trace.nested_steps
                    )

            step_trace.completed_at = datetime.utcnow()
            step_trace.duration_ms = int(
                (step_trace.completed_at - step_trace.started_at).total_seconds() * 1000
            )

        except Exception as e:
            step_trace.error = str(e)
            step_trace.completed_at = datetime.utcnow()
            raise
