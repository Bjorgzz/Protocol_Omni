# k3s Production Deployment

> Zone A/B architecture with Blackwell reset bug mitigation

## Overview

Production deployment uses k3s with split runtime architecture:

- **Zone A** (Brain): Standard Docker for inference (raw metal performance)
- **Zone B** (Hands): gVisor for agents (security isolation)

## 1. Install k3s

```bash
# Install k3s with gVisor support
curl -sfL https://get.k3s.io | sh -s - \
  --disable traefik \
  --disable servicelb \
  --write-kubeconfig-mode 644

# Install gVisor runtime
sudo apt install -y runsc
sudo mv /usr/bin/runsc /usr/local/bin/

# Configure containerd for gVisor
cat <<EOF | sudo tee /var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.gvisor]
  runtime_type = "io.containerd.runsc.v1"
EOF

# Create gVisor RuntimeClass
kubectl apply -f - <<EOF
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: gvisor
EOF

# Restart k3s
sudo systemctl restart k3s
```

## 2. Install NVIDIA Device Plugin

```bash
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/main/deployments/static/nvidia-device-plugin.yml
```

## 3. Deploy Zone A (Inference Engine)

```yaml
# k8s/zone-a-inference.yaml
apiVersion: v1
kind: Pod
metadata:
  name: inference-engine
  namespace: default
  labels:
    zone: brain
    app: ktransformers
spec:
  restartPolicy: OnFailure  # CRITICAL: Prevents Blackwell reset loops
  hostNetwork: true
  
  containers:
  - name: ktransformers
    image: omni/ktransformers:v15
    
    securityContext:
      privileged: true
      capabilities:
        add: ["SYS_RAWIO", "SYS_NICE"]
    
    resources:
      limits:
        nvidia.com/gpu: 2
        memory: "350Gi"
      requests:
        nvidia.com/gpu: 2
        memory: "300Gi"
        cpu: "48"
    
    env:
    - name: NVIDIA_VISIBLE_DEVICES
      value: "all"
    - name: TORCH_CUDA_ARCH_LIST
      value: "9.0a 10.0 12.0"
    - name: ENABLE_DEEPGEMM
      value: "1"
    - name: SGLANG_ENABLE_JIT_DEEPGEMM
      value: "0"
    
    command:
      - /bin/bash
      - -c
      - |
        numactl --cpunodebind=0 --interleave=all \
        python3 -m ktransformers.server.main \
          --model /models/deepseek-v3.2-dq3_k_m \
          --host 0.0.0.0 \
          --port 8000 \
          --gpu_split "90000,30000" \
          --attention-backend triton
    
    ports:
    - containerPort: 8000
      hostPort: 8000
    
    startupProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 300
      periodSeconds: 30
      failureThreshold: 40
    
    livenessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 600
      periodSeconds: 60
      failureThreshold: 10
    
    volumeMounts:
    - name: models
      mountPath: /models
      readOnly: true
    - name: shm
      mountPath: /dev/shm
  
  volumes:
  - name: models
    hostPath:
      path: /nvme/models
  - name: shm
    emptyDir:
      medium: Memory
      sizeLimit: "64Gi"
```

## 4. Deploy Zone B (Agent Orchestrator)

```yaml
# k8s/zone-b-agents.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: agents
---
apiVersion: v1
kind: Pod
metadata:
  name: agent-orchestrator
  namespace: agents
  labels:
    zone: hands
    app: agent
spec:
  runtimeClassName: gvisor  # Sandboxed
  
  containers:
  - name: agent
    image: omni/agent-orchestrator:v15
    
    securityContext:
      privileged: false
      runAsNonRoot: true
      runAsUser: 1000
      capabilities:
        drop: ["ALL"]
      seccompProfile:
        type: RuntimeDefault
    
    env:
    - name: INFERENCE_ENDPOINT
      value: "http://192.168.3.10:8000"
    - name: MEM0_ENDPOINT
      value: "http://192.168.3.10:8050"
    
    ports:
    - containerPort: 8080
    
    resources:
      limits:
        memory: "8Gi"
        cpu: "4"
      requests:
        memory: "4Gi"
        cpu: "2"
```

## 5. Apply Manifests

```bash
kubectl apply -f k8s/zone-a-inference.yaml
kubectl apply -f k8s/zone-b-agents.yaml

# Monitor startup
kubectl logs -f inference-engine

# Verify both zones
kubectl get pods -A
```

## 6. Blackwell Reset Loop Monitoring

```yaml
# k8s/prometheus-alerts.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: blackwell-alerts
spec:
  groups:
  - name: blackwell
    rules:
    - alert: BlackwellResetLoopRisk
      expr: increase(kube_pod_container_status_restarts_total{container="ktransformers"}[10m]) > 2
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "GPU pod restart loop detected"
        action: "kubectl scale deployment inference-engine --replicas=0"
```

## 7. Verification

```bash
# Verify Zone A
kubectl exec inference-engine -- nvidia-smi
curl http://192.168.3.10:8000/health

# Verify Zone B isolation
kubectl exec -n agents agent-orchestrator -- cat /proc/version
# Should show gVisor kernel, not host kernel

# Verify network bridge
kubectl exec -n agents agent-orchestrator -- curl http://192.168.3.10:8000/health

# Verify NUMA
ssh omni@192.168.3.10 "numastat -p \$(pgrep -f ktransformers)"
# Should show memory spread across all 4 nodes
```

## Network Policies

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: zone-b-egress
  namespace: agents
spec:
  podSelector:
    matchLabels:
      zone: hands
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 192.168.3.10/32  # Only inference engine
    ports:
    - port: 8000
    - port: 8050  # Mem0
```

## Related Documentation

- [Zone Security](../architecture/zone-security.md) - Security architecture
- [Troubleshooting](../operations/troubleshooting.md) - Common issues
- [Monitoring](../operations/monitoring.md) - Observability
