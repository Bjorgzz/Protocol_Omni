# Protocol OMNI: Verification Procedures Manual

> **Version**: v16.2.2 NPS1 OPTIMIZED  
> **Purpose**: Copy-pasteable commands to verify system state  
> **Last Updated**: 2026-01-24

---

## 1. Hardware Topology Verification

### 1.1 Confirm Single NUMA Node (NPS1)

```bash
ssh omni@192.168.3.10 "numactl --hardware | head -5"
```

**Expected Output**:
```
available: 1 nodes (0)
node 0 cpus: 0-191
node 0 size: 385807 MB
node 0 free: XXXXX MB
node distances:
```

**FAIL Condition**: If `available: 4 nodes` → BIOS is NPS4, requires reconfiguration.

### 1.2 Confirm GPU Visibility

```bash
ssh omni@192.168.3.10 "nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader"
```

**Expected Output**:
```
0, NVIDIA RTX PRO 6000, 98304 MiB
1, NVIDIA RTX 5090, 32768 MiB
```

---

## 2. BIOS Settings Verification

### 2.1 Confirm NPS1 via Redfish (BMC)

```bash
curl -sk -u admin:Aa135610 \
  https://192.168.3.202/redfish/v1/Systems/Self/Bios | \
  jq '.Attributes | {NPS: .CbsDfCmnDramNpsSHP, Performance: .CbsCmnCpuGenCpb}'
```

**Expected Output**:
```json
{
  "NPS": "NPS1",
  "Performance": "Enabled"
}
```

**FAIL Condition**: If `NPS: "NPS4"` or `null` → BIOS reconfiguration required (cold boot after change).

### 2.2 Alternative: Check via SSH (if Redfish unavailable)

```bash
ssh omni@192.168.3.10 "cat /sys/devices/system/node/online"
```

**Expected**: `0` (single node)  
**FAIL**: `0-3` (four nodes = NPS4)

---

## 3. Inference Speed Verification

### 3.1 The Golden Benchmark Command

```bash
ssh omni@192.168.3.10 "docker exec deepseek-v32 \
  llama-cli --model /models/deepseek-v3.2-dq3/Q3_K_M/DeepSeek-V3-0324-Q3_K_M-00001-of-00007.gguf \
  --prompt 'Hello, world!' -n 64 --n-gpu-layers 19 --tensor-split 75,25 --flash-attn 2>&1 | \
  grep -E 'eval.*tok/s'"
```

**Expected Output**:
```
llama_print_timings: prompt eval time = ... (≥20.0 tokens per second)
llama_print_timings:        eval time = ... (≥10.9 tokens per second)
```

**Pass Criteria**:
- Prompt eval: ≥20.0 tok/s
- Generation (eval): ≥10.9 tok/s

**FAIL Conditions**:
| Observed | Likely Cause | Action |
|----------|--------------|--------|
| <7 tok/s | NPS4 active | Check BIOS, reboot |
| ~3.7 tok/s | VMM disabled | Rebuild with bare metal path |
| Model not found | Mount mismatch | Verify docker-compose volumes |

### 3.2 Quick API Latency Test

```bash
time curl -s -X POST http://192.168.3.10:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v3.2","messages":[{"role":"user","content":"Say OK"}],"max_tokens":3}' | jq -r '.choices[0].message.content'
```

**Expected**: Response in <30 seconds, output "OK" or similar.

---

## 4. API Health Checks

### 4.1 Service Health Matrix

```bash
ssh omni@192.168.3.10 '
echo "=== Service Health Matrix ==="
curl -sf http://localhost:8000/health && echo "DeepSeek-V3.2: OK" || echo "DeepSeek-V3.2: FAIL"
curl -sf http://localhost:8002/health && echo "Qwen-Executor: OK" || echo "Qwen-Executor: FAIL"
curl -sf http://localhost:8070/health && echo "MCP-Proxy: OK" || echo "MCP-Proxy: FAIL"
curl -sf http://localhost:8080/health && echo "Agent-Orch: OK" || echo "Agent-Orch: FAIL"
curl -sf http://localhost:6006/health && echo "Phoenix: OK" || echo "Phoenix: FAIL"
curl -sf http://localhost:9090/-/healthy && echo "Prometheus: OK" || echo "Prometheus: FAIL"
curl -sf http://localhost:3000/api/health && echo "Grafana: OK" || echo "Grafana: FAIL"
'
```

**Expected**: All services report OK (some may timeout during initial model load).

### 4.2 MCP Proxy Security Check

```bash
ssh omni@192.168.3.10 '
echo "=== MCP Proxy Security ==="
curl -s http://localhost:8070/health | jq .
curl -s -X POST http://localhost:8070/invoke -d "{\"tool\":\"mcp_shell\"}" -H "Content-Type: application/json" | jq .
'
```

**Expected**:
- Health: `{"status":"ok","policy":"deny"}`
- Shell invoke: `403 Forbidden` or `{"error":"Tool not allowed"}`

---

## 5. Container Status Checks

### 5.1 Docker Compose Status

```bash
ssh omni@192.168.3.10 "cd ~/Protocol_Omni/docker && docker compose -f omni-stack.yaml ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'"
```

**Expected**: All containers show `Up` status.

### 5.2 GPU Memory Allocation

```bash
ssh omni@192.168.3.10 "nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader"
```

**Expected**:
```
0, NVIDIA RTX PRO 6000, ~91000 MiB, 98304 MiB, X%
1, NVIDIA RTX 5090, ~26000 MiB, 32768 MiB, X%
```

**FAIL**: If memory.used is 0 or very low → Model not loaded.

### 5.3 Container Logs (Last Errors)

```bash
ssh omni@192.168.3.10 "docker logs deepseek-v32 2>&1 | tail -20"
```

**Look for**: "model loaded", "warming up", "listening on 0.0.0.0:8000"

---

## 6. Pre-Flight Checklist

Use this before any major operation:

| # | Check | Command | Pass Criteria |
|---|-------|---------|---------------|
| 1 | NUMA Nodes | See Section 1.1 | `available: 1 nodes` |
| 2 | NPS1 BIOS | Redfish query (Section 2.1) | `CbsDfCmnDramNpsSHP: NPS1` |
| 3 | GPU Visible | `nvidia-smi -L` | 2 GPUs listed |
| 4 | DeepSeek Speed | Golden benchmark (Section 3.1) | ≥10.9 tok/s |
| 5 | All Services | Health matrix (Section 4.1) | All OK |
| 6 | GPU Allocation | nvidia-smi memory | 91GB + 26GB used |
| 7 | MCP Security | Deny test (Section 4.2) | Shell blocked |

---

## 7. Troubleshooting Quick Reference

| Symptom | Likely Cause | Command to Verify | Fix |
|---------|--------------|-------------------|-----|
| <7 tok/s | NPS4 active | `numactl --hardware` | BIOS → NPS1, cold boot |
| ~3.7 tok/s | VMM disabled | Check Dockerfile build | Use bare metal build |
| GPU not visible | Driver issue | `nvidia-smi` | Reinstall driver 580.x |
| Model not found | Mount path wrong | `docker exec ... ls /models` | Fix compose volumes |
| Service unhealthy | Container crash | `docker logs <name>` | Check logs, restart |
| MCP allows shell | Allowlist error | Check `config/mcp-allowlist.yaml` | Remove mcp_shell |

---

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-01-24 | Initial verification manual (NPS1, 10.9 t/s baseline) |
