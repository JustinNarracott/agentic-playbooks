# Contributing to Agentic Playbooks

Thank you for your interest in contributing to Agentic Playbooks! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project follows a simple code of conduct:

- Be respectful and considerate in all interactions
- Focus on constructive feedback and collaboration
- Welcome newcomers and help them get started
- Assume good intent from all contributors

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Git
- Basic understanding of async Python

### Setting Up Development Environment

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/yourusername/agentic-playbooks.git
   cd agentic-playbooks
   ```

2. **Start the development environment:**
   ```bash
   cd docker
   docker-compose up -d
   ```

3. **Enter the workspace:**
   ```bash
   docker exec -it playbooks-workspace bash
   ```

4. **Run tests to verify setup:**
   ```bash
   pytest
   ```

## Development Workflow

### 1. Create a Feature Branch

Always work on a feature branch, never directly on `main`:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Your Changes

- Write clean, readable code
- Follow the coding standards below
- Add tests for new functionality
- Update documentation as needed

### 3. Run Tests and Linters

Before committing, ensure all tests and checks pass:

```bash
# Run all tests
pytest

# Check coverage (must be >80%)
pytest --cov=src --cov-report=term-missing

# Format code
black .

# Lint code
ruff check .

# Type check
mypy src/
```

### 4. Commit Your Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "feat: add new skill for data validation

- Implements DataValidator skill
- Adds comprehensive unit tests
- Updates documentation"
```

**Commit message format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Coding Standards

### Python Style

- Follow PEP 8 style guide
- Use type hints for all function signatures
- Maximum line length: 88 characters (enforced by Black)
- Use async/await for I/O operations

### Code Organization

**Skills:**
```python
from typing import Any, Dict
from src.skills.base import Skill

class MySkill(Skill):
    """Brief description of what the skill does."""

    name = "my_skill"
    version = "1.0.0"
    description = "Detailed description"

    async def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the skill.

        Args:
            input: Description of input parameters

        Returns:
            Description of output
        """
        # Implementation here
        pass
```

**Playbooks:**
```yaml
metadata:
  name: my_playbook
  version: 1.0.0
  description: Clear description of playbook purpose

variables:
  # Define variables with defaults

steps:
  - name: descriptive_step_name
    type: skill
    skill: skill_name
    input:
      param: "{{ variable }}"
    output_var: result
```

### Documentation

- All public functions/classes must have docstrings
- Use Google-style docstring format
- Include examples for complex functionality
- Keep documentation up to date with code changes

## Testing

### Test Requirements

- All new features must include tests
- Maintain >80% code coverage
- Tests must be deterministic (no flaky tests)
- Use mocks for external services

### Test Organization

```
tests/
├── unit/           # Unit tests for individual components
└── integration/    # Integration tests for workflows
```

### Writing Tests

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestMySkill:
    """Test suite for MySkill."""

    @pytest.mark.asyncio
    async def test_skill_success(self):
        """Test successful skill execution."""
        skill = MySkill()
        output, trace = await skill.run({"input": "value"})

        assert output["result"] == expected_value
        assert trace.error is None

    @pytest.mark.asyncio
    async def test_skill_error_handling(self):
        """Test skill error handling."""
        skill = MySkill()

        with pytest.raises(ValueError, match="expected error"):
            await skill.run({"invalid": "input"})
```

## Documentation

### When to Update Documentation

Update documentation when:
- Adding new features
- Changing existing behavior
- Adding new skills or playbooks
- Modifying architecture

### Documentation Files

- `README.md` - Project overview and quick start
- `docs/architecture.md` - Framework design and patterns
- `docs/skills.md` - Skills reference
- Code docstrings - Inline documentation

### Documentation Style

- Use clear, concise language
- Include code examples
- Add diagrams where helpful (Mermaid)
- Keep examples realistic and practical

## Pull Request Process

### Before Submitting

1. ✅ All tests pass
2. ✅ Code coverage >80%
3. ✅ Linters pass (black, ruff, mypy)
4. ✅ Documentation updated
5. ✅ Commit messages are clear

### PR Template

When creating a pull request, include:

**Title:** Clear, descriptive title (e.g., "feat: add data validation skill")

**Description:**
```markdown
## Summary
Brief description of what this PR does

## Changes
- List of specific changes
- Organized by category if needed

## Testing
- Description of how you tested
- Any manual testing performed

## Documentation
- List documentation updates
```

### Review Process

1. Automated checks run on all PRs
2. Maintainer reviews code and provides feedback
3. Address review comments
4. Once approved, PR will be merged

### After Merge

- Delete your feature branch
- Pull latest `main` branch
- Celebrate your contribution! 🎉

## Skill Contribution Guidelines

### Creating New Skills

When contributing a new skill:

1. **Choose appropriate module:**
   - `src/modules/governance/` - AI governance and compliance
   - `src/modules/` - Create new module for new domains

2. **Implement skill class:**
   - Extend `Skill` base class
   - Implement `execute()` method
   - Use clear, descriptive names

3. **Add comprehensive tests:**
   - Test success cases
   - Test error handling
   - Test edge cases
   - Aim for 100% coverage

4. **Document the skill:**
   - Add to `docs/skills.md`
   - Include input/output specifications
   - Provide usage examples

5. **Register the skill:**
   - Update module `__init__.py`
   - Ensure it's importable

## Playbook Contribution Guidelines

### Creating New Playbooks

When contributing a new playbook:

1. **Define clear purpose:**
   - What problem does it solve?
   - Who is the target user?

2. **Use existing skills:**
   - Leverage existing skills when possible
   - Only create new skills if necessary

3. **Add integration test:**
   - Test end-to-end execution
   - Verify expected outputs
   - Test error scenarios

4. **Document usage:**
   - Add example to documentation
   - Show expected inputs/outputs

## Questions?

If you have questions:
- Open a GitHub Discussion
- Check existing documentation
- Review closed issues for similar questions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Agentic Playbooks! 🙏
