# Create labels and issues for agentic-playbooks
# Run: .\create_issues.ps1

$REPO = "JustinNarracott/agentic-playbooks"

Write-Host "Creating labels for $REPO..." -ForegroundColor Cyan

# Create labels (ignore errors if they exist)
gh label create "type: feature" --color 0052CC --description "New feature" --repo $REPO 2>$null
gh label create "type: bug" --color D73A4A --description "Something broken" --repo $REPO 2>$null
gh label create "type: docs" --color 7057FF --description "Documentation" --repo $REPO 2>$null
gh label create "type: chore" --color 666666 --description "Maintenance" --repo $REPO 2>$null
gh label create "type: question" --color FF69B4 --description "Needs Justin input" --repo $REPO 2>$null
gh label create "priority: critical" --color B60205 --description "Drop everything" --repo $REPO 2>$null
gh label create "priority: high" --color FF6B00 --description "Do this week" --repo $REPO 2>$null
gh label create "priority: medium" --color FBCA04 --description "Do this sprint" --repo $REPO 2>$null
gh label create "priority: low" --color 0E8A16 --description "Backlog" --repo $REPO 2>$null

Write-Host "Labels created!" -ForegroundColor Green
Write-Host ""
Write-Host "Creating issues..." -ForegroundColor Cyan

# Issue #1
$body1 = @"
## Description
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
- tests/unit/test_playbook_loader.py
"@
gh issue create --repo $REPO --title "Create PlaybookLoader class" --label "type: feature" --label "priority: high" --body $body1
Write-Host "Created issue #1" -ForegroundColor Green

# Issue #2
$body2 = @"
## Description
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
- tests/unit/test_playbook_engine.py
"@
gh issue create --repo $REPO --title "Create PlaybookEngine class" --label "type: feature" --label "priority: high" --body $body2
Write-Host "Created issue #2" -ForegroundColor Green

# Issue #3
$body3 = @"
## Description
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
- tests/unit/test_tracer.py
"@
gh issue create --repo $REPO --title "Create ExecutionTracer class" --label "type: feature" --label "priority: high" --body $body3
Write-Host "Created issue #3" -ForegroundColor Green

# Issue #4
$body4 = @"
## Description
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
- tests/unit/test_decision_context_extractor.py
"@
gh issue create --repo $REPO --title "Create first skill - DecisionContextExtractor" --label "type: feature" --label "priority: medium" --body $body4
Write-Host "Created issue #4" -ForegroundColor Green

# Issue #5
$body5 = @"
## Description
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
- tests/integration/test_ai_decision_audit.py
"@
gh issue create --repo $REPO --title "Create first playbook - AI Decision Audit" --label "type: feature" --label "priority: medium" --body $body5
Write-Host "Created issue #5" -ForegroundColor Green

# Issue #6
$body6 = @"
## Description
Write architecture documentation explaining the framework.

## Acceptance Criteria
- [ ] Explain Skills > Playbooks > Traces pattern
- [ ] Include diagrams (Mermaid)
- [ ] Document extension points
- [ ] Examples of creating new skills
- [ ] Examples of creating new playbooks

## Files to create
- docs/architecture.md
"@
gh issue create --repo $REPO --title "Documentation - Architecture" --label "type: docs" --label "priority: medium" --body $body6
Write-Host "Created issue #6" -ForegroundColor Green

# Issue #7
$body7 = @"
## Description
Document all built-in skills.

## Acceptance Criteria
- [ ] Document each skill's purpose
- [ ] Document inputs/outputs
- [ ] Include usage examples
- [ ] Auto-generate from docstrings if possible

## Files to create
- docs/skills.md
"@
gh issue create --repo $REPO --title "Documentation - Skills Reference" --label "type: docs" --label "priority: low" --body $body7
Write-Host "Created issue #7" -ForegroundColor Green

# Issue #8
$body8 = @"
## Description
Ensure test coverage reporting is working and coverage is >80%.

## Acceptance Criteria
- [ ] pytest-cov configured in pyproject.toml
- [ ] Coverage report generated on CI
- [ ] Identify and fill coverage gaps
- [ ] Add coverage badge to README

## Files to modify
- pyproject.toml
- .github/workflows/ci.yml
- README.md
"@
gh issue create --repo $REPO --title "Add pytest-cov and increase coverage" --label "type: chore" --label "priority: low" --body $body8
Write-Host "Created issue #8" -ForegroundColor Green

Write-Host ""
Write-Host "Done! View at: https://github.com/$REPO/issues" -ForegroundColor Cyan
