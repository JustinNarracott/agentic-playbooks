"""Unit tests for DecisionContextExtractor skill."""

import json
import os
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.governance.skills.decision_context_extractor import (
    DecisionContext,
    DecisionContextExtractor,
)


@pytest.fixture
def mock_openai_response() -> Dict[str, Any]:
    """Create a mock OpenAI API response."""
    return {
        "decision_summary": "Approved loan application based on credit score and income",
        "stakeholders": ["loan applicant", "bank", "credit bureau"],
        "constraints": ["maximum loan amount $500k", "minimum credit score 680"],
        "data_sources": ["credit report", "income verification", "bank statements"],
        "risk_factors": ["high debt-to-income ratio", "recent job change"],
        "confidence_level": "high",
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


class TestDecisionContext:
    """Test suite for DecisionContext Pydantic model."""

    def test_create_decision_context(self) -> None:
        """Test creating a DecisionContext instance."""
        context = DecisionContext(
            decision_summary="Test decision",
            stakeholders=["user1", "user2"],
            constraints=["budget limit"],
            data_sources=["database"],
        )

        assert context.decision_summary == "Test decision"
        assert context.stakeholders == ["user1", "user2"]
        assert context.constraints == ["budget limit"]
        assert context.data_sources == ["database"]
        assert context.risk_factors is None
        assert context.confidence_level is None

    def test_decision_context_defaults(self) -> None:
        """Test DecisionContext with default values."""
        context = DecisionContext(decision_summary="Minimal decision")

        assert context.decision_summary == "Minimal decision"
        assert context.stakeholders == []
        assert context.constraints == []
        assert context.data_sources == []
        assert context.risk_factors is None
        assert context.confidence_level is None

    def test_decision_context_with_optional_fields(self) -> None:
        """Test DecisionContext with optional fields."""
        context = DecisionContext(
            decision_summary="Full decision",
            stakeholders=["user"],
            constraints=[],
            data_sources=["api"],
            risk_factors=["compliance risk"],
            confidence_level="medium",
        )

        assert context.risk_factors == ["compliance risk"]
        assert context.confidence_level == "medium"


class TestDecisionContextExtractor:
    """Test suite for DecisionContextExtractor skill."""

    def test_skill_metadata(self) -> None:
        """Test skill has correct metadata."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = DecisionContextExtractor()

            assert skill.name == "decision_context_extractor"
            assert skill.version == "1.0.0"
            assert (
                skill.description == "Extract governance context from AI decision text"
            )

    def test_init_requires_api_key(self) -> None:
        """Test that initialization requires OPENAI_API_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable"):
                DecisionContextExtractor()

    def test_init_with_api_key(self) -> None:
        """Test initialization with API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = DecisionContextExtractor()
            assert skill.client is not None
            assert skill.model == "gpt-4o-mini"  # Default model

    def test_init_with_custom_model(self) -> None:
        """Test initialization with custom model."""
        with patch.dict(
            os.environ, {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "gpt-4"}
        ):
            skill = DecisionContextExtractor()
            assert skill.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_execute_basic(
        self, mock_openai_client: AsyncMock, mock_openai_response: Dict[str, Any]
    ) -> None:
        """Test basic execution with decision text."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = DecisionContextExtractor()
            skill.client = mock_openai_client

            decision_text = "We approved the loan application..."
            result = await skill.execute({"decision_text": decision_text})

            # Verify OpenAI was called
            mock_openai_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
            assert call_kwargs["model"] == "gpt-4o-mini"
            assert call_kwargs["temperature"] == 0.1
            assert call_kwargs["response_format"] == {"type": "json_object"}

            # Verify messages
            messages = call_kwargs["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert "governance analyst" in messages[0]["content"].lower()
            assert messages[1]["role"] == "user"
            assert decision_text in messages[1]["content"]

            # Verify output
            assert "context" in result
            assert "raw_response" in result
            assert (
                result["context"]["decision_summary"]
                == mock_openai_response["decision_summary"]
            )
            assert (
                result["context"]["stakeholders"]
                == mock_openai_response["stakeholders"]
            )

    @pytest.mark.asyncio
    async def test_execute_with_additional_context(
        self, mock_openai_client: AsyncMock
    ) -> None:
        """Test execution with additional context."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = DecisionContextExtractor()
            skill.client = mock_openai_client

            await skill.execute(
                {
                    "decision_text": "Loan approved",
                    "additional_context": "Customer has been with bank for 10 years",
                }
            )

            # Verify additional context was included in prompt
            call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
            user_message = call_kwargs["messages"][1]["content"]
            assert "Additional Context" in user_message
            assert "Customer has been with bank for 10 years" in user_message

    @pytest.mark.asyncio
    async def test_execute_missing_decision_text(
        self, mock_openai_client: AsyncMock
    ) -> None:
        """Test error when decision_text is missing."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = DecisionContextExtractor()
            skill.client = mock_openai_client

            with pytest.raises(ValueError, match="decision_text is required"):
                await skill.execute({})

    @pytest.mark.asyncio
    async def test_execute_empty_decision_text(
        self, mock_openai_client: AsyncMock
    ) -> None:
        """Test error when decision_text is empty."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = DecisionContextExtractor()
            skill.client = mock_openai_client

            with pytest.raises(ValueError, match="decision_text is required"):
                await skill.execute({"decision_text": ""})

    @pytest.mark.asyncio
    async def test_execute_invalid_json_response(
        self, mock_openai_client: AsyncMock
    ) -> None:
        """Test error handling for invalid JSON response."""
        # Mock invalid JSON response
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="Not valid JSON"))
        ]
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = DecisionContextExtractor()
            skill.client = mock_openai_client

            with pytest.raises(ValueError, match="Failed to parse LLM response"):
                await skill.execute({"decision_text": "Test decision"})

    @pytest.mark.asyncio
    async def test_execute_missing_required_fields(
        self, mock_openai_client: AsyncMock
    ) -> None:
        """Test error handling when LLM response is missing required fields."""
        # Mock response missing required field
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "stakeholders": ["user1"],
                            "constraints": [],
                            # Missing decision_summary
                        }
                    )
                )
            )
        ]
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = DecisionContextExtractor()
            skill.client = mock_openai_client

            with pytest.raises(ValueError, match="Failed to parse LLM response"):
                await skill.execute({"decision_text": "Test decision"})

    @pytest.mark.asyncio
    async def test_execute_sets_reasoning_trace(
        self, mock_openai_client: AsyncMock, mock_openai_response: Dict[str, Any]
    ) -> None:
        """Test that execution sets reasoning in trace."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = DecisionContextExtractor()
            skill.client = mock_openai_client

            # Execute through run() to get trace
            output, trace = await skill.run({"decision_text": "Test decision"})

            assert trace.reasoning is not None
            assert "gpt-4o-mini" in trace.reasoning
            assert "Confidence: high" in trace.reasoning

    @pytest.mark.asyncio
    async def test_execute_all_context_fields(
        self, mock_openai_client: AsyncMock, mock_openai_response: Dict[str, Any]
    ) -> None:
        """Test that all context fields are properly extracted."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = DecisionContextExtractor()
            skill.client = mock_openai_client

            result = await skill.execute({"decision_text": "Test decision"})

            context = result["context"]
            assert (
                context["decision_summary"] == mock_openai_response["decision_summary"]
            )
            assert context["stakeholders"] == mock_openai_response["stakeholders"]
            assert context["constraints"] == mock_openai_response["constraints"]
            assert context["data_sources"] == mock_openai_response["data_sources"]
            assert context["risk_factors"] == mock_openai_response["risk_factors"]
            assert (
                context["confidence_level"] == mock_openai_response["confidence_level"]
            )

    @pytest.mark.asyncio
    async def test_execute_minimal_response(
        self, mock_openai_client: AsyncMock
    ) -> None:
        """Test execution with minimal valid response."""
        # Mock minimal response (only required fields)
        minimal_response = {
            "decision_summary": "Simple decision",
            "stakeholders": [],
            "constraints": [],
            "data_sources": [],
        }

        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content=json.dumps(minimal_response)))
        ]
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            skill = DecisionContextExtractor()
            skill.client = mock_openai_client

            result = await skill.execute({"decision_text": "Test decision"})

            context = result["context"]
            assert context["decision_summary"] == "Simple decision"
            assert context["stakeholders"] == []
            assert context["constraints"] == []
            assert context["data_sources"] == []
            assert context["risk_factors"] is None
            assert context["confidence_level"] is None
