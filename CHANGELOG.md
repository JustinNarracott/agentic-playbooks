# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-29

### Added

#### Core Engine
- **PlaybookLoader** - Load and validate playbook definitions from YAML files with Pydantic models (#1)
  - Support for skill and decision step types
  - Jinja2 template variable substitution (opt-in when variables provided)
  - Comprehensive error handling and validation
  - Load from YAML files, strings, or Python dictionaries

- **PlaybookEngine** - Execute playbooks with skills and decision logic (#2)
  - Execute skill steps via SkillRegistry
  - Evaluate decision branches with Jinja2 conditions
  - Pass outputs between steps using `output_var`
  - Support for nested decision steps
  - Generate comprehensive execution traces

- **ExecutionTracer** - Capture comprehensive playbook execution traces (#3)
  - `StepTrace` for individual step execution with timing, inputs/outputs, errors
  - `ExecutionTrace` for complete playbook execution with all steps and final context
  - JSON export and import capabilities
  - Configurable indentation (formatted or compact JSON)

#### Advanced Features
- **CheckpointManager** - Checkpoint and resume support for long-running workflows (#10)
  - Save execution state after each step
  - Resume from any checkpoint
  - Automatic cleanup on successful completion
  - Error recovery with helpful resume instructions

- **PlaybookValidator** - Comprehensive playbook validation before execution (#23)
  - Syntax validation for YAML structure
  - Reference validation for undefined variables and skills
  - Logic validation for unreachable branches and circular dependencies
  - Configurable validation levels (ERROR, WARNING, INFO)
  - Integration with PlaybookEngine for pre-execution validation

- **PlaybookVisualizer** - Visual workflow diagrams in Mermaid and Graphviz formats (#22)
  - Mermaid flowchart generation
  - Graphviz DOT format generation
  - Decision tree visualization with branch conditions
  - Nested step representation
  - Save diagrams to files

- **BatchExecutor** - Parallel batch execution with concurrency control (#24)
  - Execute playbooks with multiple input contexts in parallel
  - Configurable concurrency limits with asyncio.Semaphore
  - Progress tracking and reporting
  - Aggregated results with success/failure statistics
  - Export results to JSON and CSV formats

- **MetricsCollector** - Comprehensive metrics collection and observability (#25)
  - Thread-safe counters, histograms, and gauges
  - Time-based retention for histogram values (default 1 hour)
  - Percentile calculations (P50, P95, P99)
  - Automatic tracking of:
    - Playbook execution counts and duration (success/failure)
    - Skill execution counts and duration (success/failure/not_found)
    - Decision branch frequencies
  - PrometheusExporter for Prometheus text format
  - StatsDExporter for StatsD UDP export

#### Error Handling
- **Comprehensive Error System** (#8)
  - `PlaybookExecutionError` - Base exception for execution errors
  - `SkillNotFoundError` - Skill registry lookup failures with suggestions
  - `TemplateError` - Jinja2 template rendering errors with context
  - `SkillExecutionError` - Skill execution failures with reasoning
  - `InvalidInputError` - Input validation errors
  - `CheckpointError` - Checkpoint operation errors
  - `ValidationError` - Playbook validation errors

#### Skills Framework
- **SkillRegistry** - Centralized skill registration and discovery
  - Singleton pattern for global skill access
  - Automatic metadata extraction from skill classes
  - List available skills with metadata

- **Base Skill Class** - Abstract base for all skills
  - Standardized `run()` method with input/output/trace
  - Metadata support (name, version, description, input/output schema)
  - Async execution support

#### Governance Skills Module
- **DecisionContextExtractor** - Extract context from AI decisions using OpenAI (#4)
  - Extract decision summary, stakeholders, constraints
  - Identify data sources and risk factors
  - Provide confidence levels for extractions
  - Store reasoning in execution trace

- **RiskIdentifier** - Identify and assess risks in AI decisions (#18)
  - Analyze decision context for potential risks
  - Assess risk severity (low/medium/high/critical)
  - Recommend mitigation actions
  - Overall risk level assessment

- **LeadershipQuestionsGenerator** - Generate thoughtful leadership questions (#20)
  - Strategic questions about business impact and alignment
  - Ethical questions about fairness, bias, and compliance
  - Operational questions about implementation and monitoring
  - Context-aware question generation

#### Example Playbooks
- **AI Decision Audit Playbook** - Complete governance workflow (#9)
  - Extract decision context from text
  - Identify and assess risks
  - Generate leadership questions for review
  - Comprehensive 3-step workflow example

#### Documentation
- Comprehensive README with installation, quick start, and examples
- API documentation with docstrings for all public classes and methods
- Skills documentation with usage examples
- Playbook format specification
- Template rendering guide
- Error handling guide

### Testing
- 194 unit tests with 84% code coverage
- Integration tests for complete workflows
- Docker-based testing environment
- Automated CI/CD with GitHub Actions
- Linting with black, ruff, and mypy

### Development Tools
- Docker workspace for consistent development environment
- docker-compose setup with volume mounts
- Pre-configured Python 3.11 environment
- Development dependencies (pytest, black, ruff, mypy)

---

## Release Notes

**Agentic Playbooks v1.0.0** is a production-ready framework for building and executing agentic workflows with AI skills. This initial release provides a complete foundation for:

- **Workflow Orchestration**: Define complex multi-step workflows with skills and decision logic
- **AI Integration**: Seamlessly integrate AI capabilities through the skills framework
- **Production Ready**: Comprehensive error handling, validation, checkpointing, and metrics
- **Developer Friendly**: Clear abstractions, extensive documentation, and testing tools

### What's Next?

Future releases will focus on:
- Additional built-in skills for common AI operations
- Enhanced visualization and debugging tools
- Performance optimizations for large-scale batch processing
- Community-contributed skills and playbooks

### Contributors

Built with ❤️ by [@justinnarracott](https://github.com/JustinNarracott) and Claude Code.

---

[1.0.0]: https://github.com/JustinNarracott/agentic-playbooks/releases/tag/v1.0.0
