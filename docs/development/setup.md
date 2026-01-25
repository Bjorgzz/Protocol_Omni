# Development Setup

Guide for setting up a local development environment for Protocol OMNI.

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | With pip and venv |
| Docker | 29.x | With NVIDIA Container Toolkit |
| kubectl | 1.28+ | For k8s deployments |
| SSH | - | Access to 192.168.3.10 |

## Local Setup

### 1. Clone Repository

```bash
# Replace YOUR-ORG with actual organization
git clone https://github.com/YOUR-ORG/Protocol_Omni.git
cd Protocol_Omni
```

### 2. Python Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or: .venv\Scripts\activate  # Windows

# Install with dev dependencies
pip install -e ".[dev]"
```

### 3. Verify Installation

```bash
# Run tests
pytest

# Type check
mypy src/

# Lint
ruff check src/
```

## Development Workflow

### Code Quality

```bash
# Format code
ruff format src/

# Lint with auto-fix
ruff check --fix src/

# Type check
mypy src/
```

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest src/metacognition/

# With coverage
pytest --cov=src/ --cov-report=html

# Verbose
pytest -v
```

### Pre-commit Checks

Before committing, run:

```bash
ruff check src/
mypy src/
pytest
```

## IDE Configuration

### VS Code

`.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.analysis.typeCheckingMode": "basic",
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff"
    }
}
```

### PyCharm

1. Set Python interpreter to `.venv/bin/python`
2. Enable Ruff plugin for linting
3. Configure mypy for type checking

## Remote Development

### SSH to Infrastructure

```bash
# SSH to omni-prime host
ssh omni@192.168.3.10

# With SSH key
ssh -i ~/.ssh/id_ed25519 omni@192.168.3.10
```

### Remote Docker

```bash
# Set Docker host
export DOCKER_HOST=ssh://omni@192.168.3.10

# Run commands remotely
docker ps
docker compose -f docker/omni-stack.yaml ps
```

## Testing Against Live Stack

### Health Checks

```bash
# Check inference engine
curl http://192.168.3.10:8000/health

# Check metacognition
curl http://192.168.3.10:8011/health

# Check agent orchestrator
curl http://192.168.3.10:8080/health
```

### Local Proxy

For local development against remote services:

```bash
# Forward inference port
ssh -L 8000:localhost:8000 omni@192.168.3.10

# Now access locally
curl http://localhost:8000/health
```

## Module Development

### Agent Router

```
src/agent/
├── __init__.py
└── router.py    # Cognitive routing logic
```

Key file: `src/agent/router.py` implements the Cognitive Trinity routing.

### Metacognition

```
src/metacognition/
├── __init__.py
├── engine.py    # Main verification pipeline
├── gates.py     # 4-gate implementations
└── test_gates.py
```

Run metacognition tests:
```bash
pytest src/metacognition/ -v
```

### GEPA (Legacy)

```
src/gepa/
├── __init__.py
├── evolution.py  # Genetic optimization
└── pareto.py     # Pareto frontier
```

> **Note**: GEPA is legacy research code. Production uses Letta (:8283) for self-improvement.

## Troubleshooting

### Import Errors

```bash
# Reinstall in dev mode
pip install -e ".[dev]"
```

### Type Check Failures

```bash
# Run with verbose output
mypy src/ --verbose
```

### Test Failures

```bash
# Run failed tests only
pytest --lf

# With debug output
pytest -v --tb=long
```

## Next Steps

- [Commands Reference](../operations/commands.md) - CLI commands
- [Architecture Overview](../architecture/overview.md) - System design
- [Docker Compose](../../docker/README.md) - Container configuration
