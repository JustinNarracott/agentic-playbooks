"""RiskIdentifier - identifies risks from decision context."""

import json
import os
from typing import Any, Dict, List

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from ....skills.base import Skill


class RiskAnalysis(BaseModel):
    """Structured risk analysis output."""

    risks: List[Dict[str, str]] = Field(
        description="List of identified risks with severity and mitigation"
    )
    overall_risk_level: str = Field(
        description="Overall risk level: low, medium, high, critical"
    )
    recommended_actions: List[str] = Field(
        default_factory=list, description="Recommended risk mitigation actions"
    )


class RiskIdentifier(Skill):
    """
    Identify and analyze risks from decision context.

    This skill analyzes decision context to identify potential risks,
    assess their severity, and recommend mitigation actions.

    Example:
        identifier = RiskIdentifier()
        output = await identifier.execute({
            "decision_context": {
                "decision_summary": "...",
                "stakeholders": [...],
                ...
            }
        })
    """

    name = "risk_identifier"
    version = "1.0.0"
    description = "Identify and analyze risks from decision context"

    def __init__(self) -> None:
        super().__init__()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable must be set to use RiskIdentifier"
            )
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify risks from decision context.

        Args:
            input: Dictionary with:
                - decision_context (dict): The decision context to analyze

        Returns:
            Dictionary with:
                - analysis (dict): Risk analysis results
                - raw_response (str): Raw LLM response

        Raises:
            ValueError: If decision_context is missing
        """
        decision_context = input.get("decision_context")
        if not decision_context:
            raise ValueError("decision_context is required")

        # Build prompt for risk analysis
        system_prompt = """You are a risk analyst evaluating AI decisions.
Analyze the decision context and identify potential risks:
1. List all risks with severity (low/medium/high/critical) and brief description
2. Assess overall risk level
3. Recommend specific mitigation actions

Return your analysis as a JSON object with these exact keys:
- risks: array of objects with {severity: string, description: string}
- overall_risk_level: string (low/medium/high/critical)
- recommended_actions: array of strings

Be thorough and specific."""

        context_str = json.dumps(decision_context, indent=2)
        user_prompt = f"""Decision Context:
{context_str}

Analyze this decision for potential risks."""

        # Call OpenAI
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        raw_response = response.choices[0].message.content or "{}"

        # Parse and validate response
        try:
            analysis_data = json.loads(raw_response)
            analysis = RiskAnalysis(**analysis_data)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse LLM response: {e}") from e

        # Store reasoning in trace
        if self._trace:
            self._trace.reasoning = (
                f"Identified {len(analysis.risks)} risks using {self.model}. "
                f"Overall risk level: {analysis.overall_risk_level}"
            )

        return {
            "analysis": analysis.model_dump(),
            "raw_response": raw_response,
        }
