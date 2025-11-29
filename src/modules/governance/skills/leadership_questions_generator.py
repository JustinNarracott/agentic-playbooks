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
        description="Strategic questions about business impact"
    )
    ethical_questions: List[str] = Field(description="Ethical and compliance questions")
    operational_questions: List[str] = Field(
        description="Operational and implementation questions"
    )


class LeadershipQuestionsGenerator(Skill):
    """
    Generate questions for leadership review of AI decisions.

    This skill analyzes decision context and risks to generate
    thoughtful questions that leadership should consider.

    Example:
        generator = LeadershipQuestionsGenerator()
        output = await generator.execute({
            "decision_context": {...},
            "risk_analysis": {...}
        })
    """

    name = "leadership_questions_generator"
    version = "1.0.0"
    description = "Generate questions for leadership review"

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
        Generate leadership questions.

        Args:
            input: Dictionary with:
                - decision_context (dict): The decision context
                - risk_analysis (dict, optional): Risk analysis results

        Returns:
            Dictionary with:
                - questions (dict): Generated questions by category
                - raw_response (str): Raw LLM response

        Raises:
            ValueError: If decision_context is missing
        """
        decision_context = input.get("decision_context")
        if not decision_context:
            raise ValueError("decision_context is required")

        risk_analysis = input.get("risk_analysis", {})

        # Build prompt for question generation
        system_prompt = """You are a governance advisor helping leadership review AI decisions.
Generate thoughtful questions leadership should ask about this decision:
1. Strategic questions about business impact and alignment
2. Ethical questions about fairness, bias, and compliance
3. Operational questions about implementation and monitoring

Return your questions as a JSON object with these exact keys:
- strategic_questions: array of strings (3-5 questions)
- ethical_questions: array of strings (3-5 questions)
- operational_questions: array of strings (3-5 questions)

Questions should be specific, actionable, and thought-provoking."""

        context_str = json.dumps(
            {"decision_context": decision_context, "risk_analysis": risk_analysis},
            indent=2,
        )
        user_prompt = f"""Context and Analysis:
{context_str}

Generate leadership review questions."""

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
                f"Generated {total_questions} leadership questions using {self.model}"
            )

        return {
            "questions": questions.model_dump(),
            "raw_response": raw_response,
        }
