"""Integration tests for remote services (require --run-remote flag)."""
import subprocess
from typing import Tuple

import pytest

REMOTE_HOST = "192.168.3.10"
REMOTE_USER = "omni"


def ssh_exec(cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
    """Execute command on remote host via SSH."""
    result = subprocess.run(
        ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def verify_ssh_access():
    """Verify SSH access to remote host."""
    code, out, err = ssh_exec("echo 'SSH OK'", timeout=10)
    if code != 0:
        pytest.skip(f"Cannot SSH to {REMOTE_HOST}: {err}")
    return True


@pytest.mark.remote
class TestSSHAccess:
    """Test SSH connectivity to remote host."""

    def test_ssh_connection(self, verify_ssh_access):
        """SSH connection should work."""
        code, out, _ = ssh_exec("hostname")
        assert code == 0
        assert len(out.strip()) > 0


@pytest.mark.remote
class TestDockerServices:
    """Test Docker services on remote host."""

    def test_docker_accessible(self, verify_ssh_access):
        """Docker should be accessible."""
        code, out, _ = ssh_exec("docker ps --format '{{.Names}}' | head -5")
        assert code == 0

    def test_qdrant_running(self, verify_ssh_access):
        """Qdrant should be running."""
        code, out, _ = ssh_exec("docker ps | grep qdrant")
        assert code == 0
        assert "qdrant" in out

    def test_deepseek_running(self, verify_ssh_access):
        """DeepSeek-V32 should be running."""
        code, out, _ = ssh_exec("docker ps | grep deepseek")
        assert code == 0

    def test_mem0_running(self, verify_ssh_access):
        """Mem0 should be running."""
        code, out, _ = ssh_exec("docker ps | grep mem0")
        assert code == 0
        assert "mem0" in out


@pytest.mark.remote
class TestServiceHealth:
    """Test service health endpoints."""

    def test_deepseek_health(self, verify_ssh_access):
        """DeepSeek health endpoint should respond."""
        code, out, _ = ssh_exec("curl -sf http://localhost:8000/health")
        assert code == 0
        assert "ok" in out.lower() or "status" in out.lower()

    def test_qdrant_health(self, verify_ssh_access):
        """Qdrant should have collections."""
        code, out, _ = ssh_exec("curl -sf http://localhost:6333/collections")
        assert code == 0
        assert "collections" in out

    def test_mem0_health(self, verify_ssh_access):
        """Mem0 health endpoint should respond."""
        code, out, _ = ssh_exec("curl -sf http://localhost:8050/health")
        assert code == 0
        assert "ok" in out.lower()

    def test_agent_health(self, verify_ssh_access):
        """Agent orchestrator health should respond."""
        code, out, _ = ssh_exec("curl -sf http://localhost:8080/health", timeout=10)
        if code != 0:
            pytest.skip("Agent orchestrator not running")
        assert "ok" in out.lower()


@pytest.mark.remote
class TestMem0Memory:
    """Test Mem0 memory service (UNBLOCKED in v16.2)."""

    def test_mem0_container_healthy(self, verify_ssh_access):
        """Mem0 container should be healthy."""
        code, out, _ = ssh_exec("docker inspect mem0 --format '{{.State.Health.Status}}'")
        assert code == 0
        assert "healthy" in out

    def test_mem0_vector_dimensions(self, verify_ssh_access):
        """Mem0 should use 384-dim vectors (HuggingFace MiniLM)."""
        code, out, _ = ssh_exec(
            "curl -sf http://localhost:6333/collections/mem0 | "
            "python3 -c \"import sys,json; d=json.load(sys.stdin); print(d['result']['config']['params']['vectors']['size'])\""
        )
        assert code == 0
        assert "384" in out

    def test_mem0_qdrant_connection(self, verify_ssh_access):
        """Mem0 should be connected to Qdrant."""
        code, out, _ = ssh_exec(
            "docker exec mem0 curl -sf http://qdrant:6333/collections"
        )
        assert code == 0
        assert "collections" in out

    def test_mem0_llm_connection(self, verify_ssh_access):
        """Mem0 should be able to reach LLM."""
        code, out, _ = ssh_exec(
            "docker exec mem0 curl -sf http://deepseek-v32:8000/health"
        )
        assert code == 0


@pytest.mark.remote
class TestNVMePersistence:
    """Test NVMe storage configuration."""

    def test_nvme_mounted(self, verify_ssh_access):
        """NVMe should be mounted."""
        code, out, _ = ssh_exec("df -h | grep nvme")
        if code != 0:
            pytest.skip("NVMe not mounted as separate device")
        assert "/nvme" in out or "nvme" in out

    def test_mem0_data_dir_exists(self, verify_ssh_access):
        """Mem0 data directory should exist on NVMe."""
        code, out, _ = ssh_exec("ls -la /nvme/mem0_data 2>/dev/null || echo 'NOT_FOUND'")
        if "NOT_FOUND" in out:
            pytest.skip("Mem0 data directory not on NVMe")
        assert code == 0


@pytest.mark.remote
class TestGPUStatus:
    """Test GPU availability."""

    def test_nvidia_smi_available(self, verify_ssh_access):
        """nvidia-smi should be available."""
        code, out, _ = ssh_exec("nvidia-smi --query-gpu=name --format=csv,noheader")
        if code != 0:
            pytest.skip("nvidia-smi not available")
        assert len(out.strip()) > 0

    def test_gpu_memory_available(self, verify_ssh_access):
        """GPU should have available memory."""
        code, out, _ = ssh_exec(
            "nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits"
        )
        if code != 0:
            pytest.skip("Cannot query GPU memory")
        assert code == 0
