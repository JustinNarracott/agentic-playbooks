"""Tests for checkpoint management."""

import json
from pathlib import Path

import pytest

from src.playbooks.checkpoint import CheckpointManager
from src.playbooks.errors import CheckpointError
from src.playbooks.tracer import StepTrace


class TestCheckpointManager:
    """Test CheckpointManager."""

    @pytest.fixture
    def checkpoint_dir(self, tmp_path):
        """Create temporary checkpoint directory."""
        checkpoint_path = tmp_path / "checkpoints"
        return str(checkpoint_path)

    @pytest.fixture
    def manager(self, checkpoint_dir):
        """Create CheckpointManager instance."""
        return CheckpointManager(checkpoint_dir)

    def test_checkpoint_dir_created(self, manager):
        """Test that checkpoint directory is created."""
        assert Path(manager.checkpoint_dir).exists()
        assert Path(manager.checkpoint_dir).is_dir()

    def test_save_and_load_checkpoint(self, manager):
        """Test saving and loading a checkpoint."""
        execution_id = "test-123"
        playbook_name = "test_playbook"
        context_vars = {"input": "value", "result": 42}
        completed_steps = []

        # Save checkpoint
        manager.save_checkpoint(
            execution_id=execution_id,
            playbook_name=playbook_name,
            current_step=2,
            context_vars=context_vars,
            completed_steps=completed_steps,
        )

        # Load checkpoint
        checkpoint = manager.load_checkpoint(execution_id)

        assert checkpoint is not None
        assert checkpoint["execution_id"] == execution_id
        assert checkpoint["playbook_name"] == playbook_name
        assert checkpoint["current_step"] == 2
        assert checkpoint["context"] == context_vars
        assert "timestamp" in checkpoint

    def test_load_nonexistent_checkpoint(self, manager):
        """Test loading checkpoint that doesn't exist."""
        checkpoint = manager.load_checkpoint("nonexistent-id")
        assert checkpoint is None

    def test_delete_checkpoint(self, manager):
        """Test deleting a checkpoint."""
        execution_id = "delete-test"

        # Save checkpoint
        manager.save_checkpoint(
            execution_id=execution_id,
            playbook_name="test",
            current_step=0,
            context_vars={},
            completed_steps=[],
        )

        # Verify it exists
        assert manager.load_checkpoint(execution_id) is not None

        # Delete it
        result = manager.delete_checkpoint(execution_id)
        assert result is True

        # Verify it's gone
        assert manager.load_checkpoint(execution_id) is None

    def test_delete_nonexistent_checkpoint(self, manager):
        """Test deleting checkpoint that doesn't exist."""
        result = manager.delete_checkpoint("nonexistent")
        assert result is False

    def test_list_checkpoints(self, manager):
        """Test listing all checkpoints."""
        # Save multiple checkpoints
        manager.save_checkpoint("id-1", "test", 0, {}, [])
        manager.save_checkpoint("id-2", "test", 0, {}, [])
        manager.save_checkpoint("id-3", "test", 0, {}, [])

        # List checkpoints
        checkpoints = manager.list_checkpoints()

        assert len(checkpoints) == 3
        assert "id-1" in checkpoints
        assert "id-2" in checkpoints
        assert "id-3" in checkpoints

    def test_list_checkpoints_empty(self, manager):
        """Test listing checkpoints when none exist."""
        checkpoints = manager.list_checkpoints()
        assert checkpoints == []

    def test_checkpoint_contains_timestamp(self, manager):
        """Test that checkpoints include timestamp."""
        manager.save_checkpoint("test", "playbook", 0, {}, [])

        checkpoint = manager.load_checkpoint("test")
        assert "timestamp" in checkpoint
        assert checkpoint["timestamp"]  # Non-empty

    def test_save_checkpoint_with_step_traces(self, manager):
        """Test saving checkpoint with completed step traces."""
        from datetime import datetime

        step1 = StepTrace(
            step_name="step1", step_type="skill", started_at=datetime.utcnow()
        )
        step1.completed_at = datetime.utcnow()
        step1.duration_ms = 100

        step2 = StepTrace(
            step_name="step2", step_type="skill", started_at=datetime.utcnow()
        )
        step2.completed_at = datetime.utcnow()
        step2.error = "Test error"

        completed_steps = [step1, step2]

        manager.save_checkpoint(
            execution_id="with-steps",
            playbook_name="test",
            current_step=2,
            context_vars={},
            completed_steps=completed_steps,
        )

        checkpoint = manager.load_checkpoint("with-steps")

        assert len(checkpoint["completed_steps"]) == 2
        assert checkpoint["completed_steps"][0]["step_name"] == "step1"
        assert checkpoint["completed_steps"][1]["step_name"] == "step2"
        assert checkpoint["completed_steps"][1]["error"] == "Test error"

    def test_checkpoint_file_format(self, manager, checkpoint_dir):
        """Test that checkpoint files are valid JSON."""
        manager.save_checkpoint("format-test", "test", 0, {"key": "value"}, [])

        checkpoint_file = Path(checkpoint_dir) / "format-test.json"
        assert checkpoint_file.exists()

        # Load as JSON
        with open(checkpoint_file) as f:
            data = json.load(f)

        assert data["execution_id"] == "format-test"
        assert data["context"]["key"] == "value"

    def test_checkpoint_error_on_corrupted_file(self, manager, checkpoint_dir):
        """Test that loading corrupted checkpoint raises CheckpointError."""
        # Create a corrupted checkpoint file
        checkpoint_file = Path(checkpoint_dir) / "corrupted.json"
        checkpoint_file.write_text("{ invalid json")

        with pytest.raises(CheckpointError) as exc_info:
            manager.load_checkpoint("corrupted")

        assert exc_info.value.operation == "load"
        assert exc_info.value.execution_id == "corrupted"
