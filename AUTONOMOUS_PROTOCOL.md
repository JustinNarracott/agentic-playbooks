# Autonomous Work Protocol

> How Claude/Claude Code works on this project autonomously

---

## The Golden Rules

1. **Bias towards action** - Do the work, don't just plan it
2. **Small commits, frequent checkpoints** - Never go dark for hours
3. **When in doubt, create an Issue not a PR** - Ask before going down wrong path
4. **Tests prove it works, docs explain why** - Both are required
5. **Justin reviews strategy, Claude handles execution** - Don't wait for approval on implementation details

---

## Decision Matrix

### ✅ PROCEED AUTONOMOUSLY (no check-in needed)

- Writing tests for existing code
- Fixing lint/type errors
- Implementing a well-defined Issue
- Writing documentation for existing code
- Refactoring without changing behaviour
- Adding examples/demos
- Updating CHANGELOG

### 📤 CREATE PR FOR REVIEW (checkpoint)

- Feature complete and tested
- New skill or playbook implemented
- Module added or significantly changed
- Breaking changes to API

### ⏸️ STOP AND ASK (create Issue)

- Architectural decision needed
- Multiple valid approaches, unclear which
- Scope unclear or expanding
- External dependency decision (API, library choice)
- Business logic unclear
- Blocked for >30 mins on same problem

---

## Workflow

### Daily Cycle

```
1. CHECK
   └── GitHub Issues for assigned tasks
   └── PRs for review feedback
   └── Pick highest priority unblocked Issue

2. WORK
   └── Create feature branch: feature/{issue-number}-{short-desc}
   └── Implement with tests
   └── Commit frequently with clear messages
   └── Update docs as you go

3. CHECKPOINT
   └── Run full test suite
   └── Run linters (black, ruff, mypy)
   └── Self-review diff
   └── Apply decision matrix

4. DELIVER
   └── Push branch
   └── Create PR or Issue per decision matrix
   └── Move to next task
```

### Commit Messages

Format: `{type}: {description}`

Types:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `test` - Tests
- `refactor` - Refactoring
- `chore` - Maintenance

Examples:
```
feat: add skill registry with decorator pattern
test: add unit tests for playbook loader
docs: update README with quick start guide
fix: handle empty input in decision node
```

### Branch Naming

Format: `{type}/{issue-number}-{short-description}`

Examples:
```
feature/12-skill-registry
fix/15-yaml-parsing-error
docs/18-api-reference
```

---

## PR Template

When creating a PR, use this structure:

```markdown
## Summary
[What does this PR do?]

## Related Issue
Closes #[number]

## Changes
- [Change 1]
- [Change 2]

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] `pytest` passes locally
- [ ] `black .` passes
- [ ] `ruff check .` passes

## Documentation
- [ ] README updated (if needed)
- [ ] Docstrings added
- [ ] CHANGELOG updated

@justinnarracott ready for review 🍾
```

---

## Question Issue Template

When you need to ask Justin something:

```markdown
## Context
[What were you working on?]

## The Question
[What do you need decided?]

## Options Considered

### Option A
- Pros:
- Cons:

### Option B
- Pros:
- Cons:

## My Recommendation
[What would you do if you had to choose?]

## Blocking?
- [ ] Yes, can't proceed without this
- [ ] No, can work on other things meanwhile
```

---

## Labels

### Priority
- `priority: critical` - Drop everything
- `priority: high` - Do this week
- `priority: medium` - Do this sprint
- `priority: low` - Backlog
- `priority: someday` - Parking lot

### Type
- `type: feature` - New capability
- `type: bug` - Something broken
- `type: docs` - Documentation
- `type: refactor` - Code improvement
- `type: question` - Needs Justin input

### Status
- `status: in-progress` - Being worked on
- `status: review-needed` - PR ready for Justin
- `status: blocked` - Can't proceed
- `status: approved` - Ready to merge

---

## Success Metrics

| Metric | Target |
|--------|--------|
| PRs merged without major revisions | >80% |
| Time from Issue to PR | <24 hours |
| Question Issues per week | <2 |
| Test coverage | >80% |
| Justin review time per PR | <10 mins |

---

*Drinking our own champagne 🍾*
