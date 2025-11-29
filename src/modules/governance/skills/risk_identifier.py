"""RiskIdentifier - analyzes decision context to identify and assess risks."""

import json
import os
from typing import Any, Dict, List

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from ....skills.base import Skill


class Risk(BaseModel):
    """Individual risk assessment."""

    severity: str = Field(description="Risk severity: low, medium, high, or critical")
    description: str = Field(description="Description of the risk")
    category: str = Field(
        description="Risk category: business, compliance, operational, reputational, etc."
    )
    likelihood: str = Field(
        default="unknown", description="Likelihood: low, medium, high, or unknown"
    )


class RiskAnalysis(BaseModel):
    """Structured risk analysis results."""

    risks: List[Risk] = Field(
        default_factory=list, description="List of identified risks"
    )
    overall_risk_level: str = Field(
        description="Overall risk level: low, medium, high, or critical"
    )
    recommended_actions: List[str] = Field(
        default_factory=list, description="Recommended mitigation actions"
    )
    confidence_level: str = Field(
        default="medium", description="Confidence in risk assessment"
    )


class RiskIdentifier(Skill):
    """
    Analyze decision context to identify and assess risks.

    This skill uses OpenAI to analyze decision context and:
    - Identify potential risks across multiple categories
    - Assess risk severity and likelihood
    - Determine overall risk level
    - Recommend mitigation actions

    Example:
        identifier = RiskIdentifier()
        output = await identifier.execute({
            "decision_context": {
                "decision_summary": "Approved $400k loan...",
                "stakeholders": ["applicant", "bank"],
                "risk_factors": ["high debt-to-income ratio"]
            }
        })
        # Returns: {
        #   "analysis": {
        #     "risks": [...],
        #     "overall_risk_level": "high",
        #     "recommended_actions": [...]
        #   }
        # }
    """

    name = "risk_identifier"
    version = "1.0.0"
    description = "Analyze decision context to identify and assess risks"

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
        Analyze decision context for risks.

        Args:
            input: Dictionary with:
                - decision_context (dict): Decision context from DecisionContextExtractor

        Returns:
            Dictionary with:
                - analysis (dict): Risk analysis results
                - raw_response (str): Raw LLM response for auditing

        Raises:
            ValueError: If decision_context is missing
        """
        decision_context = input.get("decision_context")
        if not decision_context:
            raise ValueError("decision_context is required")

        # Build prompt for risk analysis
        system_prompt = """You are a risk assessment expert analyzing AI decisions for potential risks.

Analyze the provided decision context and identify ALL potential risks across these categories:
- Business risks (financial, strategic, operational)
- Compliance risks (regulatory, legal, policy violations)
- Operational risks (process failures, dependencies, resource constraints)
- Reputational risks (brand damage, stakeholder concerns)
- Technical risks (system failures, data issues)
- Ethical risks (bias, fairness, transparency concerns)

For each risk:
1. Assess severity: low, medium, high, or critical
2. Assess likelihood: low, medium, high
3. Categorize the risk type
4. Provide clear description

Then:
- Determine overall risk level (highest severity found)
- Recommend 3-5 specific mitigation actions

Return your analysis as a JSON object with these exact keys:
- risks: array of objects with {severity, description, category, likelihood}
- overall_risk_level: string (low/medium/high/critical)
- recommended_actions: array of strings
- confidence_level: string (low/medium/high)

Be thorough - missing a critical risk could have serious consequences."""

        # Format decision context for analysis
        context_summary = f"""Decision Summary: {decision_context.get('decision_summary', 'Not provided')}

Stakeholders: {', '.join(decision_context.get('stakeholders', []))}

Constraints: {', '.join(decision_context.get('constraints', []))}

Data Sources: {', '.join(decision_context.get('data_sources', []))}

Pre-identified Risk Factors: {', '.join(decision_context.get('risk_factors', []))}"""

        # Call OpenAI
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_summary},
            ],
            temperature=0.2,  # Slightly higher for creative risk identification
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
            risk_count = len(analysis.risks)
            high_critical = sum(
                1 for r in analysis.risks if r.severity in ["high", "critical"]
            )
            self._trace.reasoning = (
                f"Analyzed decision context using {self.model}. "
                f"Identified {risk_count} risks ({high_critical} high/critical). "
                f"Overall risk level: {analysis.overall_risk_level}. "
                f"Confidence: {analysis.confidence_level}"
            )

        return {
            "analysis": analysis.model_dump(),
            "raw_response": raw_response,
        }
