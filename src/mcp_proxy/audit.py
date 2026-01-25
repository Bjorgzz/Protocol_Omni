"""
Audit Logger - Structured logging and Prometheus metrics for MCP tool invocations.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Optional

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

logger = logging.getLogger(__name__)

mcp_invocations_total = Counter(
    "mcp_invocations_total",
    "Total MCP tool invocations",
    ["tool", "method", "status"]
)

mcp_invocation_duration = Histogram(
    "mcp_invocation_duration_seconds",
    "MCP tool invocation duration",
    ["tool", "method"]
)

mcp_denied_total = Counter(
    "mcp_denied_total",
    "Total denied MCP tool invocations",
    ["tool", "method", "reason"]
)


@dataclass
class AuditEvent:
    """Structured audit event for MCP invocations."""
    timestamp: float
    audit_id: str
    tool: str
    method: str
    status: str
    duration_ms: Optional[float] = None
    user_context: Optional[str] = None
    error: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class AuditLogger:
    """
    Logs MCP tool invocations with structured JSON and Prometheus metrics.
    """

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self._file_handler = None

        if log_file:
            self._file_handler = open(log_file, "a")

    def log_invocation(
        self,
        audit_id: str,
        tool: str,
        method: str,
        status: str,
        duration_ms: Optional[float] = None,
        user_context: Optional[str] = None,
        error: Optional[str] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            timestamp=time.time(),
            audit_id=audit_id,
            tool=tool,
            method=method,
            status=status,
            duration_ms=duration_ms,
            user_context=user_context,
            error=error,
        )

        mcp_invocations_total.labels(tool=tool, method=method, status=status).inc()

        if duration_ms:
            mcp_invocation_duration.labels(tool=tool, method=method).observe(duration_ms / 1000)

        log_line = event.to_json()
        logger.info(f"MCP_AUDIT: {log_line}")

        if self._file_handler:
            self._file_handler.write(log_line + "\n")
            self._file_handler.flush()

        return event

    def log_denied(
        self,
        audit_id: str,
        tool: str,
        method: str,
        reason: str,
    ) -> AuditEvent:
        mcp_denied_total.labels(tool=tool, method=method, reason=reason).inc()

        return self.log_invocation(
            audit_id=audit_id,
            tool=tool,
            method=method,
            status="denied",
            error=reason,
        )

    def get_metrics(self) -> bytes:
        return generate_latest()

    def get_metrics_content_type(self) -> str:
        return CONTENT_TYPE_LATEST

    def close(self):
        if self._file_handler:
            self._file_handler.close()
