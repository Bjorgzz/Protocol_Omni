# Troubleshooting Guide

> Common issues and solutions for Protocol OMNI

## Quick Diagnosis

```bash
# System overview
docker compose -f docker/omni-stack.yaml ps
nvidia-smi
htop

# Check for errors
docker compose -f docker/omni-stack.yaml logs --tail 50 | grep -i error
```

## GPU Issues

### GPU Not Visible in Container

**Symptom**: Container can't see GPUs

**Solution**:
```bash
# Verify host GPU
nvidia-smi

# Test container GPU access
docker run --rm --gpus all nvidia/cuda:13.0.1-base-ubi9 nvidia-smi

# Reconfigure toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### PCIe Stuck at Gen1 (2.5GT/s)

**Symptom**: 12.8x slower bandwidth than expected

**Diagnosis**:
```bash
nvidia-smi --query-gpu=name,pcie.link.gen.current,pcie.link.width.current --format=csv
# Expected: 5, 16 (Gen5 x16)
# Problem: 1, 16 (Gen1 x16)
```

**Solution**:
1. Access BIOS via BMC (https://192.168.3.202)
2. Navigate to AMD CBS → NBIO → PCIe
3. Set `CbsCmnEarlyLinkSpeedSHP` → GEN5
4. Cold reboot (power cycle, not restart)

### DeepGEMM Build Error

**Symptom**: SM 12.0 compilation fails

**Solution**: Consumer Blackwell (SM 12.0) doesn't support DeepGEMM GPU JIT:
```yaml
env:
- name: ENABLE_DEEPGEMM
  value: "1"  # CPU kernels still work
- name: SGLANG_ENABLE_JIT_DEEPGEMM
  value: "0"  # Disable GPU JIT
```

### Flash Attention Not Supported

**Symptom**: Flash Attention fails on Blackwell

**Solution**: Use Triton backend:
```bash
--attention-backend triton
```

## Memory Issues

### NUMA OOM (Out of Memory)

**Symptom**: Process killed during model load

**Diagnosis**:
```bash
numastat -p $(pgrep -f ktransformers)
# If all memory on Node 0: OOM risk
```

**Cause**: Using `--membind=0` limits to 96GB

**Solution**:
```bash
# Wrong
numactl --cpunodebind=0 --membind=0  # 96GB cap

# Correct
numactl --cpunodebind=0 --interleave=all  # 384GB capacity
```

### Container OOM Killed

**Symptom**: Container killed by kernel

**Solution**:
```yaml
# Increase memory limits
deploy:
  resources:
    limits:
      memory: 350G
```

### Tensor Parallel OOM

**Symptom**: OOM with TP=2

**Cause**: Unequal GPU sizes (96GB + 32GB)

**Solution**: Don't use tensor parallel with unequal GPUs. Use `--gpu_split` instead:
```bash
--gpu_split "90000,30000"
```

## Network Issues

### Zone B Can't Reach Zone A

**Symptom**:
```
ConnectionRefusedError: [Errno 111] Connection refused to http://localhost:8000
```

**Cause**: gVisor's localhost is container loopback, not host

**Solution**:

Zone A - Bind to all interfaces:
```bash
--host 0.0.0.0
```

Zone B - Target host IP:
```yaml
env:
- name: INFERENCE_ENDPOINT
  value: "http://192.168.3.10:8000"  # NOT localhost
```

## Model Issues

### Model Load Timeout

**Symptom**: Model doesn't load within timeout

**Cause**: 281GB model takes 3-5 minutes to load

**Solution**:
```yaml
startupProbe:
  initialDelaySeconds: 300  # 5 min
  failureThreshold: 40      # 25 min total
```

### Model Load Fails

**Debug**:
```bash
# Check logs
docker compose -f docker/omni-stack.yaml logs deepseek-v32

# Check GPU memory
nvidia-smi

# Enter container
docker exec -it deepseek-v32 bash
```

### CUDA Version Mismatch

**Symptom**:
```
RuntimeError: The detected CUDA version mismatches...
```

**Solution**: Use PyTorch cu130 nightly:
```bash
pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu130
```

## k3s Issues

### Blackwell Reset Loop

**Symptom**: GPU pod restarts repeatedly, then host freezes

**Cause**: Consumer Blackwell FLR (Function Level Reset) bug

**Prevention**:
```yaml
restartPolicy: OnFailure  # NOT Always

startupProbe:
  initialDelaySeconds: 300
  failureThreshold: 40

livenessProbe:
  initialDelaySeconds: 600
  failureThreshold: 10
```

**Monitoring**:
```yaml
- alert: BlackwellResetLoopRisk
  expr: increase(kube_pod_container_status_restarts_total{container="ktransformers"}[10m]) > 2
```

**Emergency**:
```bash
kubectl scale deployment inference-engine --replicas=0
```

### gVisor Not Working

**Symptom**: Pod fails to start with gVisor

**Diagnosis**:
```bash
kubectl describe pod agent-orchestrator -n agents
```

**Solution**:
```bash
# Verify gVisor installed
which runsc

# Check RuntimeClass
kubectl get runtimeclass gvisor
```

## Performance Issues

### Low Inference Speed

**Symptom**: <5 tok/s instead of ~20 tok/s

**Possible Causes**:

1. **DeepGEMM disabled**:
   ```bash
   docker logs inference-engine 2>&1 | grep -i deepgemm
   # Should show "DeepGEMM enabled"
   ```

2. **NUMA misconfigured**:
   ```bash
   numastat -p $(pgrep -f ktransformers)
   # Memory should spread across all 4 nodes
   ```

3. **PCIe Gen1**:
   ```bash
   nvidia-smi --query-gpu=pcie.link.gen.current --format=csv
   # Should be 5 (Gen5)
   ```

## Full Stack Restart

After host reboot:

```bash
# 1. Verify GPU
nvidia-smi

# 2. Start stack
cd ~/Protocol_Omni/docker
docker compose -f omni-stack.yaml --profile full up -d

# 3. Monitor (3-5 min)
docker compose -f omni-stack.yaml logs -f deepseek-v32

# 4. Verify
curl http://localhost:8000/health
curl http://localhost:8002/health
```

## Getting Help

1. Check logs: `docker compose logs -f <service>`
2. Check [AGENTS.md](../../AGENTS.md) for operational doctrine
3. Query ByteRover: `brv query "How to fix <issue>"`
4. Review [Architecture](../architecture/overview.md)
