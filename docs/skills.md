# Skills Reference

This document provides a complete reference for all built-in skills in the Agentic Playbooks framework.

## Table of Contents

- [Governance Skills](#governance-skills)
  - [DecisionContextExtractor](#decisioncontextextractor)
  - [RiskIdentifier](#riskidentifier)
  - [LeadershipQuestionsGenerator](#leadershipquestionsgenerator)
- [Creating Custom Skills](#creating-custom-skills)
- [Skill Development Guidelines](#skill-development-guidelines)

## Governance Skills

The governance module provides skills for AI decision auditing, risk analysis, and compliance.

### DecisionContextExtractor

Extracts structured governance context from AI decision text using OpenAI.

**Module:** `src.modules.governance.skills.decision_context_extractor`

**Purpose:** Analyze decision text to extract key elements including stakeholders, constraints, data sources, and risk factors. This skill provides the foundation for AI decision governance by creating structured, auditable context.

**Configuration:**
- Requires `OPENAI_API_KEY` environment variable
- Optional `OPENAI_MODEL` environment variable (default: `gpt-4o-mini`)

**Input:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `decision_text` | string | Yes | The decision text to analyze |
| `additional_context` | string | No | Additional context for analysis |

**Output:**

| Field | Type | Description |
|-------|------|-------------|
| `context` | object | Structured decision context |
| `context.decision_summary` | string | Brief summary of the decision |
| `context.stakeholders` | array[string] | Identified stakeholders |
| `context.constraints` | array[string] | Constraints or limitations |
| `context.data_sources` | array[string] | Data sources used |
| `context.risk_factors` | array[string] | Potential risks identified |
| `context.confidence_level` | string | Confidence level (high/medium/low) |
| `raw_response` | string | Raw LLM response for auditing |

**Usage in Playbooks:**

```yaml
steps:
  - name: extract_context
    type: skill
    skill: decision_context_extractor
    input:
      decision_text: "{{ decision_text }}"
      additional_context: "{{ optional_context }}"
    output_var: extracted_context
```

**Python Usage:**

```python
from src.modules.governance import DecisionContextExtractor

# Initialize skill
extractor = DecisionContextExtractor()

# Execute
output, trace = await extractor.run({
    "decision_text": "We approved the loan application based on credit score...",
    "additional_context": "Customer has been with us for 5 years"
})

# Access results
context = output["context"]
print(f"Summary: {context['decision_summary']}")
print(f"Stakeholders: {context['stakeholders']}")
print(f"Risks: {context['risk_factors']}")

# Access trace for governance
print(f"Reasoning: {trace.reasoning}")
```

**Example Output:**

```json
{
  "context": {
    "decision_summary": "Approved $400k business loan based on credit score and revenue",
    "stakeholders": [
      "loan applicant",
      "bank",
      "credit bureau",
      "regulators"
    ],
    "constraints": [
      "maximum loan amount $500k",
      "minimum credit score 680"
    ],
    "data_sources": [
      "credit report",
      "income verification",
      "bank statements"
    ],
    "risk_factors": [
      "high debt-to-income ratio",
      "new business venture"
    ],
    "confidence_level": "high"
  },
  "raw_response": "..."
}
```

---

### RiskIdentifier

Analyzes decision context to identify and assess risks using OpenAI.

**Module:** `src.modules.governance.skills.risk_identifier`

**Purpose:** Evaluate decision context to identify potential risks, assess their severity, and recommend mitigation actions. Essential for risk management and governance workflows.

**Configuration:**
- Requires `OPENAI_API_KEY` environment variable
- Optional `OPENAI_MODEL` environment variable (default: `gpt-4o-mini`)

**Input:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `decision_context` | object | Yes | Decision context to analyze (from DecisionContextExtractor) |

**Output:**

| Field | Type | Description |
|-------|------|-------------|
| `analysis` | object | Risk analysis results |
| `analysis.risks` | array[object] | List of identified risks |
| `analysis.risks[].severity` | string | Risk severity (low/medium/high/critical) |
| `analysis.risks[].description` | string | Risk description |
| `analysis.overall_risk_level` | string | Overall risk level (low/medium/high/critical) |
| `analysis.recommended_actions` | array[string] | Recommended mitigation actions |
| `raw_response` | string | Raw LLM response for auditing |

**Usage in Playbooks:**

```yaml
steps:
  - name: analyze_risks
    type: skill
    skill: risk_identifier
    input:
      decision_context: "{{ extracted_context.context }}"
    output_var: risk_analysis
```

**Python Usage:**

```python
from src.modules.governance import RiskIdentifier, DecisionContextExtractor

# First extract context
extractor = DecisionContextExtractor()
context_output, _ = await extractor.run({
    "decision_text": "Approved high-value loan..."
})

# Then analyze risks
identifier = RiskIdentifier()
risk_output, trace = await identifier.run({
    "decision_context": context_output["context"]
})

# Access results
analysis = risk_output["analysis"]
print(f"Overall risk: {analysis['overall_risk_level']}")
print(f"Risks found: {len(analysis['risks'])}")

for risk in analysis["risks"]:
    print(f"- [{risk['severity']}] {risk['description']}")

print(f"\nRecommended actions:")
for action in analysis["recommended_actions"]:
    print(f"- {action}")
```

**Example Output:**

```json
{
  "analysis": {
    "risks": [
      {
        "severity": "high",
        "description": "High debt-to-income ratio increases default risk"
      },
      {
        "severity": "medium",
        "description": "New business venture has uncertain revenue"
      },
      {
        "severity": "low",
        "description": "Limited credit history available"
      }
    ],
    "overall_risk_level": "high",
    "recommended_actions": [
      "Require additional collateral",
      "Reduce loan amount to $300k",
      "Implement stricter monitoring schedule"
    ]
  },
  "raw_response": "..."
}
```

---

### LeadershipQuestionsGenerator

Generates strategic, ethical, and operational questions for leadership review of AI decisions.

**Module:** `src.modules.governance.skills.leadership_questions_generator`

**Purpose:** Create thoughtful questions that leadership should consider when reviewing AI decisions. Helps ensure proper oversight and governance of automated decision-making.

**Configuration:**
- Requires `OPENAI_API_KEY` environment variable
- Optional `OPENAI_MODEL` environment variable (default: `gpt-4o-mini`)

**Input:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `decision_context` | object | Yes | Decision context (from DecisionContextExtractor) |
| `risk_analysis` | object | No | Risk analysis (from RiskIdentifier) |

**Output:**

| Field | Type | Description |
|-------|------|-------------|
| `questions` | object | Generated questions by category |
| `questions.strategic_questions` | array[string] | Questions about business impact and alignment |
| `questions.ethical_questions` | array[string] | Questions about fairness, bias, and compliance |
| `questions.operational_questions` | array[string] | Questions about implementation and monitoring |
| `raw_response` | string | Raw LLM response for auditing |

**Usage in Playbooks:**

```yaml
steps:
  - name: generate_questions
    type: skill
    skill: leadership_questions_generator
    input:
      decision_context: "{{ extracted_context.context }}"
      risk_analysis: "{{ risk_analysis.analysis }}"
    output_var: leadership_questions
```

**Python Usage:**

```python
from src.modules.governance import (
    DecisionContextExtractor,
    RiskIdentifier,
    LeadershipQuestionsGenerator
)

# Extract context and analyze risks first
extractor = DecisionContextExtractor()
context_output, _ = await extractor.run({
    "decision_text": "Approved loan application..."
})

identifier = RiskIdentifier()
risk_output, _ = await identifier.run({
    "decision_context": context_output["context"]
})

# Generate leadership questions
generator = LeadershipQuestionsGenerator()
questions_output, trace = await generator.run({
    "decision_context": context_output["context"],
    "risk_analysis": risk_output["analysis"]
})

# Access results
questions = questions_output["questions"]

print("Strategic Questions:")
for q in questions["strategic_questions"]:
    print(f"- {q}")

print("\nEthical Questions:")
for q in questions["ethical_questions"]:
    print(f"- {q}")

print("\nOperational Questions:")
for q in questions["operational_questions"]:
    print(f"- {q}")
```

**Example Output:**

```json
{
  "questions": {
    "strategic_questions": [
      "Does this decision align with our risk appetite for small business lending?",
      "What is the expected ROI on this loan given the identified risks?",
      "How does this decision fit within our overall portfolio strategy?",
      "Are we adequately compensated for the risk level?"
    ],
    "ethical_questions": [
      "Are we treating all applicants fairly regardless of business type?",
      "Could this decision create bias in future lending decisions?",
      "Do we have appropriate human oversight of high-risk decisions?",
      "Are we transparent with the applicant about how the decision was made?"
    ],
    "operational_questions": [
      "What monitoring will we implement for this high-risk loan?",
      "Who is responsible for ongoing review and oversight?",
      "What are the escalation procedures if risks materialize?",
      "How will we measure the success of this decision over time?"
    ]
  },
  "raw_response": "..."
}
```

---

## Complete Governance Workflow Example

Here's how to use all three governance skills together:

**Playbook (`playbooks/governance/ai_decision_audit.yaml`):**

```yaml
metadata:
  name: ai_decision_audit
  version: 1.0.0
  description: Complete AI decision audit workflow

variables:
  decision_text: ""

steps:
  # Step 1: Extract decision context
  - name: extract_decision_context
    type: skill
    skill: decision_context_extractor
    input:
      decision_text: "{{ decision_text }}"
    output_var: context_extraction

  # Step 2: Analyze risks
  - name: analyze_risks
    type: skill
    skill: risk_identifier
    input:
      decision_context: "{{ context_extraction.context }}"
    output_var: risk_analysis

  # Step 3: Generate leadership questions
  - name: generate_leadership_questions
    type: skill
    skill: leadership_questions_generator
    input:
      decision_context: "{{ context_extraction.context }}"
      risk_analysis: "{{ risk_analysis.analysis }}"
    output_var: leadership_review

  # Step 4: Escalate high-risk decisions
  - name: assess_risk_level
    type: decision
    branches:
      - condition: "risk_analysis.analysis.overall_risk_level == 'critical' or risk_analysis.analysis.overall_risk_level == 'high'"
        steps:
          - name: flag_for_immediate_review
            type: skill
            skill: decision_context_extractor
            input:
              decision_text: "HIGH/CRITICAL RISK: Immediate review required"
              additional_context: "Risk level: {{ risk_analysis.analysis.overall_risk_level }}"
            output_var: escalation_flag
```

**Python Usage:**

```python
from src.playbooks import PlaybookLoader, PlaybookEngine
from src.skills.registry import SkillRegistry
from src.modules.governance import (
    DecisionContextExtractor,
    RiskIdentifier,
    LeadershipQuestionsGenerator
)

# Register skills
registry = SkillRegistry.get_instance()
registry.register(DecisionContextExtractor)
registry.register(RiskIdentifier)
registry.register(LeadershipQuestionsGenerator)

# Load and execute playbook
loader = PlaybookLoader()
playbook = loader.load_from_file("playbooks/governance/ai_decision_audit.yaml")

engine = PlaybookEngine(registry)
trace = await engine.execute(
    playbook,
    initial_context={
        "decision_text": "We approved a $400k loan for a startup business..."
    }
)

# Access results
context = trace.final_context["context_extraction"]["context"]
risks = trace.final_context["risk_analysis"]["analysis"]
questions = trace.final_context["leadership_review"]["questions"]

print(f"Decision: {context['decision_summary']}")
print(f"Overall Risk: {risks['overall_risk_level']}")
print(f"Questions Generated: {len(questions['strategic_questions']) + len(questions['ethical_questions']) + len(questions['operational_questions'])}")

# Export trace for compliance
trace.save_to_file("audit_traces/decision_12345.json")
```

---

## Creating Custom Skills

See the [Architecture documentation](architecture.md#creating-custom-skills) for detailed guidance on creating custom skills.

**Quick Example:**

```python
from typing import Any, Dict
from src.skills.base import Skill

class MyCustomSkill(Skill):
    """My custom skill description."""

    name = "my_custom_skill"
    version = "1.0.0"
    description = "Brief description of what this skill does"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the skill.

        Args:
            input: {
                "param1": str,
                "param2": int
            }

        Returns:
            {
                "result": str,
                "metadata": dict
            }
        """
        # Your skill logic here
        result = self._process(input["param1"], input["param2"])

        # Store reasoning for governance
        if self._trace:
            self._trace.reasoning = "Explanation of what happened"

        return {
            "result": result,
            "metadata": {"processed": True}
        }

# Register the skill
from src.skills.registry import SkillRegistry
registry = SkillRegistry.get_instance()
registry.register(MyCustomSkill)
```

---

## Skill Development Guidelines

### Best Practices

1. **Single Responsibility**: Each skill should do one thing well
2. **Type Safety**: Use type hints and validate inputs
3. **Error Handling**: Raise descriptive exceptions
4. **Tracing**: Store reasoning in `self._trace.reasoning` for governance
5. **Documentation**: Include clear docstrings with input/output specs
6. **Testing**: Write comprehensive unit tests

### Input/Output Patterns

**Simple Input/Output:**
```python
async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
    value = input["value"]
    result = self._transform(value)
    return {"result": result}
```

**Structured Input/Output with Pydantic:**
```python
from pydantic import BaseModel

class SkillInput(BaseModel):
    value: str
    options: dict = {}

class SkillOutput(BaseModel):
    result: str
    confidence: float

async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
    # Validate input
    validated_input = SkillInput(**input)

    # Process
    result = self._process(validated_input.value)

    # Return validated output
    output = SkillOutput(result=result, confidence=0.95)
    return output.model_dump()
```

### Error Handling

```python
async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
    # Validate required fields
    if "required_field" not in input:
        raise ValueError("required_field is required")

    try:
        # Your logic
        result = await self._call_external_api(input["data"])
    except ExternalAPIError as e:
        # Add context to errors
        raise ValueError(f"Failed to call external API: {e}") from e

    return {"result": result}
```

### Async Operations

All skills must be async to support I/O operations:

```python
async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
    # Async HTTP call
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    # Async database query
    result = await db.query(sql)

    return {"data": result}
```

### Governance and Tracing

Always populate reasoning for AI-powered skills:

```python
async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
    # Call AI model
    response = await self.openai_client.chat.completions.create(...)

    result = parse_response(response)

    # Store reasoning in trace
    if self._trace:
        self._trace.reasoning = (
            f"Analyzed using {self.model}. "
            f"Confidence: {result.get('confidence')}. "
            f"Reasoning: {result.get('explanation')}"
        )

    return result
```

### Testing Skills

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_skill():
    """Test skill execution."""
    skill = MyCustomSkill()

    output, trace = await skill.run({
        "param1": "test",
        "param2": 42
    })

    # Verify output
    assert output["result"] == expected_result

    # Verify trace
    assert trace.skill_name == "my_custom_skill"
    assert trace.error is None
    assert trace.duration_ms > 0
    assert trace.reasoning is not None
```

---

## Skill Registry

All skills must be registered before use:

```python
from src.skills.registry import SkillRegistry

# Get global registry instance
registry = SkillRegistry.get_instance()

# Register a skill
registry.register(MySkill)

# Get a skill
skill_class = registry.get("my_skill")

# List all skills
skill_names = registry.list_skills()
```

**Decorator Registration:**

```python
from src.skills.registry import skill

@skill
class MySkill(Skill):
    name = "my_skill"
    # ...
```

---

## Additional Resources

- [Architecture Documentation](architecture.md) - Framework design and patterns
- [API Documentation](api.md) - Complete API reference
- [Examples](../examples/) - Sample skills and playbooks

For questions or contributions, see the project README.
