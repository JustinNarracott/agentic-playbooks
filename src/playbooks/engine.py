"""PlaybookEngine - executes playbooks with skills and decision logic."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from jinja2 import Environment, TemplateSyntaxError

from ..skills.base import Skill
from ..skills.registry import SkillRegistry
from .checkpoint import CheckpointManager
from .errors import (
    PlaybookExecutionError,
    SkillExecutionError,
    SkillNotFoundError,
    TemplateError,
)
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

    def evaluate_condition(self, condition: str, step_name: str = "unknown") -> bool:
        """
        Evaluate a Jinja2 condition template.

        Args:
            condition: Jinja2 template condition string
            step_name: Name of the step for error context

        Returns:
            Boolean result of condition evaluation

        Raises:
            TemplateError: If condition cannot be evaluated
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
            raise TemplateError(
                template_str=condition,
                error=e,
                step_name=step_name,
                field_name="condition",
                available_vars=self.variables,
            ) from e
        except Exception as e:
            raise TemplateError(
                template_str=condition,
                error=e,
                step_name=step_name,
                field_name="condition",
                available_vars=self.variables,
            ) from e

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
        resume_from: Optional[str] = None,
        checkpoint_dir: Optional[str] = None,
    ) -> ExecutionTrace:
        """
        Execute a playbook with optional checkpoint/resume support.

        Args:
            playbook: The playbook to execute
            initial_context: Optional initial context variables
            resume_from: Optional execution ID to resume from checkpoint
            checkpoint_dir: Optional directory for checkpoint files

        Returns:
            ExecutionTrace with complete execution details

        Raises:
            PlaybookExecutionError: If execution fails
            CheckpointError: If checkpoint operations fail
        """
        # Initialize checkpoint manager if checkpoint_dir provided
        checkpoint_manager = (
            CheckpointManager(checkpoint_dir) if checkpoint_dir else None
        )

        # Resume from checkpoint if requested
        if resume_from and checkpoint_manager:
            checkpoint = checkpoint_manager.load_checkpoint(resume_from)
            if not checkpoint:
                raise PlaybookExecutionError(
                    f"Checkpoint not found for execution: {resume_from}"
                )

            execution_id = checkpoint["execution_id"]
            trace = self._restore_trace(checkpoint)
            context = ExecutionContext(checkpoint["context"])
            start_step = checkpoint["current_step"]
        else:
            execution_id = str(uuid.uuid4())
            trace = ExecutionTrace(playbook.metadata.name, execution_id)
            context_vars = {**playbook.variables, **(initial_context or {})}
            context = ExecutionContext(context_vars)
            start_step = 0

        try:
            # Execute steps (starting from checkpoint if resuming)
            for i, step in enumerate(playbook.steps[start_step:], start=start_step):
                await self._execute_step(step, context, trace.steps)

                # Save checkpoint after each step if enabled
                if checkpoint_manager:
                    checkpoint_manager.save_checkpoint(
                        execution_id=execution_id,
                        playbook_name=playbook.metadata.name,
                        current_step=i + 1,
                        context_vars=context.variables,
                        completed_steps=trace.steps,
                    )

            trace.success = True

            # Clean up checkpoint on successful completion
            if checkpoint_manager:
                checkpoint_manager.delete_checkpoint(execution_id)

        except Exception as e:
            trace.error = str(e)
            trace.success = False

            # Provide helpful message about resuming from checkpoint
            if checkpoint_manager:
                print(f"\nExecution failed at step {len(trace.steps)}.")
                print("Resume with:")
                print(
                    f"  engine.execute(playbook, resume_from='{execution_id}', "
                    f"checkpoint_dir='{checkpoint_dir}')"
                )

            raise

        finally:
            trace.completed_at = datetime.utcnow()
            trace.duration_ms = int(
                (trace.completed_at - trace.started_at).total_seconds() * 1000
            )
            trace.final_context = context.variables.copy()

        return trace

    def _restore_trace(self, checkpoint: Dict[str, Any]) -> ExecutionTrace:
        """
        Restore ExecutionTrace from checkpoint data.

        Args:
            checkpoint: Checkpoint dictionary

        Returns:
            Restored ExecutionTrace
        """
        trace = ExecutionTrace(
            playbook_name=checkpoint["playbook_name"],
            execution_id=checkpoint["execution_id"],
        )

        # Restore completed steps
        for step_data in checkpoint.get("completed_steps", []):
            step_trace = StepTrace(
                step_name=step_data.get("step_name", "unknown"),
                step_type=step_data.get("step_type", "unknown"),
                started_at=datetime.fromisoformat(step_data["started_at"]),
            )

            if step_data.get("completed_at"):
                step_trace.completed_at = datetime.fromisoformat(
                    step_data["completed_at"]
                )

            if step_data.get("duration_ms"):
                step_trace.duration_ms = step_data["duration_ms"]

            if step_data.get("error"):
                step_trace.error = step_data["error"]

            trace.steps.append(step_trace)

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
                raise SkillNotFoundError(
                    skill_name=step.skill,
                    step_name=step.name,
                    available_skills=self.skill_registry.list_skills(),
                    playbook_name="unknown",  # Will be set by execute() context
                )

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

        except SkillNotFoundError:
            # Re-raise SkillNotFoundError as-is
            step_trace.error = "Skill not found"
            step_trace.completed_at = datetime.utcnow()
            raise
        except Exception as e:
            # Wrap other exceptions in SkillExecutionError
            step_trace.error = str(e)
            step_trace.completed_at = datetime.utcnow()

            # Extract reasoning from skill trace if available
            reasoning = None
            if step_trace.skill_trace and hasattr(step_trace.skill_trace, "reasoning"):
                reasoning = step_trace.skill_trace.reasoning

            raise SkillExecutionError(
                skill_name=step.skill,
                step_name=step.name,
                input_data=rendered_input,
                original_error=e,
                reasoning=reasoning,
            ) from e

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
                if context.evaluate_condition(branch.condition, step_name=step.name):
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
