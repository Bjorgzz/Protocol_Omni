"""
Sovereign Status Tool - Protocol OMNI v16.3.3

Self-introspection tool for the Agent Orchestrator.
Queries GPU metrics (DCGM) and Memory layer (Mem0) to report system state.
"""

import re
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DCGM_ENDPOINT = "http://dcgm-exporter:9400/metrics"
MEM0_ENDPOINT = "http://mem0:8000"
TIMEOUT = 10.0


def _parse_prometheus_metric(text: str, metric_name: str) -> List[Dict[str, Any]]:
    """Parse Prometheus text format and extract metric values with labels."""
    results = []
    pattern = rf'^{metric_name}\{{([^}}]+)\}}\s+(\S+)'
    
    for line in text.split('\n'):
        match = re.match(pattern, line)
        if match:
            labels_str, value = match.groups()
            labels = {}
            for label in labels_str.split(','):
                if '=' in label:
                    key, val = label.split('=', 1)
                    labels[key] = val.strip('"')
            try:
                results.append({
                    "labels": labels,
                    "value": float(value)
                })
            except ValueError:
                pass
    return results


def get_gpu_status() -> Dict[str, Any]:
    """
    Query GPU status from DCGM Exporter.
    
    Returns:
        Dict with GPU metrics or error status
    """
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(DCGM_ENDPOINT)
            response.raise_for_status()
            metrics_text = response.text
        
        gpus = []
        vram_used_metrics = _parse_prometheus_metric(metrics_text, "DCGM_FI_DEV_FB_USED")
        vram_free_metrics = _parse_prometheus_metric(metrics_text, "DCGM_FI_DEV_FB_FREE")
        util_metrics = _parse_prometheus_metric(metrics_text, "DCGM_FI_DEV_GPU_UTIL")
        temp_metrics = _parse_prometheus_metric(metrics_text, "DCGM_FI_DEV_GPU_TEMP")
        power_metrics = _parse_prometheus_metric(metrics_text, "DCGM_FI_DEV_POWER_USAGE")
        
        gpu_map = {}
        for metric in vram_used_metrics:
            gpu_id = metric["labels"].get("gpu", "unknown")
            if gpu_id not in gpu_map:
                gpu_map[gpu_id] = {"id": gpu_id, "name": metric["labels"].get("modelName", "Unknown GPU")}
            gpu_map[gpu_id]["vram_used_mb"] = metric["value"]
        
        for metric in vram_free_metrics:
            gpu_id = metric["labels"].get("gpu", "unknown")
            if gpu_id in gpu_map:
                gpu_map[gpu_id]["vram_free_mb"] = metric["value"]
        
        for metric in util_metrics:
            gpu_id = metric["labels"].get("gpu", "unknown")
            if gpu_id in gpu_map:
                gpu_map[gpu_id]["utilization_pct"] = metric["value"]
        
        for metric in temp_metrics:
            gpu_id = metric["labels"].get("gpu", "unknown")
            if gpu_id in gpu_map:
                gpu_map[gpu_id]["temperature_c"] = metric["value"]
        
        for metric in power_metrics:
            gpu_id = metric["labels"].get("gpu", "unknown")
            if gpu_id in gpu_map:
                gpu_map[gpu_id]["power_w"] = metric["value"]
        
        for gpu_id, gpu_data in gpu_map.items():
            used = gpu_data.get("vram_used_mb", 0)
            free = gpu_data.get("vram_free_mb", 0)
            total = used + free
            gpu_data["vram_total_mb"] = total
            gpu_data["vram_used_gb"] = round(used / 1024, 1)
            gpu_data["vram_free_gb"] = round(free / 1024, 1)
            gpu_data["vram_total_gb"] = round(total / 1024, 1)
            gpus.append(gpu_data)
        
        total_used = sum(g.get("vram_used_mb", 0) for g in gpus)
        total_capacity = sum(g.get("vram_total_mb", 0) for g in gpus)
        
        return {
            "status": "ok",
            "gpus": gpus,
            "summary": {
                "total_vram_used_gb": round(total_used / 1024, 1),
                "total_vram_capacity_gb": round(total_capacity / 1024, 1),
                "utilization_pct": round((total_used / total_capacity * 100) if total_capacity > 0 else 0, 1),
            }
        }
        
    except httpx.RequestError as e:
        logger.error(f"DCGM request failed: {e}")
        return {"status": "error", "error": f"DCGM unreachable: {e}", "gpus": []}
    except Exception as e:
        logger.error(f"GPU status failed: {e}")
        return {"status": "error", "error": str(e), "gpus": []}


def get_memory_status() -> Dict[str, Any]:
    """
    Query memory layer status from Mem0.
    
    Returns:
        Dict with memory count or error status
    """
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(f"{MEM0_ENDPOINT}/v1/memories/", params={"user_id": "system", "limit": 1})
            
            if response.status_code == 200:
                data = response.json()
                memory_count = data.get("count", len(data.get("memories", [])))
                return {
                    "status": "ok",
                    "memory_count": memory_count,
                }
            else:
                health = client.get(f"{MEM0_ENDPOINT}/health")
                if health.status_code == 200:
                    return {
                        "status": "ok",
                        "memory_count": 0,
                        "note": "Mem0 healthy but no memories found"
                    }
                return {"status": "degraded", "memory_count": 0, "error": f"Mem0 HTTP {response.status_code}"}
                
    except httpx.RequestError as e:
        logger.error(f"Mem0 request failed: {e}")
        return {"status": "error", "memory_count": 0, "error": f"Mem0 unreachable: {e}"}
    except Exception as e:
        logger.error(f"Memory status failed: {e}")
        return {"status": "error", "memory_count": 0, "error": str(e)}


def get_sovereign_status() -> Dict[str, Any]:
    """
    Get complete sovereign system status.
    
    Returns a summary of:
    - GPU metrics (VRAM, utilization, temperature, power)
    - Memory layer status (Mem0 memory count)
    """
    gpu_status = get_gpu_status()
    memory_status = get_memory_status()
    
    overall_status = "healthy"
    if gpu_status.get("status") != "ok" or memory_status.get("status") != "ok":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "body": gpu_status,
        "mind": memory_status,
        "summary": {
            "vram": f"{gpu_status.get('summary', {}).get('total_vram_used_gb', 0):.1f}GB / {gpu_status.get('summary', {}).get('total_vram_capacity_gb', 0):.1f}GB",
            "memories": memory_status.get("memory_count", 0),
            "gpu_count": len(gpu_status.get("gpus", [])),
        }
    }


def format_status_for_agent(status: Dict[str, Any]) -> str:
    """
    Format status dict into natural language for agent response.
    
    This is what gets returned when the agent is asked about VRAM/status.
    """
    summary = status.get("summary", {})
    body = status.get("body", {})
    mind = status.get("mind", {})
    
    lines = [
        f"**System Status: {status.get('status', 'unknown').upper()}**",
        "",
        f"**VRAM:** {summary.get('vram', 'Unknown')} ({body.get('summary', {}).get('utilization_pct', 0):.1f}% utilized)",
        f"**GPUs:** {summary.get('gpu_count', 0)} active",
    ]
    
    for gpu in body.get("gpus", []):
        lines.append(
            f"  - GPU {gpu.get('id', '?')}: {gpu.get('vram_used_gb', 0):.1f}GB / {gpu.get('vram_total_gb', 0):.1f}GB "
            f"| {gpu.get('temperature_c', 0):.0f}°C | {gpu.get('power_w', 0):.0f}W"
        )
    
    lines.extend([
        "",
        f"**Memories:** {summary.get('memories', 0)} stored in Mem0",
        "",
        "All systems operational." if status.get("status") == "healthy" else "Some systems degraded - check logs."
    ])
    
    return "\n".join(lines)
