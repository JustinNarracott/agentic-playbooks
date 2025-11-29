"""PlaybookVisualizer - generates Mermaid flowchart diagrams from playbooks."""

from pathlib import Path
from typing import List, Set

from .models import DecisionStep, Playbook, SkillStep, Step


class PlaybookVisualizer:
    """
    Generate Mermaid flowchart diagrams from playbook definitions.

    This class converts playbook structures into Mermaid syntax for
    documentation, governance, and workflow visualization.

    Example:
        visualizer = PlaybookVisualizer()
        playbook = loader.load_from_file("playbooks/governance/ai_decision_audit.yaml")
        mermaid_code = visualizer.to_mermaid(playbook)
        print(mermaid_code)

        # Save to file
        visualizer.save_diagram(playbook, "workflow.md")
    """

    def __init__(self) -> None:
        """Initialize the PlaybookVisualizer."""
        self._node_counter = 0
        self._node_ids: Set[str] = set()

    def to_mermaid(
        self,
        playbook: Playbook,
        show_variables: bool = False,
        direction: str = "TD",
    ) -> str:
        """
        Generate Mermaid flowchart syntax from a playbook.

        Args:
            playbook: The playbook to visualize
            show_variables: Whether to show variable flow annotations
            direction: Flowchart direction (TD=top-down, LR=left-right)

        Returns:
            Mermaid flowchart syntax as string
        """
        self._node_counter = 0
        self._node_ids = set()

        lines: List[str] = []

        # Header
        lines.append(f"flowchart {direction}")

        # Add metadata as comment
        lines.append(
            f"    %% Playbook: {playbook.metadata.name} v{playbook.metadata.version}"
        )
        if playbook.metadata.description:
            lines.append(f"    %% {playbook.metadata.description}")
        lines.append("")

        # Start node
        start_id = "Start"
        lines.append(f"    {start_id}([Start])")

        # Process steps
        prev_id = start_id
        for i, step in enumerate(playbook.steps):
            step_ids = self._process_step(step, lines, show_variables)
            if step_ids:
                # Connect previous node to this step
                lines.append(f"    {prev_id} --> {step_ids[0]}")
                prev_id = step_ids[-1]  # Last node of this step becomes previous

        # End node
        end_id = "End"
        lines.append(f"    {prev_id} --> {end_id}")
        lines.append(f"    {end_id}([End])")

        return "\n".join(lines)

    def _process_step(
        self, step: Step, lines: List[str], show_variables: bool
    ) -> List[str]:
        """
        Process a step and add it to the diagram.

        Args:
            step: The step to process
            lines: List of Mermaid lines to append to
            show_variables: Whether to show variable annotations

        Returns:
            List of node IDs created for this step (first and last for connections)
        """
        if isinstance(step, SkillStep):
            return self._process_skill_step(step, lines, show_variables)
        elif isinstance(step, DecisionStep):
            return self._process_decision_step(step, lines, show_variables)
        else:
            return []

    def _process_skill_step(
        self, step: SkillStep, lines: List[str], show_variables: bool
    ) -> List[str]:
        """
        Process a skill step.

        Args:
            step: The skill step to process
            lines: List of Mermaid lines to append to
            show_variables: Whether to show variable annotations

        Returns:
            List with single node ID for this skill step
        """
        node_id = self._generate_node_id(step.name)

        # Create node label with skill name
        label = self._escape_label(step.name)
        if show_variables and step.output_var:
            label += f"\\n-> {step.output_var}"

        # Skill steps are rectangles
        lines.append(f"    {node_id}[{label}]")

        return [node_id]

    def _process_decision_step(
        self, step: DecisionStep, lines: List[str], show_variables: bool
    ) -> List[str]:
        """
        Process a decision step with branches.

        Args:
            step: The decision step to process
            lines: List of Mermaid lines to append to
            show_variables: Whether to show variable annotations

        Returns:
            List with decision node ID and merge node ID
        """
        decision_id = self._generate_node_id(step.name)
        merge_id = self._generate_node_id(f"{step.name}_merge")

        # Decision nodes are diamonds
        label = self._escape_label(step.name)
        lines.append(f"    {decision_id}{{{label}}}")

        # Process each branch
        for i, branch in enumerate(step.branches):
            # Shorten condition for display
            condition_label = self._shorten_condition(branch.condition)

            if branch.steps:
                # Branch has steps - create them
                branch_first_id = None
                branch_last_id = decision_id

                for branch_step in branch.steps:
                    step_ids = self._process_step(branch_step, lines, show_variables)
                    if step_ids:
                        if branch_first_id is None:
                            branch_first_id = step_ids[0]
                            # Connect decision to first step of branch
                            lines.append(
                                f"    {decision_id} -->|{condition_label}| {branch_first_id}"
                            )
                        else:
                            # Connect previous step to current
                            lines.append(f"    {branch_last_id} --> {step_ids[0]}")

                        branch_last_id = step_ids[-1]

                # Connect last step of branch to merge
                if branch_last_id != decision_id:
                    lines.append(f"    {branch_last_id} --> {merge_id}")
            else:
                # Empty branch - connect directly to merge
                lines.append(f"    {decision_id} -->|{condition_label}| {merge_id}")

        # Process default branch if present
        if step.default:
            default_first_id = None
            default_last_id = decision_id

            for default_step in step.default:
                step_ids = self._process_step(default_step, lines, show_variables)
                if step_ids:
                    if default_first_id is None:
                        default_first_id = step_ids[0]
                        # Connect decision to first step of default
                        lines.append(
                            f"    {decision_id} -->|default| {default_first_id}"
                        )
                    else:
                        # Connect previous step to current
                        lines.append(f"    {default_last_id} --> {step_ids[0]}")

                    default_last_id = step_ids[-1]

            # Connect last step of default to merge
            if default_last_id != decision_id:
                lines.append(f"    {default_last_id} --> {merge_id}")
        else:
            # No default branch - add direct connection
            lines.append(f"    {decision_id} -->|else| {merge_id}")

        # Merge node (invisible/small)
        lines.append(f"    {merge_id}(( ))")

        return [decision_id, merge_id]

    def _generate_node_id(self, name: str) -> str:
        """
        Generate a unique node ID from a step name.

        Args:
            name: Step name

        Returns:
            Unique node ID
        """
        # Sanitize name for Mermaid ID
        base_id = name.replace(" ", "_").replace("-", "_")
        base_id = "".join(c for c in base_id if c.isalnum() or c == "_")

        # Ensure uniqueness
        node_id = base_id
        counter = 1
        while node_id in self._node_ids:
            node_id = f"{base_id}_{counter}"
            counter += 1

        self._node_ids.add(node_id)
        return node_id

    def _escape_label(self, text: str) -> str:
        """
        Escape text for use in Mermaid labels.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        # Replace characters that need escaping in Mermaid
        text = text.replace('"', "'")
        text = text.replace("[", "(")
        text = text.replace("]", ")")
        return text

    def _shorten_condition(self, condition: str, max_len: int = 40) -> str:
        """
        Shorten a condition for display in diagram.

        Args:
            condition: Condition string
            max_len: Maximum length

        Returns:
            Shortened condition
        """
        condition = condition.strip()

        # Remove common verbose patterns
        condition = condition.replace(" == ", "=")
        condition = condition.replace(" != ", "`")
        condition = condition.replace(" and ", " & ")
        condition = condition.replace(" or ", " | ")

        if len(condition) > max_len:
            condition = condition[: max_len - 3] + "..."

        return self._escape_label(condition)

    def save_diagram(
        self,
        playbook: Playbook,
        output_path: str,
        show_variables: bool = False,
        direction: str = "TD",
    ) -> None:
        """
        Save Mermaid diagram to a file.

        Args:
            playbook: The playbook to visualize
            output_path: Path to output file (.md or .mmd)
            show_variables: Whether to show variable flow annotations
            direction: Flowchart direction (TD=top-down, LR=left-right)
        """
        mermaid_code = self.to_mermaid(playbook, show_variables, direction)

        path = Path(output_path)

        # Wrap in markdown code fence if .md file
        if path.suffix == ".md":
            content = f"# {playbook.metadata.name}\n\n"
            if playbook.metadata.description:
                content += f"{playbook.metadata.description}\n\n"
            content += f"```mermaid\n{mermaid_code}\n```\n"
        else:
            content = mermaid_code

        path.write_text(content, encoding="utf-8")


def main() -> None:
    """CLI entry point for playbook visualization."""
    import argparse
    import sys

    from .loader import PlaybookLoader

    parser = argparse.ArgumentParser(
        description="Generate Mermaid flowchart diagrams from playbooks"
    )
    parser.add_argument("playbook", help="Path to playbook YAML file")
    parser.add_argument(
        "-o", "--output", help="Output file path (.md or .mmd)", default=None
    )
    parser.add_argument(
        "--direction",
        choices=["TD", "LR"],
        default="TD",
        help="Flowchart direction (TD=top-down, LR=left-right)",
    )
    parser.add_argument(
        "--show-variables",
        action="store_true",
        help="Show variable flow annotations",
    )

    args = parser.parse_args()

    try:
        # Load playbook
        loader = PlaybookLoader()
        playbook = loader.load_from_file(args.playbook)

        # Generate diagram
        visualizer = PlaybookVisualizer()

        if args.output:
            visualizer.save_diagram(
                playbook,
                args.output,
                show_variables=args.show_variables,
                direction=args.direction,
            )
            print(f"Diagram saved to: {args.output}")
        else:
            mermaid = visualizer.to_mermaid(
                playbook,
                show_variables=args.show_variables,
                direction=args.direction,
            )
            print(mermaid)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
