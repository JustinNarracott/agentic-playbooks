"""Unit tests for LeadershipQuestionsGenerator skill."""

import json
import os
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.governance.skills.leadership_questions_generator import (
    LeadershipQuestions,
    LeadershipQuestionsGenerator,
)


@pytest.fixture
def mock_decision_context() -> Dict[str, Any]:
    """Create a mock decision context."""
    return {
        "decision_summary": "Approved $400k loan for startup business",
        "stakeholders": ["loan applicant", "bank", "investors"],
        "constraints": ["maximum loan amount $500k", "minimum credit score 680"],
        "data_sources": ["credit report", "business plan", "financial statements"],
        "risk_factors": ["high debt-to-income ratio", "new business venture"],
    }


@pytest.fixture
def mock_risk_analysis() -> Dict[str, Any]:
    """Create a mock risk analysis."""
    return {
        "risks": [
            {
                "severity": "high",
                "description": "High debt-to-income ratio increases default risk",
                "category": "business",
                "likelihood": "medium",
            },
            {
                "severity": "medium",
                "description": "New business venture has uncertain revenue",
                "category": "business",
                "likelihood": "high",
            },
        ],
        "overall_risk_level": "high",
        "recommended_actions": [
            "Require additional collateral",
            "Reduce loan amount",
        ],
        "confidence_level": "high",
    }


@pytest.fixture
def mock_openai_response() -> Dict[str, Any]:
    """Create a mock OpenAI API response."""
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
def mock_openai_client(mock_openai_response: Dict[str, Any]) -> AsyncMock:
    """Create a mock OpenAI client."""
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content=json.dumps(mock_openai_response)))
    ]

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    return mock_client


class TestLeadershipQuestions:
    """Test suite for LeadershipQuestions Pydantic model."""

    def test_create_leadership_questions(self) -> None:
        """Test creating a LeadershipQuestions instance."""
        questions = LeadershipQuestions(
            strategic_questions=["Question 1", "Question 2"],
            ethical_questions=["Question 3"],
            operational_questions=["Question 4", "Question 5"],
        )

        assert len(questions.strategic_questions) == 2
        assert len(questions.ethical_questions) == 1
        assert len(questions.operational_questions) == 2

    def test_leadership_questions_defaults(self) -> None:
        """Test LeadershipQuestions with default values."""
        questions = LeadershipQuestions()

        assert questions.strategic_questions == []
        assert questions.ethical_questions == []
        assert questions.operational_questions == []

    def test_leadership_questions_serialization(self) -> None:
        """Test serializing LeadershipQuestions to dict."""
        questions = LeadershipQuestions(
            strategic_questions=["Strategic Q1"],
            ethical_questions=["Ethical Q1"],
            operational_questions=["Operational Q1"],
        )

        data = questions.model_dump()
        assert "strategic_questions" in data
        assert "ethical_questions" in data
        assert "operational_questions" in data
        assert data["strategic_questions"] == ["Strategic Q1"]


class TestLeadershipQuestionsGenerator:
    """Test suite for LeadershipQuestionsGenerator skill."""

    def test_skill_metadata(self) -> None:
        """Test skill has correct metadata."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = LeadershipQuestionsGenerator()

            assert skill.name == "leadership_questions_generator"
            assert skill.version == "1.0.0"
            assert (
                skill.description
                == "Generate strategic leadership review questions for AI decisions"
            )

    def test_initialization_requires_api_key(self) -> None:
        """Test that initialization requires OPENAI_API_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                LeadershipQuestionsGenerator()

    def test_initialization_with_api_key(self) -> None:
        """Test successful initialization with API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = LeadershipQuestionsGenerator()
            assert skill.client is not None
            assert skill.model == "gpt-4o-mini"

    def test_initialization_with_custom_model(self) -> None:
        """Test initialization with custom model."""
        with patch.dict(
            os.environ, {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "gpt-4"}
        ):
            skill = LeadershipQuestionsGenerator()
            assert skill.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_execute_basic(
        self,
        mock_decision_context: Dict[str, Any],
        mock_openai_client: AsyncMock,
    ) -> None:
        """Test basic execution with decision context only."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
        ):
            skill = LeadershipQuestionsGenerator()
            output, trace = await skill.run({"decision_context": mock_decision_context})

            assert "questions" in output
            assert "raw_response" in output
            assert "strategic_questions" in output["questions"]
            assert "ethical_questions" in output["questions"]
            assert "operational_questions" in output["questions"]
            assert len(output["questions"]["strategic_questions"]) == 3
            assert len(output["questions"]["ethical_questions"]) == 3
            assert len(output["questions"]["operational_questions"]) == 3

    @pytest.mark.asyncio
    async def test_execute_with_risk_analysis(
        self,
        mock_decision_context: Dict[str, Any],
        mock_risk_analysis: Dict[str, Any],
        mock_openai_client: AsyncMock,
    ) -> None:
        """Test execution with both decision context and risk analysis."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
        ):
            skill = LeadershipQuestionsGenerator()
            output, trace = await skill.run(
                {
                    "decision_context": mock_decision_context,
                    "risk_analysis": mock_risk_analysis,
                }
            )

            assert "questions" in output
            # Verify OpenAI was called with context including risk analysis
            mock_openai_client.chat.completions.create.assert_called_once()
            call_args = mock_openai_client.chat.completions.create.call_args
            user_content = call_args.kwargs["messages"][1]["content"]
            assert "Overall Risk Level: high" in user_content
            assert "High/Critical Risks:" in user_content

    @pytest.mark.asyncio
    async def test_execute_missing_decision_context(
        self, mock_openai_client: AsyncMock
    ) -> None:
        """Test that missing decision_context raises ValueError."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
        ):
            skill = LeadershipQuestionsGenerator()
            with pytest.raises(ValueError, match="decision_context is required"):
                await skill.run({})

    @pytest.mark.asyncio
    async def test_execute_empty_decision_context(
        self, mock_openai_client: AsyncMock
    ) -> None:
        """Test execution with empty decision context dict."""
        # Empty dict is truthy, so this should work but use defaults
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
        ):
            skill = LeadershipQuestionsGenerator()
            output, _ = await skill.run(
                {"decision_context": {"decision_summary": "Test"}}
            )

            assert "questions" in output
            # Verify it handles missing optional fields gracefully
            call_args = mock_openai_client.chat.completions.create.call_args
            user_content = call_args.kwargs["messages"][1]["content"]
            assert "Decision Summary: Test" in user_content

    @pytest.mark.asyncio
    async def test_execute_invalid_json_response(
        self, mock_decision_context: Dict[str, Any]
    ) -> None:
        """Test handling of invalid JSON response from OpenAI."""
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="Invalid JSON"))]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_client,
            ),
        ):
            skill = LeadershipQuestionsGenerator()
            with pytest.raises(ValueError, match="Failed to parse LLM response"):
                await skill.run({"decision_context": mock_decision_context})

    @pytest.mark.asyncio
    async def test_execute_with_partial_response(
        self, mock_decision_context: Dict[str, Any]
    ) -> None:
        """Test handling of response with only some fields (others use defaults)."""
        # Since fields have default_factory=list, missing fields will use empty lists
        partial_response = {
            "strategic_questions": ["Q1"],
            "ethical_questions": [],
            "operational_questions": [],
        }

        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content=json.dumps(partial_response)))
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_client,
            ),
        ):
            skill = LeadershipQuestionsGenerator()
            output, _ = await skill.run({"decision_context": mock_decision_context})

            assert output["questions"]["strategic_questions"] == ["Q1"]
            assert output["questions"]["ethical_questions"] == []
            assert output["questions"]["operational_questions"] == []

    @pytest.mark.asyncio
    async def test_execute_sets_reasoning_trace(
        self,
        mock_decision_context: Dict[str, Any],
        mock_openai_client: AsyncMock,
    ) -> None:
        """Test that execution sets reasoning in skill trace."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
        ):
            skill = LeadershipQuestionsGenerator()
            _, trace = await skill.run({"decision_context": mock_decision_context})

            assert trace is not None
            assert trace.reasoning is not None
            assert "Generated 9 leadership review questions" in trace.reasoning
            assert "Strategic: 3" in trace.reasoning
            assert "Ethical: 3" in trace.reasoning
            assert "Operational: 3" in trace.reasoning
            assert "gpt-4o-mini" in trace.reasoning

    @pytest.mark.asyncio
    async def test_execute_includes_risk_factors_in_context(
        self, mock_decision_context: Dict[str, Any], mock_openai_client: AsyncMock
    ) -> None:
        """Test that risk factors from decision context are included in prompt."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
        ):
            skill = LeadershipQuestionsGenerator()
            await skill.run({"decision_context": mock_decision_context})

            call_args = mock_openai_client.chat.completions.create.call_args
            user_content = call_args.kwargs["messages"][1]["content"]
            assert "Risk Factors:" in user_content
            assert "high debt-to-income ratio" in user_content
            assert "new business venture" in user_content

    @pytest.mark.asyncio
    async def test_execute_formats_high_severity_risks(
        self,
        mock_decision_context: Dict[str, Any],
        mock_risk_analysis: Dict[str, Any],
        mock_openai_client: AsyncMock,
    ) -> None:
        """Test that high/critical severity risks are highlighted in prompt."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
        ):
            skill = LeadershipQuestionsGenerator()
            await skill.run(
                {
                    "decision_context": mock_decision_context,
                    "risk_analysis": mock_risk_analysis,
                }
            )

            call_args = mock_openai_client.chat.completions.create.call_args
            user_content = call_args.kwargs["messages"][1]["content"]
            assert "High/Critical Risks:" in user_content
            assert "[high]" in user_content
            assert "High debt-to-income ratio increases default risk" in user_content

    @pytest.mark.asyncio
    async def test_execute_uses_correct_temperature(
        self, mock_decision_context: Dict[str, Any], mock_openai_client: AsyncMock
    ) -> None:
        """Test that execution uses temperature 0.3 for varied questions."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch(
                "src.modules.governance.skills.leadership_questions_generator.AsyncOpenAI",
                return_value=mock_openai_client,
            ),
        ):
            skill = LeadershipQuestionsGenerator()
            await skill.run({"decision_context": mock_decision_context})

            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args.kwargs["temperature"] == 0.3
            assert call_args.kwargs["response_format"] == {"type": "json_object"}
