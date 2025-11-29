"""BatchExecutor - parallel playbook execution with progress tracking."""

import asyncio
import csv
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .engine import PlaybookEngine
from .models import Playbook
from .tracer import ExecutionTrace


@dataclass
class BatchResult:
    """Result of a single playbook execution in a batch."""

    index: int
    input_context: Dict[str, Any]
    trace: Optional[ExecutionTrace] = None
    error: Optional[str] = None
    duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.trace is not None and self.trace.success

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "index": self.index,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "input_context": self.input_context,
            "trace": self.trace.to_dict() if self.trace else None,
        }


@dataclass
class BatchResults:
    """Aggregated results from batch execution."""

    results: List[BatchResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    @property
    def total(self) -> int:
        """Total number of executions."""
        return len(self.results)

    @property
    def success_count(self) -> int:
        """Number of successful executions."""
        return sum(1 for r in self.results if r.success)

    @property
    def failure_count(self) -> int:
        """Number of failed executions."""
        return sum(1 for r in self.results if not r.success)

    @property
    def avg_duration_ms(self) -> float:
        """Average execution duration in milliseconds."""
        if not self.results:
            return 0.0
        return sum(r.duration_ms for r in self.results) / len(self.results)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total": self.total,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "avg_duration_ms": self.avg_duration_ms,
            "total_duration_ms": self.total_duration_ms,
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, output_path: str, indent: int = 2) -> None:
        """
        Export results to JSON file.

        Args:
            output_path: Path to output JSON file
            indent: JSON indentation level (default: 2)
        """
        path = Path(output_path)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=indent)

    def to_csv(self, output_path: str) -> None:
        """
        Export results summary to CSV file.

        Args:
            output_path: Path to output CSV file
        """
        path = Path(output_path)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["index", "success", "duration_ms", "error"],
            )
            writer.writeheader()
            for result in self.results:
                writer.writerow(
                    {
                        "index": result.index,
                        "success": result.success,
                        "duration_ms": result.duration_ms,
                        "error": result.error or "",
                    }
                )


class BatchExecutor:
    """
    Execute playbooks in batch with parallel execution and progress tracking.

    Example:
        executor = BatchExecutor(max_concurrency=5)
        inputs = [
            {"decision_text": "Approved loan..."},
            {"decision_text": "Rejected loan..."},
        ]
        results = await executor.execute_batch(playbook, inputs)
        print(f"Success: {results.success_count}/{results.total}")
        results.to_json("results.json")
    """

    def __init__(
        self,
        engine: Optional[PlaybookEngine] = None,
        max_concurrency: int = 5,
        show_progress: bool = False,
    ) -> None:
        """
        Initialize batch executor.

        Args:
            engine: PlaybookEngine to use (creates new one if None)
            max_concurrency: Maximum number of parallel executions
            show_progress: Whether to show progress updates
        """
        self.engine = engine or PlaybookEngine()
        self.max_concurrency = max_concurrency
        self.show_progress = show_progress
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def execute_batch(
        self,
        playbook: Playbook,
        inputs: List[Dict[str, Any]],
        continue_on_error: bool = True,
    ) -> BatchResults:
        """
        Execute playbook with multiple input contexts in parallel.

        Args:
            playbook: The playbook to execute
            inputs: List of input contexts
            continue_on_error: Continue processing if individual executions fail

        Returns:
            BatchResults with aggregated execution results
        """
        if not inputs:
            return BatchResults(results=[], total_duration_ms=0.0)

        # Create semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

        # Show initial progress
        if self.show_progress:
            print(f"Processing {len(inputs)} inputs...")

        # Track total time
        start_time = time.perf_counter()

        # Create tasks for all inputs
        tasks = [
            self._execute_single(playbook, i, input_ctx, continue_on_error)
            for i, input_ctx in enumerate(inputs)
        ]

        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate total duration
        total_duration_ms = (time.perf_counter() - start_time) * 1000

        # Handle any exceptions from gather
        batch_results: List[BatchResult] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                batch_results.append(
                    BatchResult(
                        index=i,
                        input_context=inputs[i],
                        error=str(result),
                        duration_ms=0.0,
                    )
                )
            elif isinstance(result, BatchResult):
                batch_results.append(result)

        # Show final progress
        if self.show_progress:
            success_count = sum(1 for r in batch_results if r.success)
            failure_count = len(batch_results) - success_count
            avg_duration = total_duration_ms / len(batch_results)
            print(
                f"Completed: Success: {success_count}, Failed: {failure_count}, "
                f"Avg: {avg_duration:.0f}ms"
            )

        return BatchResults(results=batch_results, total_duration_ms=total_duration_ms)

    async def _execute_single(
        self,
        playbook: Playbook,
        index: int,
        input_context: Dict[str, Any],
        continue_on_error: bool,
    ) -> BatchResult:
        """
        Execute playbook for a single input.

        Args:
            playbook: The playbook to execute
            index: Index of this input in the batch
            input_context: Input context for execution
            continue_on_error: Whether to continue on error

        Returns:
            BatchResult for this execution
        """
        async with self._semaphore:  # type: ignore
            start_time = time.perf_counter()

            try:
                trace = await self.engine.execute(playbook, input_context)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Show progress update
                if self.show_progress:
                    status = "✓" if trace.success else "✗"
                    print(f"  [{index + 1}] {status} ({duration_ms:.0f}ms)")

                return BatchResult(
                    index=index,
                    input_context=input_context,
                    trace=trace,
                    error=trace.error if not trace.success else None,
                    duration_ms=duration_ms,
                )

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Show progress update
                if self.show_progress:
                    print(f"  [{index + 1}] ✗ Error: {e}")

                if not continue_on_error:
                    raise

                return BatchResult(
                    index=index,
                    input_context=input_context,
                    error=str(e),
                    duration_ms=duration_ms,
                )


def main() -> None:
    """CLI entry point for batch execution."""
    import argparse
    import sys

    from .loader import PlaybookLoader

    parser = argparse.ArgumentParser(
        description="Execute playbooks in batch with multiple inputs"
    )
    parser.add_argument("playbook", help="Path to playbook YAML file")
    parser.add_argument("inputs", help="Path to JSON file with input contexts")
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=5,
        help="Maximum parallel executions (default: 5)",
    )
    parser.add_argument(
        "--output",
        help="Output file path for results (.json or .csv)",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show progress updates",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop batch execution on first error",
    )

    args = parser.parse_args()

    async def run() -> None:
        try:
            # Load playbook
            loader = PlaybookLoader()
            playbook = loader.load_from_file(args.playbook)

            # Load inputs
            inputs_path = Path(args.inputs)
            with inputs_path.open("r", encoding="utf-8") as f:
                inputs = json.load(f)

            if not isinstance(inputs, list):
                print("Error: inputs file must contain a JSON array", file=sys.stderr)
                sys.exit(1)

            # Execute batch
            executor = BatchExecutor(
                max_concurrency=args.max_concurrency,
                show_progress=args.progress,
            )
            results = await executor.execute_batch(
                playbook,
                inputs,
                continue_on_error=not args.stop_on_error,
            )

            # Print summary
            print("\nBatch Execution Summary:")
            print(f"  Total: {results.total}")
            print(f"  Success: {results.success_count}")
            print(f"  Failed: {results.failure_count}")
            print(f"  Avg Duration: {results.avg_duration_ms:.0f}ms")
            print(f"  Total Duration: {results.total_duration_ms:.0f}ms")

            # Export results if requested
            if args.output:
                output_path = Path(args.output)
                if output_path.suffix == ".csv":
                    results.to_csv(str(output_path))
                else:
                    results.to_json(str(output_path))
                print(f"\nResults saved to: {args.output}")

            # Exit with error code if any failures
            sys.exit(0 if results.failure_count == 0 else 1)

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Run the async function
    asyncio.run(run())


if __name__ == "__main__":
    main()
