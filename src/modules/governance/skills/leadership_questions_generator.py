"""LeadershipQuestionsGenerator - generates questions for leadership review."""

import json
import os
from typing import Any, Dict, List

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from ....skills.base import Skill


class LeadershipQuestions(BaseModel):
    """Structured leadership questions output."""

    strategic_questions: List[str] = Field(
        default_factory=list,
        description="Strategic questions about business impact and alignment",
    )
    ethical_questions: List[str] = Field(
        default_factory=list,
        description="Ethical questions about fairness, bias, and compliance",
    )
    operational_questions: List[str] = Field(
        default_factory=list,
        description="Operational questions about implementation and monitoring",
    )


class LeadershipQuestionsGenerator(Skill):
    """
    Generate strategic leadership review questions for AI decisions.

    This skill uses OpenAI to generate thoughtful review questions across:
    - Strategic: business impact, alignment, ROI
    - Ethical: fairness, bias, compliance, human oversight
    - Operational: implementation, monitoring, escalation

    Example:
        generator = LeadershipQuestionsGenerator()
        output = await generator.execute({
            "decision_context": {
                "decision_summary": "Approved $400k loan...",
                "stakeholders": ["applicant", "bank"]
            },
            "risk_analysis": {
                "overall_risk_level": "high",
                "risks": [...]
            }
        })
        # Returns: {
        #   "questions": {
        #     "strategic_questions": [...],
        #     "ethical_questions": [...],
        #     "operational_questions": [...]
        #   }
        # }
    """

    name = "leadership_questions_generator"
    version = "1.0.0"
    description = "Generate strategic leadership review questions for AI decisions"

    def __init__(self) -> None:
        super().__init__()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable must be set to use LeadershipQuestionsGenerator"
            )
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate leadership review questions.

        Args:
            input: Dictionary with:
                - decision_context (dict): Decision context from DecisionContextExtractor
                - risk_analysis (dict, optional): Risk analysis from RiskIdentifier

        Returns:
            Dictionary with:
                - questions (dict): Leadership review questions by category
                - raw_response (str): Raw LLM response for auditing

        Raises:
            ValueError: If decision_context is missing
        """
        decision_context = input.get("decision_context")
        if not decision_context:
            raise ValueError("decision_context is required")

        risk_analysis = input.get("risk_analysis")

        # Build prompt for question generation
        system_prompt = """You are a leadership advisor generating strategic review questions for AI decisions.

Generate thoughtful, probing questions that leadership should consider when reviewing this AI decision.
Generate 3-5 questions in each of these categories:

**Strategic Questions** - Focus on:
- Business impact and ROI
- Alignment with organizational strategy
- Long-term implications
- Resource allocation
- Competitive positioning

**Ethical Questions** - Focus on:
- Fairness and bias concerns
- Treatment of different stakeholders
- Transparency and explainability
- Human oversight and accountability
- Compliance with values and policies

**Operational Questions** - Focus on:
- Implementation requirements
- Monitoring and ongoing review
- Escalation procedures
- Performance metrics
- Contingency plans

Return your questions as a JSON object with these exact keys:
- strategic_questions: array of strings
- ethical_questions: array of strings
- operational_questions: array of strings

Make questions specific to this decision context, not generic."""

        # Format context for analysis
        context_summary = f"""Decision Summary: {decision_context.get('decision_summary', 'Not provided')}

Stakeholders: {', '.join(decision_context.get('stakeholders', []))}

Constraints: {', '.join(decision_context.get('constraints', []))}

Data Sources: {', '.join(decision_context.get('data_sources', []))}"""

        if decision_context.get("risk_factors"):
            context_summary += f"\n\nRisk Factors: {', '.join(decision_context.get('risk_factors', []))}"

        # Add risk analysis if provided
        if risk_analysis:
            context_summary += f"\n\nOverall Risk Level: {risk_analysis.get('overall_risk_level', 'unknown')}"

            risks = risk_analysis.get("risks", [])
            if risks:
                high_severity = [
                    r for r in risks if r.get("severity") in ["high", "critical"]
                ]
                if high_severity:
                    context_summary += "\n\nHigh/Critical Risks:"
                    for risk in high_severity:
                        context_summary += (
                            f"\n- [{risk.get('severity')}] {risk.get('description')}"
                        )

        user_prompt = f"""Generate leadership review questions for this decision:

{context_summary}"""

        # Call OpenAI
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        raw_response = response.choices[0].message.content or "{}"

        # Parse and validate response
        try:
            questions_data = json.loads(raw_response)
            questions = LeadershipQuestions(**questions_data)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse LLM response: {e}") from e

        # Store reasoning in trace
        if self._trace:
            total_questions = (
                len(questions.strategic_questions)
                + len(questions.ethical_questions)
                + len(questions.operational_questions)
            )
            self._trace.reasoning = (
                f"Generated {total_questions} leadership review questions using {self.model}. "
                f"Strategic: {len(questions.strategic_questions)}, "
                f"Ethical: {len(questions.ethical_questions)}, "
                f"Operational: {len(questions.operational_questions)}"
            )

        return {
            "questions": questions.model_dump(),
            "raw_response": raw_response,
        }
