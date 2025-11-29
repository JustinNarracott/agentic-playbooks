"""Integration test for AI Decision Audit playbook."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.governance import (
    DecisionContextExtractor,
    LeadershipQuestionsGenerator,
    RiskIdentifier,
)
from src.playbooks import PlaybookEngine, PlaybookLoader
from src.skills.registry import SkillRegistry


@pytest.fixture
def playbook_path() -> str:
    """Get path to the AI Decision Audit playbook."""
    return str(
        Path(__file__).parent.parent.parent
        / "playbooks"
        / "governance"
        / "ai_decision_audit.yaml"
    )


@pytest.fixture
def skill_registry() -> SkillRegistry:
    """Create a skill registry with governance skills."""
    registry = SkillRegistry()
    registry.register(DecisionContextExtractor)
    registry.register(RiskIdentifier)
    registry.register(LeadershipQuestionsGenerator)
    return registry


@pytest.fixture
def mock_openai_context_response() -> dict:
    """Mock response for decision context extraction."""
    return {
        "decision_summary": "Approved loan application for small business",
        "stakeholders": ["loan applicant", "bank", "credit bureau", "regulators"],
        "constraints": ["maximum loan amount $500k", "minimum credit score 680"],
        "data_sources": ["credit report", "income verification", "bank statements"],
        "risk_factors": ["high debt-to-income ratio", "new business venture"],
        "confidence_level": "high",
    }


@pytest.fixture
def mock_openai_risk_response() -> dict:
    """Mock response for risk identification."""
    return {
        "risks": [
            {
                "severity": "high",
                "description": "High debt-to-income ratio increases default risk",
            },
            {
                "severity": "medium",
                "description": "New business venture has uncertain revenue",
            },
            {"severity": "low", "description": "Limited credit history"},
        ],
        "overall_risk_level": "high",
        "recommended_actions": [
            "Require additional collateral",
            "Reduce loan amount",
            "Implement stricter monitoring",
        ],
    }


@pytest.fixture
def mock_openai_questions_response() -> dict:
    """Mock response for leadership questions."""
    return {
        "strategic_questions": [
            "Does this decision align with our risk appetite?",
            "What is the expected ROI on this loan?",
            "How does this fit our portfolio strategy?",
        ],
        "ethical_questions": [
            "Are we treating all applicants fairly?",
            "Could this decision create bias in future decisions?",
            "Do we have appropriate human oversight?",
        ],
        "operational_questions": [
            "What monitoring will we implement?",
            "Who is responsible for ongoing review?",
            "What are the escalation procedures?",
        ],
    }


@pytest.fixture
def mock_openai_client(
    mock_openai_context_response: dict,
    mock_openai_risk_response: dict,
    mock_openai_questions_response: dict,
) -> AsyncMock:
    """Create a mock OpenAI client that returns appropriate responses."""

    async def mock_create(**kwargs: dict) -> MagicMock:
        """Mock the create method based on the prompt content."""
        messages = kwargs.get("messages", [])
        user_content = messages[1]["content"] if len(messages) > 1 else ""

        # Determine which response to return based on content
        if "Decision Text:" in user_content:
            response_data = mock_openai_context_response
        elif (
            "Decision Context:" in user_content
            and "Analyze this decision" in user_content
        ):
            response_data = mock_openai_risk_response
        elif "Generate leadership review questions" in user_content:
            response_data = mock_openai_questions_response
        else:
            response_data = mock_openai_context_response

        import json

        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content=json.dumps(response_data)))
        ]
        return mock_completion

    mock_client = AsyncMock()
    mock_client.chat.completions.create = mock_create
    return mock_client


class TestAIDecisionAuditPlaybook:
    """Integration tests for AI Decision Audit playbook."""

    @pytest.mark.asyncio
    async def test_playbook_loads_successfully(self, playbook_path: str) -> None:
        """Test that the playbook YAML loads without errors."""
        loader = PlaybookLoader()
        playbook = loader.load_from_file(playbook_path)

        assert playbook.metadata.name == "ai_decision_audit"
        assert playbook.metadata.version == "1.0.0"
        assert len(playbook.steps) == 4  # 3 skills + 1 decision

    @pytest.mark.asyncio
    async def test_playbook_execution_end_to_end(
        self,
        playbook_path: str,
        skill_registry: SkillRegistry,
        mock_openai_client: AsyncMock,
    ) -> None:
        """Test complete execution of the playbook."""
        # Patch OpenAI client for all skills
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.decision_context_extractor.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
            patch(
                "src.modules.governance.skills.risk_identifier.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
        ):
            # Load playbook
            loader = PlaybookLoader()
            playbook = loader.load_from_file(playbook_path)

            # Execute playbook
            engine = PlaybookEngine(skill_registry)
            trace = await engine.execute(
                playbook,
                initial_context={
                    "decision_text": "We approved a $400k loan for a startup business..."
                },
            )

            # Verify execution succeeded
            assert trace.success is True
            assert trace.error is None

            # Verify all steps executed
            assert len(trace.steps) == 4

            # Verify context extraction step
            assert trace.steps[0].step_name == "extract_decision_context"
            assert trace.steps[0].step_type == "skill"
            assert trace.steps[0].error is None

            # Verify risk analysis step
            assert trace.steps[1].step_name == "analyze_risks"
            assert trace.steps[1].step_type == "skill"
            assert trace.steps[1].error is None

            # Verify leadership questions step
            assert trace.steps[2].step_name == "generate_leadership_questions"
            assert trace.steps[2].step_type == "skill"
            assert trace.steps[2].error is None

            # Verify decision step
            assert trace.steps[3].step_name == "assess_risk_level"
            assert trace.steps[3].step_type == "decision"

            # Verify final context contains outputs
            assert "context_extraction" in trace.final_context
            assert "risk_analysis" in trace.final_context
            assert "leadership_review" in trace.final_context

            # Verify context extraction output
            context = trace.final_context["context_extraction"]["context"]
            assert (
                context["decision_summary"]
                == "Approved loan application for small business"
            )
            assert "loan applicant" in context["stakeholders"]

            # Verify risk analysis output
            risk_analysis = trace.final_context["risk_analysis"]["analysis"]
            assert risk_analysis["overall_risk_level"] == "high"
            assert len(risk_analysis["risks"]) > 0

            # Verify leadership questions output
            questions = trace.final_context["leadership_review"]["questions"]
            assert len(questions["strategic_questions"]) > 0
            assert len(questions["ethical_questions"]) > 0
            assert len(questions["operational_questions"]) > 0

    @pytest.mark.asyncio
    async def test_playbook_high_risk_escalation(
        self,
        playbook_path: str,
        skill_registry: SkillRegistry,
        mock_openai_client: AsyncMock,
    ) -> None:
        """Test that high risk decisions trigger escalation."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.decision_context_extractor.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
            patch(
                "src.modules.governance.skills.risk_identifier.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
        ):
            # Load and execute playbook
            loader = PlaybookLoader()
            playbook = loader.load_from_file(playbook_path)
            engine = PlaybookEngine(skill_registry)
            trace = await engine.execute(
                playbook,
                initial_context={"decision_text": "High risk loan decision..."},
            )

            # Verify decision step executed the high risk branch
            decision_step = trace.steps[3]
            assert decision_step.step_name == "assess_risk_level"
            assert decision_step.decision_taken is not None
            assert "branch_0" in decision_step.decision_taken

            # Verify escalation flag was created
            assert "escalation_flag" in trace.final_context
            assert len(decision_step.nested_steps) == 1
            assert (
                decision_step.nested_steps[0].step_name == "flag_for_immediate_review"
            )

    @pytest.mark.asyncio
    async def test_playbook_traces_all_steps(
        self,
        playbook_path: str,
        skill_registry: SkillRegistry,
        mock_openai_client: AsyncMock,
    ) -> None:
        """Test that all steps are properly traced."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.decision_context_extractor.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
            patch(
                "src.modules.governance.skills.risk_identifier.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
        ):
            # Load and execute playbook
            loader = PlaybookLoader()
            playbook = loader.load_from_file(playbook_path)
            engine = PlaybookEngine(skill_registry)
            trace = await engine.execute(
                playbook,
                initial_context={"decision_text": "Test decision..."},
            )

            # Verify all steps have timing information
            for step in trace.steps:
                assert step.started_at is not None
                assert step.completed_at is not None
                assert step.duration_ms is not None
                assert step.duration_ms >= 0

            # Verify skill steps have skill traces
            for step in trace.steps[:3]:  # First 3 are skill steps
                assert step.skill_trace is not None
                assert step.skill_trace.reasoning is not None

            # Export trace to verify it's serializable
            trace_dict = trace.to_dict()
            assert trace_dict["playbook_name"] == "ai_decision_audit"
            assert len(trace_dict["steps"]) == 4
