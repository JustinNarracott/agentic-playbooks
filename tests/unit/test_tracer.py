"""Unit tests for ExecutionTracer and trace classes."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

from src.playbooks.tracer import ExecutionTrace, ExecutionTracer, StepTrace
from src.skills.base import SkillTrace


class TestStepTrace:
    """Test suite for StepTrace."""

    def test_create_step_trace(self) -> None:
        """Test creating a step trace."""
        started_at = datetime.utcnow()
        trace = StepTrace("test_step", "skill", started_at)

        assert trace.step_name == "test_step"
        assert trace.step_type == "skill"
        assert trace.started_at == started_at
        assert trace.completed_at is None
        assert trace.duration_ms is None
        assert trace.skill_trace is None
        assert trace.decision_taken is None
        assert trace.error is None
        assert trace.nested_steps == []

    def test_step_trace_to_dict_basic(self) -> None:
        """Test converting step trace to dict."""
        started_at = datetime.utcnow()
        completed_at = datetime.utcnow()

        trace = StepTrace("my_step", "skill", started_at)
        trace.completed_at = completed_at
        trace.duration_ms = 100

        result = trace.to_dict()

        assert result["step_name"] == "my_step"
        assert result["step_type"] == "skill"
        assert result["started_at"] == started_at.isoformat()
        assert result["completed_at"] == completed_at.isoformat()
        assert result["duration_ms"] == 100
        assert result["error"] is None

    def test_step_trace_to_dict_with_skill_trace(self) -> None:
        """Test converting step trace with skill trace to dict."""
        started_at = datetime.utcnow()
        completed_at = datetime.utcnow()

        step_trace = StepTrace("skill_step", "skill", started_at)
        step_trace.completed_at = completed_at
        step_trace.duration_ms = 50

        # Create a skill trace
        skill_trace = SkillTrace(
            skill_name="test_skill",
            execution_id="exec-123",
            input={"a": 1, "b": 2},
            started_at=started_at,
        )
        skill_trace.output = {"result": 3}
        skill_trace.completed_at = completed_at
        skill_trace.duration_ms = 40

        step_trace.skill_trace = skill_trace

        result = step_trace.to_dict()

        assert "skill_trace" in result
        assert result["skill_trace"]["skill_name"] == "test_skill"
        assert result["skill_trace"]["execution_id"] == "exec-123"
        assert result["skill_trace"]["input"] == {"a": 1, "b": 2}
        assert result["skill_trace"]["output"] == {"result": 3}
        assert result["skill_trace"]["duration_ms"] == 40

    def test_step_trace_to_dict_with_decision(self) -> None:
        """Test converting decision step trace to dict."""
        started_at = datetime.utcnow()

        trace = StepTrace("decision_step", "decision", started_at)
        trace.decision_taken = "branch_0: condition > 50"

        result = trace.to_dict()

        assert result["step_type"] == "decision"
        assert result["decision_taken"] == "branch_0: condition > 50"

    def test_step_trace_to_dict_with_nested_steps(self) -> None:
        """Test converting step trace with nested steps to dict."""
        started_at = datetime.utcnow()

        parent_trace = StepTrace("parent", "decision", started_at)

        # Add nested steps
        child1 = StepTrace("child1", "skill", started_at)
        child2 = StepTrace("child2", "skill", started_at)

        parent_trace.nested_steps = [child1, child2]

        result = parent_trace.to_dict()

        assert "nested_steps" in result
        assert len(result["nested_steps"]) == 2
        assert result["nested_steps"][0]["step_name"] == "child1"
        assert result["nested_steps"][1]["step_name"] == "child2"

    def test_step_trace_with_error(self) -> None:
        """Test step trace with error."""
        started_at = datetime.utcnow()

        trace = StepTrace("failed_step", "skill", started_at)
        trace.error = "Something went wrong"

        result = trace.to_dict()

        assert result["error"] == "Something went wrong"


class TestExecutionTrace:
    """Test suite for ExecutionTrace."""

    def test_create_execution_trace(self) -> None:
        """Test creating an execution trace."""
        trace = ExecutionTrace("test_playbook", "exec-123")

        assert trace.playbook_name == "test_playbook"
        assert trace.execution_id == "exec-123"
        assert trace.started_at is not None
        assert trace.completed_at is None
        assert trace.duration_ms is None
        assert trace.steps == []
        assert trace.final_context == {}
        assert trace.error is None
        assert trace.success is False

    def test_execution_trace_to_dict(self) -> None:
        """Test converting execution trace to dict."""
        trace = ExecutionTrace("my_playbook", "exec-456")
        trace.completed_at = datetime.utcnow()
        trace.duration_ms = 500
        trace.success = True
        trace.final_context = {"result": 42}

        result = trace.to_dict()

        assert result["playbook_name"] == "my_playbook"
        assert result["execution_id"] == "exec-456"
        assert result["duration_ms"] == 500
        assert result["success"] is True
        assert result["final_context"] == {"result": 42}
        assert result["error"] is None

    def test_execution_trace_with_steps(self) -> None:
        """Test execution trace with multiple steps."""
        trace = ExecutionTrace("playbook_with_steps", "exec-789")

        step1 = StepTrace("step1", "skill", datetime.utcnow())
        step2 = StepTrace("step2", "decision", datetime.utcnow())

        trace.steps = [step1, step2]

        result = trace.to_dict()

        assert len(result["steps"]) == 2
        assert result["steps"][0]["step_name"] == "step1"
        assert result["steps"][1]["step_name"] == "step2"

    def test_execution_trace_to_json(self) -> None:
        """Test exporting execution trace to JSON."""
        trace = ExecutionTrace("json_playbook", "exec-json")
        trace.success = True
        trace.final_context = {"value": 100}

        json_str = trace.to_json()

        # Parse to verify it's valid JSON
        parsed = json.loads(json_str)

        assert parsed["playbook_name"] == "json_playbook"
        assert parsed["execution_id"] == "exec-json"
        assert parsed["success"] is True
        assert parsed["final_context"] == {"value": 100}

    def test_execution_trace_to_json_compact(self) -> None:
        """Test exporting execution trace to compact JSON."""
        trace = ExecutionTrace("compact_playbook", "exec-compact")

        json_str = trace.to_json(indent=None)

        # Compact JSON should not have newlines
        assert "\n" not in json_str

    def test_execution_trace_save_to_file(self) -> None:
        """Test saving execution trace to file."""
        trace = ExecutionTrace("file_playbook", "exec-file")
        trace.success = True
        trace.final_context = {"saved": True}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "trace.json"

            trace.save_to_file(str(filepath))

            assert filepath.exists()

            # Read and verify
            with open(filepath, "r") as f:
                loaded = json.load(f)

            assert loaded["playbook_name"] == "file_playbook"
            assert loaded["final_context"] == {"saved": True}

    def test_execution_trace_with_error(self) -> None:
        """Test execution trace with error."""
        trace = ExecutionTrace("error_playbook", "exec-error")
        trace.error = "Execution failed"
        trace.success = False

        result = trace.to_dict()

        assert result["error"] == "Execution failed"
        assert result["success"] is False


class TestExecutionTracer:
    """Test suite for ExecutionTracer."""

    def test_create_trace(self) -> None:
        """Test creating trace via ExecutionTracer."""
        trace = ExecutionTracer.create_trace("tracer_playbook", "exec-create")

        assert isinstance(trace, ExecutionTrace)
        assert trace.playbook_name == "tracer_playbook"
        assert trace.execution_id == "exec-create"

    def test_create_step_trace(self) -> None:
        """Test creating step trace via ExecutionTracer."""
        started_at = datetime.utcnow()
        trace = ExecutionTracer.create_step_trace("tracer_step", "skill", started_at)

        assert isinstance(trace, StepTrace)
        assert trace.step_name == "tracer_step"
        assert trace.step_type == "skill"
        assert trace.started_at == started_at

    def test_create_step_trace_default_time(self) -> None:
        """Test creating step trace with default time."""
        trace = ExecutionTracer.create_step_trace("default_step", "decision")

        assert isinstance(trace, StepTrace)
        assert trace.started_at is not None

    def test_load_from_json(self) -> None:
        """Test loading trace from JSON string."""
        # Create a trace and export it
        original_trace = ExecutionTrace("load_playbook", "exec-load")
        original_trace.success = True
        original_trace.final_context = {"loaded": True}

        json_str = original_trace.to_json()

        # Load it back
        loaded_dict = ExecutionTracer.load_from_json(json_str)

        assert loaded_dict["playbook_name"] == "load_playbook"
        assert loaded_dict["execution_id"] == "exec-load"
        assert loaded_dict["success"] is True
        assert loaded_dict["final_context"] == {"loaded": True}

    def test_load_from_file(self) -> None:
        """Test loading trace from JSON file."""
        trace = ExecutionTrace("file_load_playbook", "exec-file-load")
        trace.success = True
        trace.final_context = {"file_loaded": True}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "trace_load.json"

            # Save
            trace.save_to_file(str(filepath))

            # Load
            loaded_dict = ExecutionTracer.load_from_file(str(filepath))

            assert loaded_dict["playbook_name"] == "file_load_playbook"
            assert loaded_dict["final_context"] == {"file_loaded": True}

    def test_round_trip_json(self) -> None:
        """Test saving and loading preserves data."""
        # Create complex trace
        trace = ExecutionTrace("round_trip", "exec-round")
        trace.success = True
        trace.final_context = {"a": 1, "b": [2, 3], "c": {"nested": True}}

        step1 = StepTrace("step1", "skill", datetime.utcnow())
        step1.duration_ms = 100

        step2 = StepTrace("step2", "decision", datetime.utcnow())
        step2.decision_taken = "branch_0"

        trace.steps = [step1, step2]

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "round_trip.json"

            # Save
            trace.save_to_file(str(filepath))

            # Load
            loaded = ExecutionTracer.load_from_file(str(filepath))

            # Verify
            assert loaded["playbook_name"] == "round_trip"
            assert loaded["success"] is True
            assert loaded["final_context"]["c"]["nested"] is True
            assert len(loaded["steps"]) == 2
            assert loaded["steps"][0]["step_name"] == "step1"
            assert loaded["steps"][0]["duration_ms"] == 100
            assert loaded["steps"][1]["decision_taken"] == "branch_0"
