# Sentinel Audit Integration Plan - 2026-01-28

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate findings from Sentinel Audit 2026-01-28 into Protocol OMNI architecture

**Architecture:** Tiered integration with zero VRAM disruption to production DeepSeek-R1-0528 Oracle

**Tech Stack:** llama.cpp b7857+, NVIDIA 590.x, MCP Apps, BitNet (eval), Qwen3-Omni (eval)

---

## Executive Summary

| Finding | Priority | Integration Point | Risk | Effort |
|---------|----------|-------------------|------|--------|
| llama.cpp b7857 | **P0** | `docker/omni-stack.yaml` | LOW | 2h |
| NVIDIA 590.x | P2 | Host driver | **HIGH** | 4h |
| MCP Apps Extension | **P0** | `src/mcp_proxy/gateway.py` | LOW | 4h |
| Llama 4 Scout | P1 | `config/agent_stack.yaml` | LOW | 8h |
| BitNet b1.58 | P2 | `src/agent/nodes/classification.py` | MEDIUM | 8h |
| Qwen3-Omni | P2 | `docker/omni-stack.yaml` | LOW | 4h |
| Moltbot | P3 | New service | LOW | 16h |

---

## Current vs. Proposed Architecture

### Layer 1: Inference Engine

| Aspect | Current State | Proposed State | Delta |
|--------|---------------|----------------|-------|
| **llama.cpp** | b7848 (`68ac3acb4`) | b7857+ | +9 releases |
| **Key Fix** | MLA + q4_1 KV cache | `cuda: fix 'V is K view' check` | Stability |
| **File** | `docker/omni-stack.yaml:43-89` | Same location | In-place |
| **Image** | `omni/llama-server:sm120-cuda13` | `omni/llama-server:sm120-cuda13-b7857` | New tag |

**Current Configuration (R1-0528 Production - Iron Lung):**
```yaml
# Container: deepseek-r1-0528
# Model: DeepSeek-R1-0528 Q4_K_M (~409GB)
# Baseline: 11.20 tok/s
exec llama-server \
  --model /models/deepseek-r1-0528/DeepSeek-R1-0528-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8000 \
  --n-gpu-layers 19 \
  --ctx-size 8192 \
  --tensor-split 75,25 \
  --cache-type-k q4_1
```

**Proposed Change:** Image tag update only. No parameter changes required.

---

### Layer 2: Driver Stack

| Aspect | Current State | Proposed State | Delta |
|--------|---------------|----------------|-------|
| **NVIDIA Driver** | 580.x | 590.126.09+ | +1 branch |
| **Target** | SM 12.0 support | SM 12.0 optimized | Perf |
| **File** | Host OS | Host OS | System-level |
| **Risk** | N/A | Reboot required | Downtime |

**Prerequisite Check:**
```bash
nvidia-smi --query-gpu=driver_version --format=csv,noheader
# Current: 580.x
# Target: 590.126.09+
```

---

### Layer 3: MCP Gateway

| Aspect | Current State | Proposed State | Delta |
|--------|---------------|----------------|-------|
| **Protocol** | MCP 1.0 (tools return JSON) | MCP Apps (tools return UI) | +UI layer |
| **File** | `src/mcp_proxy/gateway.py` | Same + new models | Extend |
| **Response Type** | `ToolInvokeResponse.result: Any` | `result: Any | UIComponent` | Union |

**Current Response Model (lines 48-55):**
```python
class ToolInvokeResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    audit_id: str
    duration_ms: float
```

**Proposed Addition:**
```python
from typing import Union, Literal

class UIComponent(BaseModel):
    type: Literal["text", "image", "form", "chart", "table"]
    data: Dict[str, Any]
    interactive: bool = False

class ToolInvokeResponse(BaseModel):
    success: bool
    result: Optional[Union[Any, UIComponent]] = None
    ui_components: Optional[List[UIComponent]] = None  # MCP Apps extension
    error: Optional[str] = None
    audit_id: str
    duration_ms: float
```

---

### Layer 4: Cognitive Trinity - Alternative Oracles

| Aspect | Current State | Proposed State | Delta |
|--------|---------------|----------------|-------|
| **Primary Oracle** | DeepSeek-V3.2 671B | DeepSeek-V3.2 671B | UNCHANGED |
| **Alternative** | None (VRAM blocked) | Llama 4 Scout (API) | +External |
| **File** | `config/agent_stack.yaml` | Same + new entry | Extend |
| **Context** | 8192 tokens | 10M tokens (Scout) | 1200x |

**Current Oracle Config (lines 11-49):**
```yaml
cognitive_trinity:
  oracle:
    name: deepseek-v3.2
    endpoint: http://deepseek-v32:8000/v1
    context_size: 8192
    timeout_seconds: 300
```

**Proposed Addition:**
```yaml
cognitive_trinity:
  oracle:
    name: deepseek-v3.2
    # ... existing config ...
    
  oracle_alternative:
    name: llama-4-scout
    endpoint: https://api.meta.ai/v1  # Or local if 109B GGUF fits
    context_size: 10000000  # 10M tokens
    timeout_seconds: 600
    use_case: "Long document analysis, multi-file context"
    cost_tier: api  # Track API costs separately
```

---

### Layer 5: Classification - BitNet Evaluation

| Aspect | Current State | Proposed State | Delta |
|--------|---------------|----------------|-------|
| **Classifier** | Heuristic (keyword match) | BitNet 1-bit LLM | +ML |
| **File** | `src/agent/nodes/classification.py` | Same + BitNet option | Extend |
| **CPU Impact** | Zero (pure Python) | 5-7 tok/s CPU | New load |
| **Energy** | Negligible | 71-82% reduction vs BERT | Green |

**Current Classification (lines 126-151):**
```python
def _classify() -> tuple[ComplexityLevel, str]:
    # Check for trivial indicators
    if any(ind in prompt_lower for ind in TRIVIAL_INDICATORS):
        if len(prompt) < 50:
            return ComplexityLevel.TRIVIAL, "Trivial greeting/command"
    
    # Sovereign Vocabulary check
    for keyword in SOVEREIGN_VOCABULARY:
        if keyword in prompt_lower:
            return ComplexityLevel.COMPLEX, f"Sovereign vocabulary: '{keyword}'"
```

**Proposed Enhancement (P2 - Evaluation Phase):**
```python
BITNET_ENABLED = os.getenv("BITNET_CLASSIFIER", "false").lower() == "true"

async def _classify_with_bitnet(prompt: str) -> tuple[ComplexityLevel, str]:
    """Use BitNet b1.58 for ML-based classification."""
    if not BITNET_ENABLED:
        return None
    
    # BitNet inference (CPU-only, 5-7 tok/s)
    # Returns: {"complexity": "COMPLEX|ROUTINE|TRIVIAL", "confidence": 0.95}
    result = await bitnet_client.classify(prompt)
    
    if result.confidence > 0.8:
        return ComplexityLevel[result.complexity], f"BitNet: {result.confidence:.0%}"
    return None  # Fall back to heuristics
```

---

### Layer 6: Multimodal Backup - Qwen3-Omni

| Aspect | Current State | Proposed State | Delta |
|--------|---------------|----------------|-------|
| **Multimodal** | None | Qwen3-Omni | +Audio/Video |
| **File** | `docker/omni-stack.yaml` | New service | Add |
| **Profile** | N/A | `multimodal` | Optional |
| **VRAM** | N/A | CPU-only (GGUF) | Safe |

**Proposed Service:**
```yaml
qwen3-omni:
  image: omni/llama-server:sm120-cuda13
  container_name: qwen3-omni
  restart: unless-stopped
  profiles: ["multimodal"]
  environment:
    CUDA_VISIBLE_DEVICES: ""  # CPU-only to preserve VRAM
  volumes:
    - /nvme/models:/models:ro
  command:
    - |
      exec llama-server \
        --model /models/qwen3-omni-q4/qwen3-omni-Q4_K_M.gguf \
        --host 0.0.0.0 \
        --port 8003 \
        --threads 64 \
        --n-gpu-layers 0
  ports:
    - "8003:8003"
  networks:
    - omni-network
```

---

### Layer 7: User Interface - Moltbot

| Aspect | Current State | Proposed State | Delta |
|--------|---------------|----------------|-------|
| **UI** | None (API only) | Moltbot chat interface | +Frontend |
| **File** | N/A | `docker/omni-stack.yaml` | New service |
| **Profile** | N/A | `ui` | Optional |
| **Integration** | N/A | Routes to MCP Proxy | Gateway |

**Proposed Service (P3 - Future):**
```yaml
moltbot-ui:
  image: ghcr.io/moltbot/moltbot:latest
  container_name: moltbot-ui
  restart: unless-stopped
  profiles: ["ui"]
  environment:
    BACKEND_URL: "http://mcp-proxy:8070"
    ENABLE_MCP_APPS: "true"
  ports:
    - "3000:3000"
  networks:
    - omni-network
```

---

## Implementation Phases

### Phase 1: Core Stability (P0) - Week 1

| Task | Files | Action | Verification |
|------|-------|--------|--------------|
| 1.1 | `docker/omni-stack.yaml` | Update llama.cpp image tag | `curl localhost:8000/health` |
| 1.2 | `src/mcp_proxy/gateway.py` | Add UIComponent model | `pytest tests/mcp_proxy/` |
| 1.3 | `src/mcp_proxy/allowlist.py` | Add ext-apps permission | Manual test |

### Phase 2: Driver & Oracle (P1) - Week 2

| Task | Files | Action | Verification |
|------|-------|--------|--------------|
| 2.1 | Host OS | Upgrade NVIDIA driver | `nvidia-smi` |
| 2.2 | `config/agent_stack.yaml` | Add Llama 4 Scout entry | Config validation |
| 2.3 | `src/agent/nodes/inference.py` | Add Scout routing logic | Unit tests |

### Phase 3: Evaluation (P2) - Week 3

| Task | Files | Action | Verification |
|------|-------|--------|--------------|
| 3.1 | `src/agent/nodes/classification.py` | Add BitNet option | A/B test |
| 3.2 | `docker/omni-stack.yaml` | Add Qwen3-Omni service | `--profile multimodal` |

### Phase 4: Interface (P3) - Week 4+

| Task | Files | Action | Verification |
|------|-------|--------|--------------|
| 4.1 | `docker/omni-stack.yaml` | Add Moltbot service | `--profile ui` |
| 4.2 | Documentation | Update AGENTS.md | sentinel-doc-sync |

---

## Risk Assessment

| Upgrade | Risk | Mitigation |
|---------|------|------------|
| llama.cpp b7857 | LOW - Patch release | Keep b7848 image as fallback; **F-003**: any rebuild MUST use bare-metal build |
| NVIDIA 590.x | **HIGH** - Unvetted branch | Verify on test system first; fallback to 580.126.09 |
| MCP Apps | LOW - Additive | Feature flag `ENABLE_MCP_APPS` |
| Llama 4 Scout | LOW - API only | Cost monitoring, rate limits |
| BitNet | MEDIUM - New path | Feature flag, A/B testing |
| Qwen3-Omni | LOW - CPU profile | Separate Docker profile |
| Moltbot | LOW - Frontend only | Isolated service |

---

## Failure Registry Cross-Check

> **Verified against `docs/architecture/lessons-learned.md` on 2026-01-28**

| Upgrade | Related Failures | Verdict |
|---------|------------------|---------|
| llama.cpp b7857 | F-002, F-024 (ik_llama fork), **F-003 (VMM)** | **SAFE IF** image reuse; **REBUILD REQUIRES** bare-metal build to preserve CUDA VMM |
| NVIDIA 590.x | S-013 validates 580.126.09 only | **UNVETTED** - 590.x not yet validated; downgrade to P2 or verify first |
| MCP Apps | F-006 (Mem0 arm64, different system) | **SAFE** - Unrelated |
| Llama 4 Scout | F-020/F-022 (RAM constraints) | **API ONLY** - See sizing below |
| BitNet b1.58 | F-019 (kt-kernel segfault) | **SAFE** - Different engine, <1GB model |
| Qwen3-Omni | S-002 (Qwen CPU success) | **SAFE** - Proven pattern |
| Moltbot | F-007 (httpx async) | **SAFE** - Uses HTTP gateway |

### Llama 4 Scout Sizing Analysis

| Resource | Total | DeepSeek R1-0528 Consumes | Free for Scout | Scout Needs |
|----------|-------|---------------------------|----------------|-------------|
| GPU VRAM | 128GB (96+32) | 116GB (90+26) | **12GB** | ~60GB |
| System RAM | 377GB | 377GB + 32GB swap | **0GB** | ~60GB |

**Math:**
- Scout 109B at Q4_K_M ≈ 109B × 0.5 bytes/param = **~55GB** + KV cache overhead ≈ **60GB**
- DeepSeek R1-0528 Q4_K_M = 409GB (377GB RAM + 32GB NVMe swap)
- **Conclusion:** Scout cannot coexist with DeepSeek. Would require full model swap or API.

**No resurrection of blocked technologies.** All proposals either:
1. Use proven engines (llama.cpp mainline)
2. Add new capabilities without touching blocked paths
3. Use API fallbacks where local deployment is impossible (Scout)
4. **Require validation before execution** (NVIDIA 590.x)

---

## Rollback Plan

| Upgrade | Rollback Command |
|---------|------------------|
| llama.cpp | `docker compose up -d` (old image tag in compose) |
| NVIDIA 590.x | `sudo apt install nvidia-driver-580=580.126.09-0ubuntu1` |
| MCP Apps | Set `ENABLE_MCP_APPS=false` |
| Llama 4 Scout | Remove from agent_stack.yaml |
| BitNet | Set `BITNET_CLASSIFIER=false` |
| Qwen3-Omni | `docker compose --profile multimodal down` |
| Moltbot | `docker compose --profile ui down` |

---

## Success Criteria

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Inference stability | 11.20 tok/s | 11.20+ tok/s | Benchmark |
| MCP response types | JSON only | JSON + UI | Integration test |
| Long context routing | 8K max | 10M available | Config present |
| Classification accuracy | Heuristic | +ML option | A/B metrics |
| Energy efficiency | Baseline | -70% (BitNet) | Power monitoring |

---

## Files Modified Summary

| File | Modifications | Priority |
|------|---------------|----------|
| `docker/omni-stack.yaml` | Image tag, new services | P0, P2, P3 |
| `src/mcp_proxy/gateway.py` | UIComponent model | P0 |
| `config/agent_stack.yaml` | oracle_alternative entry | P1 |
| `src/agent/nodes/classification.py` | BitNet option | P2 |
| Host OS | NVIDIA driver | P1 |

---

## Next Steps

1. **Approve this plan** before any implementation
2. **Create worktree** for Phase 1 implementation
3. **Execute Phase 1** tasks using subagent-driven-development
4. **Validate** each phase before proceeding

---

*Plan generated by Sentinel Audit 2026-01-28*
