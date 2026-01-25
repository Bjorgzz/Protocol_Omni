# Archived Kubernetes Workloads

These are Kubernetes deployment manifests for AI model inference from v13.x.

**Superseded by:** Docker Compose stacks in `../docker/`

## Files

| File | Purpose | v14.0 Equivalent |
|------|---------|------------------|
| `bleeding-edge-deploy.yaml` | Dev inference server | `docker/omni-stack.yaml` |
| `deepseek-70b-int4.yaml` | DeepSeek 70B | Upgraded to DeepSeek-R1 671B |
| `deepseek-stack.yaml` | Full DeepSeek stack | `docker/deepseek-r1-eagle.yaml` |
| `flux-stack.yaml` | Image generation | Not in v14.0 scope |

## Reason for Archive

v14.0 uses Docker Compose instead of Kubernetes for orchestration.
