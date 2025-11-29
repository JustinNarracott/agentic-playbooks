#!/bin/bash
# Create labels and issues for agentic-playbooks
# Run from the repo directory: bash create_issues.sh

REPO="JustinNarracott/agentic-playbooks"

echo "Creating labels for $REPO..."

# Create labels first (ignore errors if they exist)
gh label create "type: feature" --color 0052CC --description "New feature" --repo $REPO 2>/dev/null || true
gh label create "type: bug" --color D73A4A --description "Something broken" --repo $REPO 2>/dev/null || true
gh label create "type: docs" --color 7057FF --description "Documentation" --repo $REPO 2>/dev/null || true
gh label create "type: chore" --color 666666 --description "Maintenance" --repo $REPO 2>/dev/null || true
gh label create "type: question" --color FF69B4 --description "Needs Justin input" --repo $REPO 2>/dev/null || true
gh label create "priority: critical" --color B60205 --description "Drop everything" --repo $REPO 2>/dev/null || true
gh label create "priority: high" --color FF6B00 --description "Do this week" --repo $REPO 2>/dev/null || true
gh label create "priority: medium" --color FBCA04 --description "Do this sprint" --repo $REPO 2>/dev/null || true
gh label create "priority: low" --color 0E8A16 --description "Backlog" --repo $REPO 2>/dev/null || true

echo "Labels created!"
echo ""
echo "Creating issues..."

# Issue #1
gh issue create --repo $REPO \
  --title "Create PlaybookLoader class" \
  --label "type: feature" --label "priority: high" \
  --body "## Description
Create the PlaybookLoader class that loads playbook definitions from YAML files.

## Acceptance Criteria
- [ ] Load single playbook from YAML file
- [ ] Validate playbook structure using Pydantic
- [ ] Support step types: skill, decision
- [ ] Handle template variables in YAML
- [ ] Unit tests with >80% coverage

## Technical Notes
Use Pydantic for validation, PyYAML for parsing, Jinja2 for template variables.

## Files to create
- src/playbooks/loader.py
- src/playbooks/models.py (Pydantic models)
- tests/unit/test_playbook_loader.py"

echo "Created issue #1"

# Issue #2
gh issue create --repo $REPO \
  --title "Create PlaybookEngine class" \
  --label "type: feature" --label "priority: high" \
  --body "## Description
Create the PlaybookEngine class that executes playbooks.

## Acceptance Criteria
- [ ] Execute a playbook with skills
- [ ] Handle decision nodes with conditions
- [ ] Pass outputs between steps
- [ ] Generate execution trace
- [ ] Unit tests with >80% coverage

## Technical Notes
Depends on #1 (PlaybookLoader) and existing Skill classes.

## Files to create
- src/playbooks/engine.py
- tests/unit/test_playbook_engine.py"

echo "Created issue #2"

# Issue #3
gh issue create --repo $REPO \
  --title "Create ExecutionTracer class" \
  --label "type: feature" --label "priority: high" \
  --body "## Description
Create the ExecutionTracer class that captures reasoning traces.

## Acceptance Criteria
- [ ] Capture step-by-step execution
- [ ] Record inputs/outputs for each step
- [ ] Record decision evaluations
- [ ] Record timing for each step
- [ ] Export trace as JSON
- [ ] Unit tests

## Technical Notes
Should integrate with PlaybookEngine.

## Files to create
- src/playbooks/tracer.py
- tests/unit/test_tracer.py"

echo "Created issue #3"

# Issue #4
gh issue create --repo $REPO \
  --title "Create first skill - DecisionContextExtractor" \
  --label "type: feature" --label "priority: medium" \
  --body "## Description
Create the first governance skill for extracting context from AI decisions.

## Acceptance Criteria
- [ ] Extract key decision elements from text
- [ ] Identify stakeholders
- [ ] Identify constraints
- [ ] Identify data sources used
- [ ] Unit tests

## Technical Notes
Part of Governance module. Can use OpenAI for extraction.

## Files to create
- src/modules/governance/__init__.py
- src/modules/governance/skills/__init__.py
- src/modules/governance/skills/decision_context_extractor.py
- tests/unit/test_decision_context_extractor.py"

echo "Created issue #4"

# Issue #5
gh issue create --repo $REPO \
  --title "Create first playbook - AI Decision Audit" \
  --label "type: feature" --label "priority: medium" \
  --body "## Description
Create the AI Decision Audit playbook YAML definition.

## Acceptance Criteria
- [ ] Define playbook in YAML
- [ ] Include decision context extraction
- [ ] Include risk identification
- [ ] Include leadership questions generation
- [ ] Integration test that runs the playbook

## Technical Notes
Depends on #4 and related skills.

## Files to create
- playbooks/governance/ai_decision_audit.yaml
- tests/integration/test_ai_decision_audit.py"

echo "Created issue #5"

# Issue #6
gh issue create --repo $REPO \
  --title "Documentation - Architecture" \
  --label "type: docs" --label "priority: medium" \
  --body "## Description
Write architecture documentation explaining the framework.

## Acceptance Criteria
- [ ] Explain Skills > Playbooks > Traces pattern
- [ ] Include diagrams (Mermaid)
- [ ] Document extension points
- [ ] Examples of creating new skills
- [ ] Examples of creating new playbooks

## Files to create
- docs/architecture.md"

echo "Created issue #6"

# Issue #7
gh issue create --repo $REPO \
  --title "Documentation - Skills Reference" \
  --label "type: docs" --label "priority: low" \
  --body "## Description
Document all built-in skills.

## Acceptance Criteria
- [ ] Document each skill's purpose
- [ ] Document inputs/outputs
- [ ] Include usage examples
- [ ] Auto-generate from docstrings if possible

## Files to create
- docs/skills.md"

echo "Created issue #7"

# Issue #8
gh issue create --repo $REPO \
  --title "Add pytest-cov and increase coverage" \
  --label "type: chore" --label "priority: low" \
  --body "## Description
Ensure test coverage reporting is working and coverage is >80%.

## Acceptance Criteria
- [ ] pytest-cov configured in pyproject.toml
- [ ] Coverage report generated on CI
- [ ] Identify and fill coverage gaps
- [ ] Add coverage badge to README

## Files to modify
- pyproject.toml
- .github/workflows/ci.yml
- README.md"

echo "Created issue #8"

echo ""
echo "Done! View at: https://github.com/$REPO/issues"
