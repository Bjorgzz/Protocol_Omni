# Monitoring Guide

> Prometheus, Grafana, Arize Phoenix

## Stack Overview

```mermaid
graph LR
    subgraph "Zone B: Agents"
        AO["Agent Orchestrator<br/>:8080"]
        MCP["MCP Proxy<br/>:8070"]
        MC["Metacognition<br/>:8011"]
    end
    
    subgraph "Observability"
        PHOENIX["Arize Phoenix<br/>:6006 (UI)<br/>:4317 (OTLP)"]
        PROM["Prometheus<br/>:9090"]
        GRAFANA["Grafana<br/>:3000"]
    end
    
    AO -->|traces| PHOENIX
    MCP -->|traces| PHOENIX
    AO -->|metrics| PROM
    PROM --> GRAFANA
```

**Note**: Phoenix has built-in OTLP receiver on :4317. No separate OTEL Collector required.

## Prometheus

### Access

```bash
# Web UI
open http://192.168.3.10:9090

# API
curl http://localhost:9090/-/healthy
curl http://localhost:9090/api/v1/targets
```

### Key Metrics

| Metric | Description |
|--------|-------------|
| `inference_tokens_per_second` | Model throughput |
| `inference_latency_seconds` | Request latency |
| `gpu_memory_used_bytes` | VRAM utilization |
| `kube_pod_container_status_restarts_total` | Container restarts |

### Alert Rules

```yaml
# Blackwell Reset Loop Detection
- alert: BlackwellResetLoopRisk
  expr: increase(kube_pod_container_status_restarts_total{container="ktransformers"}[10m]) > 2
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "GPU pod restart loop detected"
    action: "kubectl scale deployment inference-engine --replicas=0"

# Low Inference Throughput
- alert: LowInferenceThroughput
  expr: inference_tokens_per_second < 5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Inference throughput below 5 tok/s"

# High GPU Memory
- alert: HighGPUMemory
  expr: gpu_memory_used_bytes / gpu_memory_total_bytes > 0.95
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "GPU memory above 95%"
```

## Grafana

### Access

```bash
# Web UI (default: admin/admin)
open http://192.168.3.10:3000
```

### Dashboards

| Dashboard | Purpose |
|-----------|---------|
| **OMNI Overview** | System health summary |
| **GPU Metrics** | VRAM, utilization, temperature |
| **Inference Latency** | P50, P95, P99 latencies |
| **Memory Systems** | Qdrant, Memgraph, Mem0 |

### Creating Dashboards

```bash
# Import from JSON
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @docker/dashboards/omni-overview.json
```

## Arize Phoenix

AI observability platform for distributed tracing. **Status: LIVE on :6006**

### Access

```bash
# Web UI
open http://192.168.3.10:6006

# Health
curl http://localhost:6006/health
```

### Project: `omni-agent`

All traces flow into the `omni-agent` project configured in `src/agent/main.py`.

### Trace Hierarchy

When you send a request to `/v1/chat/completions`, Phoenix captures this span structure:

```
[POST /v1/chat/completions] (root span)
├── [cognitive_routing] (12ms)
│   ├── complexity = "complex"|"routine"|"trivial"
│   ├── prompt_length = 156
│   ├── routed_to = "deepseek-v32"|"qwen-executor"
│   └── fallback_used = true|false
├── [model_inference] (2180ms)  ← TTFT visible here
│   ├── endpoint = "http://deepseek-v32:8000/v1"
│   ├── model = "deepseek-v32"
│   ├── latency_ms = 2180
│   ├── status_code = 200
│   └── tokens = 156
├── [mcp_tool_invoke] (145ms)   ← Only if tools used
│   ├── tool = "mcp_ssh-mcp"
│   ├── method = "ssh_execute"
│   ├── allowed = true|false
│   ├── duration_ms = 145
│   └── rate_limited = false
└── [metacog_verify] (3ms)
    ├── verdict = "pass"|"fail"
    └── confidence = 0.85
```

### Common Queries

**Filter by complexity**:
- Click Traces → Filter → `complexity = "complex"`

**Find fallbacks**:
- Filter → `fallback_used = true`

**Find slow requests**:
- Filter → `latency_ms > 3000`

**Find tool denials**:
- Filter → `allowed = false`

### Configuration

```yaml
# docker/omni-stack.yaml
arize-phoenix:
  image: arizephoenix/phoenix:latest
  ports:
    - "6006:6006"    # UI
    - "4317:4317"    # OTLP gRPC (receives traces directly)
  volumes:
    - /nvme/phoenix-data:/data
  environment:
    PHOENIX_WORKING_DIR: /data
```

### Integration

Tracer registration in `src/agent/main.py`:

```python
from phoenix.otel import register

tracer_provider = register(
    project_name="omni-agent",
    endpoint="http://arize-phoenix:4317"
)
```

Span creation in `src/agent/router.py`:

```python
from opentelemetry import trace

tracer = trace.get_tracer("omni.router")

async def route(self, request):
    with tracer.start_as_current_span("cognitive_routing") as span:
        span.set_attribute("complexity", complexity.value)
        span.set_attribute("routed_to", decision.model_name)
        # ...
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No traces visible | Check Phoenix logs: `docker logs arize-phoenix` |
| Connection refused | Verify `PHOENIX_ENDPOINT` env var in agent container |
| Missing spans | Confirm OTEL packages in `requirements.txt` |
| Traces not persisting | Check `/nvme/phoenix-data` volume mount |

## Health Check Script

```bash
#!/bin/bash
# scripts/health-check.sh

echo "=== Inference ==="
curl -s http://localhost:8000/health | jq .

echo "=== Agent Orchestrator ==="
curl -s http://localhost:8080/health | jq .

echo "=== MCP Proxy ==="
curl -s http://localhost:8070/health | jq .

echo "=== Phoenix ==="
curl -s http://localhost:6006/health

echo "=== Prometheus ==="
curl -s http://localhost:9090/-/healthy

echo "=== Grafana ==="
curl -s http://localhost:3000/api/health | jq .

echo "=== GPU ==="
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Prometheus not scraping | Check target status at `:9090/targets` |
| Grafana no data | Verify data source configuration |
| Phoenix traces missing | Check agent logs for "Phoenix tracing initialized" |
| MCP Proxy 403 | Tool not in allowlist - check `config/mcp-allowlist.yaml` |
| High metric cardinality | Review label usage |

## Related Documentation

- [Commands](commands.md) - CLI reference
- [Troubleshooting](troubleshooting.md) - Common issues
- [Architecture](../architecture/overview.md) - System overview
