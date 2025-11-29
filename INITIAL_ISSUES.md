# Initial GitHub Issues

Create these issues in the repo to give Claude Code a backlog to work from.

---

## Issue #1: Create PlaybookLoader class
**Labels:** `type: feature`, `priority: high`, `component: engine`

### Description
Create the PlaybookLoader class that loads playbook definitions from YAML files.

### Acceptance Criteria
- [ ] Load single playbook from YAML file
- [ ] Validate playbook structure using Pydantic
- [ ] Support step types: skill, decision
- [ ] Handle template variables in YAML
- [ ] Unit tests with >80% coverage

### Technical Notes
Use Pydantic for validation, PyYAML for parsing, Jinja2 for template variables.

---

## Issue #2: Create PlaybookEngine class
**Labels:** `type: feature`, `priority: high`, `component: engine`

### Description
Create the PlaybookEngine class that executes playbooks.

### Acceptance Criteria
- [ ] Execute a playbook with skills
- [ ] Handle decision nodes with conditions
- [ ] Pass outputs between steps
- [ ] Generate execution trace
- [ ] Unit tests with >80% coverage

### Technical Notes
Depends on #1 (PlaybookLoader) and existing Skill classes.

---

## Issue #3: Create ExecutionTracer class
**Labels:** `type: feature`, `priority: high`, `component: engine`

### Description
Create the ExecutionTracer class that captures reasoning traces.

### Acceptance Criteria
- [ ] Capture step-by-step execution
- [ ] Record inputs/outputs for each step
- [ ] Record decision evaluations
- [ ] Record timing for each step
- [ ] Export trace as JSON
- [ ] Unit tests

### Technical Notes
Should integrate with PlaybookEngine.

---

## Issue #4: Create first skill - DecisionContextExtractor
**Labels:** `type: feature`, `priority: medium`, `component: skills`

### Description
Create the first governance skill for extracting context from AI decisions.

### Acceptance Criteria
- [ ] Extract key decision elements from text
- [ ] Identify stakeholders
- [ ] Identify constraints
- [ ] Identify data sources used
- [ ] Unit tests

### Technical Notes
Part of Governance module. Can use OpenAI for extraction.

---

## Issue #5: Create first playbook - AI Decision Audit
**Labels:** `type: feature`, `priority: medium`, `component: playbooks`

### Description
Create the AI Decision Audit playbook YAML definition.

### Acceptance Criteria
- [ ] Define playbook in YAML
- [ ] Include decision context extraction
- [ ] Include risk identification
- [ ] Include leadership questions generation
- [ ] Integration test that runs the playbook

### Technical Notes
Depends on #4 and related skills.

---

## Issue #6: Documentation - Architecture
**Labels:** `type: docs`, `priority: medium`, `component: docs`

### Description
Write architecture documentation explaining the framework.

### Acceptance Criteria
- [ ] Explain Skills → Playbooks → Traces pattern
- [ ] Include diagrams (Mermaid)
- [ ] Document extension points
- [ ] Examples of creating new skills
- [ ] Examples of creating new playbooks

---

## Issue #7: Documentation - Skills Reference
**Labels:** `type: docs`, `priority: low`, `component: docs`

### Description
Document all built-in skills.

### Acceptance Criteria
- [ ] Document each skill's purpose
- [ ] Document inputs/outputs
- [ ] Include usage examples
- [ ] Auto-generate from docstrings if possible

---

## Issue #8: Add pytest-cov and increase coverage
**Labels:** `type: chore`, `priority: low`

### Description
Ensure test coverage reporting is working and coverage is >80%.

### Acceptance Criteria
- [ ] pytest-cov configured
- [ ] Coverage report generated on CI
- [ ] Identify and fill coverage gaps

