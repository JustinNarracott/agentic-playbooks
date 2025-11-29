"""Unit tests for BatchExecutor."""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from src.playbooks import (
    BatchExecutor,
    BatchResult,
    BatchResults,
    Playbook,
    PlaybookEngine,
    PlaybookMetadata,
    SkillStep,
)
from src.skills.base import Skill
from src.skills.registry import SkillRegistry


class DummySkill(Skill):
    """Dummy skill for testing."""

    name = "dummy_skill"
    version = "1.0.0"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        # Simulate some work
        await asyncio.sleep(0.01)
        return {"result": f"Processed: {input.get('value', 'none')}"}


class FailingSkill(Skill):
    """Skill that always fails."""

    name = "failing_skill"
    version = "1.0.0"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("Intentional failure")


class TestBatchResult:
    """Test suite for BatchResult."""

    def test_batch_result_success(self) -> None:
        """Test BatchResult with successful execution."""
        from src.playbooks.tracer import ExecutionTrace

        trace = ExecutionTrace(playbook_name="test", execution_id="test-123")
        trace.success = True
        trace.final_context = {}

        result = BatchResult(
            index=0,
            input_context={"value": "test"},
            trace=trace,
            duration_ms=100.0,
        )

        assert result.success is True
        assert result.error is None
        assert result.index == 0
        assert result.duration_ms == 100.0

    def test_batch_result_failure(self) -> None:
        """Test BatchResult with failed execution."""
        result = BatchResult(
            index=1,
            input_context={"value": "test"},
            error="Test error",
            duration_ms=50.0,
        )

        assert result.success is False
        assert result.error == "Test error"
        assert result.trace is None

    def test_batch_result_to_dict(self) -> None:
        """Test BatchResult serialization."""
        result = BatchResult(
            index=0,
            input_context={"value": "test"},
            error="Test error",
            duration_ms=100.0,
        )

        result_dict = result.to_dict()

        assert result_dict["index"] == 0
        assert result_dict["success"] is False
        assert result_dict["error"] == "Test error"
        assert result_dict["duration_ms"] == 100.0
        assert result_dict["input_context"] == {"value": "test"}
        assert result_dict["trace"] is None


class TestBatchResults:
    """Test suite for BatchResults."""

    def test_batch_results_empty(self) -> None:
        """Test empty BatchResults."""
        results = BatchResults()

        assert results.total == 0
        assert results.success_count == 0
        assert results.failure_count == 0
        assert results.avg_duration_ms == 0.0

    def test_batch_results_properties(self) -> None:
        """Test BatchResults aggregation properties."""
        from src.playbooks.tracer import ExecutionTrace

        successful_trace = ExecutionTrace(playbook_name="test", execution_id="test-123")
        successful_trace.success = True
        successful_trace.final_context = {}

        results = BatchResults(
            results=[
                BatchResult(
                    index=0,
                    input_context={},
                    trace=successful_trace,
                    duration_ms=100.0,
                ),
                BatchResult(
                    index=1,
                    input_context={},
                    error="Error",
                    duration_ms=50.0,
                ),
                BatchResult(
                    index=2,
                    input_context={},
                    trace=successful_trace,
                    duration_ms=150.0,
                ),
            ],
            total_duration_ms=500.0,
        )

        assert results.total == 3
        assert results.success_count == 2
        assert results.failure_count == 1
        assert results.avg_duration_ms == 100.0  # (100 + 50 + 150) / 3
        assert results.total_duration_ms == 500.0

    def test_batch_results_to_dict(self) -> None:
        """Test BatchResults serialization."""
        results = BatchResults(
            results=[
                BatchResult(
                    index=0,
                    input_context={},
                    error="Error",
                    duration_ms=100.0,
                )
            ],
            total_duration_ms=200.0,
        )

        results_dict = results.to_dict()

        assert results_dict["total"] == 1
        assert results_dict["success_count"] == 0
        assert results_dict["failure_count"] == 1
        assert results_dict["avg_duration_ms"] == 100.0
        assert results_dict["total_duration_ms"] == 200.0
        assert len(results_dict["results"]) == 1

    def test_batch_results_to_json(self) -> None:
        """Test BatchResults JSON export."""
        results = BatchResults(
            results=[
                BatchResult(
                    index=0,
                    input_context={"value": "test"},
                    error="Error",
                    duration_ms=100.0,
                )
            ],
            total_duration_ms=200.0,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            results.to_json(temp_path)

            # Verify file was created and contains valid JSON
            with open(temp_path, "r") as f:
                data = json.load(f)

            assert data["total"] == 1
            assert data["success_count"] == 0
            assert data["failure_count"] == 1
        finally:
            Path(temp_path).unlink()

    def test_batch_results_to_csv(self) -> None:
        """Test BatchResults CSV export."""
        results = BatchResults(
            results=[
                BatchResult(
                    index=0,
                    input_context={},
                    error="Test error",
                    duration_ms=100.0,
                ),
                BatchResult(
                    index=1,
                    input_context={},
                    duration_ms=50.0,
                ),
            ],
            total_duration_ms=200.0,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = f.name

        try:
            results.to_csv(temp_path)

            # Verify file was created
            assert Path(temp_path).exists()

            # Read and verify CSV content
            with open(temp_path, "r") as f:
                lines = f.readlines()

            assert len(lines) == 3  # Header + 2 rows
            assert "index,success,duration_ms,error" in lines[0]
        finally:
            Path(temp_path).unlink()


class TestBatchExecutor:
    """Test suite for BatchExecutor."""

    @pytest.mark.asyncio
    async def test_batch_executor_initialization(self) -> None:
        """Test BatchExecutor can be initialized."""
        executor = BatchExecutor()
        assert executor is not None
        assert executor.max_concurrency == 5
        assert executor.show_progress is False

    @pytest.mark.asyncio
    async def test_batch_executor_custom_params(self) -> None:
        """Test BatchExecutor with custom parameters."""
        executor = BatchExecutor(max_concurrency=10, show_progress=True)
        assert executor.max_concurrency == 10
        assert executor.show_progress is True

    @pytest.mark.asyncio
    async def test_execute_batch_empty_inputs(self) -> None:
        """Test batch execution with empty inputs."""
        registry = SkillRegistry()
        registry.register(DummySkill)

        engine = PlaybookEngine(registry)
        executor = BatchExecutor(engine=engine)

        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0"),
            steps=[SkillStep(name="step1", skill="dummy_skill", input={})],
        )

        results = await executor.execute_batch(playbook, [])

        assert results.total == 0
        assert results.success_count == 0
        assert results.failure_count == 0

    @pytest.mark.asyncio
    async def test_execute_batch_single_input(self) -> None:
        """Test batch execution with single input."""
        registry = SkillRegistry()
        registry.register(DummySkill)

        engine = PlaybookEngine(registry)
        executor = BatchExecutor(engine=engine)

        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[
                SkillStep(
                    name="step1",
                    skill="dummy_skill",
                    input={"value": "{{ input_value }}"},
                )
            ],
        )

        inputs = [{"input_value": "test1"}]

        results = await executor.execute_batch(playbook, inputs)

        assert results.total == 1
        assert results.success_count == 1
        assert results.failure_count == 0
        assert results.results[0].success is True
        assert results.results[0].input_context == {"input_value": "test1"}

    @pytest.mark.asyncio
    async def test_execute_batch_multiple_inputs(self) -> None:
        """Test batch execution with multiple inputs."""
        registry = SkillRegistry()
        registry.register(DummySkill)

        engine = PlaybookEngine(registry)
        executor = BatchExecutor(engine=engine, max_concurrency=2)

        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[
                SkillStep(
                    name="step1",
                    skill="dummy_skill",
                    input={"value": "{{ input_value }}"},
                )
            ],
        )

        inputs = [
            {"input_value": f"test{i}"} for i in range(10)
        ]  # 10 parallel executions

        results = await executor.execute_batch(playbook, inputs)

        assert results.total == 10
        assert results.success_count == 10
        assert results.failure_count == 0
        assert all(r.success for r in results.results)

    @pytest.mark.asyncio
    async def test_execute_batch_with_failures(self) -> None:
        """Test batch execution with some failures."""
        registry = SkillRegistry()
        registry.register(FailingSkill)

        engine = PlaybookEngine(registry)
        executor = BatchExecutor(engine=engine)

        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[SkillStep(name="step1", skill="failing_skill", input={})],
        )

        inputs = [{"value": f"test{i}"} for i in range(5)]

        results = await executor.execute_batch(playbook, inputs)

        assert results.total == 5
        assert results.success_count == 0
        assert results.failure_count == 5
        assert all(not r.success for r in results.results)
        assert all(r.error is not None for r in results.results)

    @pytest.mark.asyncio
    async def test_execute_batch_continue_on_error(self) -> None:
        """Test that batch continues on error by default."""
        registry = SkillRegistry()
        registry.register(FailingSkill)

        engine = PlaybookEngine(registry)
        executor = BatchExecutor(engine=engine)

        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[SkillStep(name="step1", skill="failing_skill", input={})],
        )

        inputs = [{"value": f"test{i}"} for i in range(3)]

        # Should complete all executions despite failures
        results = await executor.execute_batch(playbook, inputs, continue_on_error=True)

        assert results.total == 3
        assert results.failure_count == 3

    @pytest.mark.asyncio
    async def test_execute_batch_timing(self) -> None:
        """Test that batch execution tracks timing correctly."""
        registry = SkillRegistry()
        registry.register(DummySkill)

        engine = PlaybookEngine(registry)
        executor = BatchExecutor(engine=engine)

        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[SkillStep(name="step1", skill="dummy_skill", input={})],
        )

        inputs = [{"value": "test"}]

        results = await executor.execute_batch(playbook, inputs)

        assert results.total == 1
        assert results.results[0].duration_ms > 0  # Should have some duration
        assert results.avg_duration_ms > 0
        assert results.total_duration_ms > 0

    @pytest.mark.asyncio
    async def test_execute_batch_preserves_order(self) -> None:
        """Test that results preserve input order."""
        registry = SkillRegistry()
        registry.register(DummySkill)

        engine = PlaybookEngine(registry)
        executor = BatchExecutor(engine=engine)

        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[SkillStep(name="step1", skill="dummy_skill", input={})],
        )

        inputs = [{"value": i} for i in range(10)]

        results = await executor.execute_batch(playbook, inputs)

        # Check that indices match input order
        for i, result in enumerate(results.results):
            assert result.index == i
            assert result.input_context["value"] == i

    @pytest.mark.asyncio
    async def test_execute_batch_with_progress(self) -> None:
        """Test batch execution with progress tracking."""
        registry = SkillRegistry()
        registry.register(DummySkill)

        engine = PlaybookEngine(registry)
        executor = BatchExecutor(engine=engine, show_progress=True)

        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[SkillStep(name="step1", skill="dummy_skill", input={})],
        )

        inputs = [{"value": i} for i in range(3)]

        # Should print progress messages (we can't easily test console output)
        results = await executor.execute_batch(playbook, inputs)

        assert results.total == 3
        assert results.success_count == 3

    @pytest.mark.asyncio
    async def test_execute_batch_concurrency_limit(self) -> None:
        """Test that concurrency limit is respected."""
        registry = SkillRegistry()
        registry.register(DummySkill)

        engine = PlaybookEngine(registry)
        executor = BatchExecutor(engine=engine, max_concurrency=1)  # Sequential

        playbook = Playbook(
            metadata=PlaybookMetadata(name="test", version="1.0.0", description="Test"),
            steps=[SkillStep(name="step1", skill="dummy_skill", input={})],
        )

        inputs = [{"value": i} for i in range(5)]

        results = await executor.execute_batch(playbook, inputs)

        # With concurrency=1, should execute sequentially
        assert results.total == 5
        assert results.success_count == 5
