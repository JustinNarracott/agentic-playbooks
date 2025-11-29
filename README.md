# Agentic Playbooks Framework

> **Governable AI Agent Systems with Explicit Decision Logic**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)]()

---

## 🎯 What is This?

Agentic Playbooks is a framework for building **transparent, auditable AI agent systems**. 

The core pattern:

```
Skills (atomic capabilities)
    ↓
Playbooks (orchestrated sequences with explicit decision logic)
    ↓
Reasoning Traces (transparent, auditable execution)
```

**Key Differentiators:**
- **Governance-first** - Every decision is traceable and auditable
- **Explicit decision logic** - Playbooks surface decision points, not black box reasoning
- **Reasoning traces** - Every execution produces an auditable trail
- **Composable** - Small skills combine into complex workflows

---

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/justinnarracott/agentic-playbooks.git
cd agentic-playbooks

# Start dev environment
cd docker
docker-compose up -d

# Run tests
docker exec -it playbooks-workspace pytest

# Run an example
docker exec -it playbooks-workspace python -m examples.ai_decision_audit_demo
```

---

## 📁 Project Structure

```
agentic-playbooks/
├── src/
│   ├── playbooks/      # Core playbook engine
│   ├── skills/         # Skill base classes and registry
│   └── modules/        # Domain-specific modules
├── playbooks/          # YAML playbook definitions
├── skills/             # YAML skill definitions
├── tests/              # Unit and integration tests
├── docs/               # Documentation
└── examples/           # Demo scripts
```

---

## 🧩 Core Concepts

### Skills
Atomic capabilities that do one thing well:

```yaml
# skills/company_enrichment.yaml
name: company_enrichment
version: "1.0.0"
description: "Enrich company data with firmographics"

inputs:
  - name: company_name
    type: string
    required: true

outputs:
  - name: firmographics
    type: object
  - name: icp_score
    type: number

instructions: |
  Given a company name, research and return:
  - Industry, size, revenue
  - Key decision makers
  - Technology stack signals
```

### Playbooks
Orchestrated sequences of skills with explicit decision points:

```yaml
# playbooks/lead_qualification.yaml
name: lead_qualification
version: "1.0.0"
description: "Qualify inbound lead against ICP"

steps:
  - id: enrich
    skill: company_enrichment
    input:
      company_name: "{{ input.company }}"
      
  - id: score
    skill: icp_scoring
    input:
      firmographics: "{{ steps.enrich.output.firmographics }}"
      
  - id: route
    type: decision
    condition: "{{ steps.score.output.score >= 7 }}"
    if_true: fast_track_outreach
    if_false: nurture_sequence

output:
  qualification_result: "{{ steps.route.output }}"
  reasoning_trace: "{{ execution.trace }}"
```

### Reasoning Traces
Every execution produces a full audit trail:

```json
{
  "execution_id": "abc-123",
  "playbook": "lead_qualification",
  "steps": [
    {
      "id": "enrich",
      "skill": "company_enrichment",
      "input": {"company_name": "Acme Corp"},
      "output": {"firmographics": {...}, "icp_score": 8.5},
      "reasoning": "Found company in Apollo, matched against ICP criteria...",
      "duration_ms": 1250
    },
    {
      "id": "route",
      "type": "decision",
      "condition": "score >= 7",
      "evaluation": "8.5 >= 7 = true",
      "path_taken": "fast_track_outreach"
    }
  ]
}
```

---

## 📚 Modules

| Module | Purpose | Status |
|--------|---------|--------|
| **Governance / CAIO** | AI decision audits, risk assessment | 🚧 |
| **PMO / Delivery** | Project health checks, portfolio assurance | 📋 |
| **Sales / GTM** | Lead qualification, outreach planning | 📋 |
| **Transformation** | Opportunity discovery, AI strategy | 📋 |
| **Knowledge Work** | Research curation, synthesis | 📋 |
| **Career / Personal** | Coaching, career strategy | 📋 |

---

## 🛠️ Development

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Git

### Dev Environment
```bash
# Start containers
cd docker && docker-compose up -d

# Enter workspace
docker exec -it playbooks-workspace bash

# Run tests
pytest

# Run linters
black .
ruff check .
mypy src/
```

### Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📖 Documentation

- [Architecture](docs/architecture.md)
- [Skills Reference](docs/skills.md)
- [Playbooks Reference](docs/playbooks.md)
- [Examples](docs/examples.md)

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built on concepts from:
- [VoltAgent](https://voltagent.dev) - Agent framework patterns
- [Claude Skills](https://github.com/anthropics/anthropic-cookbook) - Modular capability model
- [AgentKit](https://github.com/BCG-X-Official/agentkit) - Action plan routing

---

*Built with 🍾 by [Justin Narracott](https://github.com/justinnarracott)*
