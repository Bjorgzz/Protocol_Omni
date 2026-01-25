# Contributing to Protocol OMNI

Thank you for contributing to Protocol OMNI! This document outlines how to contribute effectively.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker CE 29.x with NVIDIA Container Toolkit
- SSH access to the infrastructure (request from project maintainer)

### Development Setup

1. Clone the repository (replace `YOUR-ORG` with actual organization):
   ```bash
   git clone https://github.com/YOUR-ORG/Protocol_Omni.git
   cd Protocol_Omni
   ```

2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run tests:
   ```bash
   pytest
   ```

See [Development Setup](docs/development/setup.md) for detailed instructions.

## Code Style

### Python

- **Formatter**: `ruff format`
- **Linter**: `ruff check`
- **Type Checker**: `mypy`

```bash
# Run all checks
ruff check src/
mypy src/
pytest
```

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new model routing logic
fix: correct NUMA binding for Node 0
docs: update quickstart guide
refactor: simplify metacognition gates
```

## Pull Request Process

1. **Branch**: Create a feature branch from `main`
2. **Test**: Ensure all tests pass locally
3. **Lint**: Run `ruff check` and `mypy`
4. **Document**: Update relevant documentation
5. **PR**: Open a pull request with clear description

### PR Checklist

- [ ] Tests pass (`pytest`)
- [ ] Linting passes (`ruff check src/`)
- [ ] Type checking passes (`mypy src/`)
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventional format

## Project Structure

```
Protocol_Omni/
├── src/              # Python source code
│   ├── agent/        # Cognitive router
│   ├── metacognition/# 4-gate verification
│   └── gepa/         # Self-evolution (legacy)
├── docker/           # Docker Compose stacks
├── k8s/              # Kubernetes manifests
├── docs/             # Documentation
└── config/           # Configuration files
```

## Testing

```bash
# Run all tests
pytest

# Run specific module
pytest src/metacognition/

# With coverage
pytest --cov=src/
```

## Documentation

- Keep documentation in `docs/` directory
- Use Mermaid for diagrams
- Update [AGENTS.md](AGENTS.md) for AI agent context
- Cross-reference related documents

## Questions?

- Check existing [documentation](docs/README.md)
- Review [troubleshooting guide](docs/operations/troubleshooting.md)
- Open an issue for bugs or feature requests
