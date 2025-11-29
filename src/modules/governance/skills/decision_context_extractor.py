"""DecisionContextExtractor - extracts governance context from AI decisions."""

import json
import os
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from ....skills.base import Skill


class DecisionContext(BaseModel):
    """Structured representation of decision context."""

    decision_summary: str = Field(description="Brief summary of the decision")
    stakeholders: List[str] = Field(
        default_factory=list, description="Identified stakeholders affected by decision"
    )
    constraints: List[str] = Field(
        default_factory=list, description="Constraints or limitations identified"
    )
    data_sources: List[str] = Field(
        default_factory=list, description="Data sources used in the decision"
    )
    risk_factors: Optional[List[str]] = Field(
        default=None, description="Potential risks or concerns"
    )
    confidence_level: Optional[str] = Field(
        default=None, description="Confidence level in the extraction"
    )


class DecisionContextExtractor(Skill):
    """
    Extract governance context from AI decision text.

    This skill uses OpenAI to analyze decision text and extract:
    - Key decision elements and summary
    - Stakeholders affected
    - Constraints and limitations
    - Data sources used
    - Risk factors

    Example:
        extractor = DecisionContextExtractor()
        output = await extractor.execute({
            "decision_text": "We decided to approve the loan application for..."
        })
        # Returns: {
        #   "context": {
        #     "decision_summary": "...",
        #     "stakeholders": ["applicant", "bank", ...],
        #     ...
        #   }
        # }
    """

    name = "decision_context_extractor"
    version = "1.0.0"
    description = "Extract governance context from AI decision text"

    def __init__(self) -> None:
        super().__init__()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable must be set to use DecisionContextExtractor"
            )
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract decision context from text.

        Args:
            input: Dictionary with:
                - decision_text (str): The decision text to analyze
                - additional_context (str, optional): Additional context for analysis

        Returns:
            Dictionary with:
                - context (dict): Extracted decision context
                - raw_response (str): Raw LLM response for auditing

        Raises:
            ValueError: If decision_text is missing
        """
        decision_text = input.get("decision_text")
        if not decision_text:
            raise ValueError("decision_text is required")

        additional_context = input.get("additional_context", "")

        # Build prompt for extraction
        system_prompt = """You are a governance analyst extracting structured context from AI decisions.
Extract the following information from the decision text:
1. A brief summary of the decision
2. All stakeholders mentioned or implied (people, organizations, systems)
3. Any constraints or limitations mentioned
4. Data sources referenced or used
5. Potential risk factors or concerns
6. Your confidence level in this extraction (high/medium/low)

Return your analysis as a JSON object with these exact keys:
- decision_summary: string
- stakeholders: array of strings
- constraints: array of strings
- data_sources: array of strings
- risk_factors: array of strings
- confidence_level: string (high/medium/low)

Be thorough but concise. If a category has no items, use an empty array."""

        user_prompt = f"""Decision Text:
{decision_text}"""

        if additional_context:
            user_prompt += f"\n\nAdditional Context:\n{additional_context}"

        # Call OpenAI
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,  # Low temperature for consistent extraction
            response_format={"type": "json_object"},
        )

        raw_response = response.choices[0].message.content or "{}"

        # Parse and validate response
        try:
            context_data = json.loads(raw_response)
            context = DecisionContext(**context_data)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse LLM response: {e}") from e

        # Store reasoning in trace
        if self._trace:
            self._trace.reasoning = (
                f"Extracted decision context using {self.model}. "
                f"Confidence: {context.confidence_level or 'unknown'}"
            )

        return {
            "context": context.model_dump(),
            "raw_response": raw_response,
        }
