"""Unit tests for PlaybookVisualizer."""


from src.playbooks import (
    DecisionBranch,
    DecisionStep,
    Playbook,
    PlaybookMetadata,
    PlaybookVisualizer,
    SkillStep,
)


class TestPlaybookVisualizer:
    """Test suite for PlaybookVisualizer."""

    def test_visualizer_initialization(self) -> None:
        """Test visualizer can be initialized."""
        visualizer = PlaybookVisualizer()
        assert visualizer is not None

    def test_simple_skill_step(self) -> None:
        """Test visualization of a single skill step."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="test_playbook", version="1.0.0"),
            steps=[SkillStep(name="test_step", skill="test_skill", input={})],
        )

        visualizer = PlaybookVisualizer()
        mermaid = visualizer.to_mermaid(playbook)

        assert "flowchart TD" in mermaid
        assert "Start([Start])" in mermaid
        assert "End([End])" in mermaid
        assert "test_step[test_step]" in mermaid

    def test_decision_step_with_branches(self) -> None:
        """Test visualization of decision step with multiple branches."""
        playbook = Playbook(
            metadata=PlaybookMetadata(name="decision_test", version="1.0.0"),
            steps=[
                DecisionStep(
                    name="check_condition",
                    branches=[
                        DecisionBranch(
                            condition="value > 10",
                            steps=[
                                SkillStep(
                                    name="high_value", skill="processor", input={}
                                )
                            ],
                        ),
                    ],
                )
            ],
        )

        visualizer = PlaybookVisualizer()
        mermaid = visualizer.to_mermaid(playbook)

        assert "check_condition{check_condition}" in mermaid
