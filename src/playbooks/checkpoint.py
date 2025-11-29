"""Checkpoint management for resumable playbook execution."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .errors import CheckpointError


class CheckpointManager:
    """
    Manages checkpoint save/restore for playbook executions.

    Allows playbooks to be resumed from the last successful step
    after a failure or interruption.
    """

    def __init__(self, checkpoint_dir: str = ".checkpoints"):
        """
        Initialize CheckpointManager.

        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        execution_id: str,
        playbook_name: str,
        current_step: int,
        context_vars: Dict[str, Any],
        completed_steps: list,
    ) -> None:
        """
        Save execution checkpoint.

        Args:
            execution_id: Unique execution identifier
            playbook_name: Name of the playbook being executed
            current_step: Index of the current step (0-based)
            context_vars: Current execution context variables
            completed_steps: List of completed step traces

        Raises:
            CheckpointError: If checkpoint save fails
        """
        try:
            checkpoint = {
                "execution_id": execution_id,
                "playbook_name": playbook_name,
                "current_step": current_step,
                "context": context_vars,
                "completed_steps": [
                    self._serialize_step(step) for step in completed_steps
                ],
                "timestamp": datetime.utcnow().isoformat(),
            }

            path = self.checkpoint_dir / f"{execution_id}.json"
            with open(path, "w") as f:
                json.dump(checkpoint, f, indent=2, default=str)

        except Exception as e:
            raise CheckpointError("save", execution_id, e) from e

    def load_checkpoint(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Load execution checkpoint.

        Args:
            execution_id: Unique execution identifier

        Returns:
            Checkpoint data dict or None if not found

        Raises:
            CheckpointError: If checkpoint load fails
        """
        try:
            path = self.checkpoint_dir / f"{execution_id}.json"

            if not path.exists():
                return None

            with open(path) as f:
                checkpoint: Dict[str, Any] = json.load(f)

            return checkpoint

        except FileNotFoundError:
            return None
        except Exception as e:
            raise CheckpointError("load", execution_id, e) from e

    def delete_checkpoint(self, execution_id: str) -> bool:
        """
        Delete checkpoint file.

        Args:
            execution_id: Unique execution identifier

        Returns:
            True if deleted, False if not found
        """
        path = self.checkpoint_dir / f"{execution_id}.json"

        if path.exists():
            path.unlink()
            return True

        return False

    def list_checkpoints(self) -> list[str]:
        """
        List all available checkpoint execution IDs.

        Returns:
            List of execution IDs with checkpoints
        """
        return [p.stem for p in self.checkpoint_dir.glob("*.json")]

    def _serialize_step(self, step: Any) -> Dict[str, Any]:
        """
        Serialize step trace for checkpoint storage.

        Args:
            step: StepTrace object

        Returns:
            Serialized step data
        """
        # Handle both StepTrace objects and dicts
        if hasattr(step, "to_dict"):
            result: Dict[str, Any] = step.to_dict()
            return result
        elif isinstance(step, dict):
            return step
        else:
            # Fallback: convert to dict manually
            fallback: Dict[str, Any] = {
                "step_name": getattr(step, "step_name", "unknown"),
                "step_type": getattr(step, "step_type", "unknown"),
                "started_at": getattr(
                    step, "started_at", datetime.utcnow()
                ).isoformat(),
                "completed_at": (
                    getattr(step, "completed_at", datetime.utcnow()).isoformat()
                    if hasattr(step, "completed_at") and step.completed_at
                    else None
                ),
                "error": getattr(step, "error", None),
            }
            return fallback
