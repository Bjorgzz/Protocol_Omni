# Protocol OMNI - Code Style & Conventions

## Python Style

- **Version:** Python 3.11+
- **Line Length:** 100 characters (ruff)
- **Type Hints:** Required on all function signatures
- **Docstrings:** Minimal, only for complex logic

## Ruff Configuration

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
```

## Naming Conventions

- **Classes:** PascalCase (`CognitiveRouter`, `MetacognitionEngine`)
- **Functions:** snake_case (`route_request`, `verify_output`)
- **Constants:** UPPER_SNAKE_CASE (`COMPLEXITY_THRESHOLD`)
- **Enums:** PascalCase with UPPER_SNAKE values

## Patterns

### Pydantic Models
```python
class AgentRequest(BaseModel):
    messages: list[dict]
    model: str | None = None
    
    def estimate_complexity(self) -> ComplexityLevel:
        ...
```

### Async Context Managers
```python
class MetacognitionEngine:
    async def __aenter__(self):
        self._client = httpx.AsyncClient()
        return self
    
    async def __aexit__(self, *args):
        await self._client.aclose()
```

### FastAPI Endpoints
```python
@app.post("/v1/route")
async def route(request: AgentRequest) -> RoutingDecision:
    ...
```

## Import Order (ruff I)

1. Standard library
2. Third-party packages
3. Local modules
