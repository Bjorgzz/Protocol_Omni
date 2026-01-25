"""
MCP Security Gateway - Default Deny proxy for MCP tool invocations.

Protocol OMNI v15.1 - Concrete Bunker Doctrine

All MCP tool calls must route through this gateway.
Tools not in the allowlist are denied with 403 Forbidden.
"""

import logging
import os
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from .allowlist import ToolAllowlist
from .audit import AuditLogger

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("omni.mcp_proxy")
    TRACING_ENABLED = True
except ImportError:
    tracer = None
    TRACING_ENABLED = False

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ToolInvokeRequest(BaseModel):
    """Request to invoke an MCP tool."""
    tool: str
    method: str
    arguments: Dict[str, Any] = {}
    timeout_ms: int = 30000


class ToolInvokeResponse(BaseModel):
    """Response from MCP tool invocation."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    audit_id: str
    duration_ms: float


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds

        self.requests[key] = [t for t in self.requests[key] if t > cutoff]

        if len(self.requests[key]) >= limit:
            return False

        self.requests[key].append(now)
        return True


allowlist: Optional[ToolAllowlist] = None
audit_logger: Optional[AuditLogger] = None
rate_limiter: Optional[RateLimiter] = None
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global allowlist, audit_logger, rate_limiter, http_client

    config_path = os.getenv("ALLOWLIST_PATH", "/config/mcp-allowlist.yaml")
    allowlist = ToolAllowlist(config_path)
    audit_logger = AuditLogger()
    rate_limiter = RateLimiter()
    http_client = httpx.AsyncClient(timeout=60.0)

    logger.info("MCP Security Gateway initialized")
    logger.info(f"Policy: {allowlist.policy}")
    logger.info(f"Allowed tools: {allowlist.list_allowed_tools()}")

    yield

    if http_client:
        await http_client.aclose()
    if audit_logger:
        audit_logger.close()


app = FastAPI(
    title="MCP Security Gateway",
    description="Protocol OMNI v15.1 - Default Deny MCP Proxy",
    version="15.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "policy": allowlist.policy if allowlist else "unknown"}


@app.get("/metrics")
async def metrics():
    if not audit_logger:
        raise HTTPException(status_code=503, detail="Not initialized")
    return Response(
        content=audit_logger.get_metrics(),
        media_type=audit_logger.get_metrics_content_type(),
    )


@app.get("/allowed-tools")
async def list_allowed_tools():
    if not allowlist:
        raise HTTPException(status_code=503, detail="Not initialized")
    return {"tools": allowlist.list_allowed_tools()}


@app.post("/invoke", response_model=ToolInvokeResponse)
async def invoke_tool(request: ToolInvokeRequest):
    if not allowlist or not audit_logger or not rate_limiter:
        raise HTTPException(status_code=503, detail="Not initialized")

    audit_id = f"mcp-{uuid.uuid4().hex[:12]}"
    start_time = time.time()

    span = None
    if TRACING_ENABLED and tracer:
        span = tracer.start_span("mcp_tool_invoke")
        span.set_attribute("tool", request.tool)
        span.set_attribute("method", request.method)

    try:
        if not allowlist.is_allowed(request.tool, request.method):
            audit_logger.log_denied(
                audit_id=audit_id,
                tool=request.tool,
                method=request.method,
                reason="not_in_allowlist",
            )
            logger.warning(f"DENIED: {request.tool}.{request.method} - not in allowlist")
            if span:
                span.set_attribute("allowed", False)
                span.set_attribute("reason", "not_in_allowlist")
                span.end()
            raise HTTPException(
                status_code=403,
                detail=f"Tool '{request.tool}' method '{request.method}' not permitted",
            )

        if span:
            span.set_attribute("allowed", True)

        permission = allowlist.get_permission(request.tool)
        if permission:
            limit, window = permission.parse_rate_limit()
            rate_key = f"{request.tool}:{request.method}"
            if not rate_limiter.is_allowed(rate_key, limit, window):
                audit_logger.log_denied(
                    audit_id=audit_id,
                    tool=request.tool,
                    method=request.method,
                    reason="rate_limited",
                )
                logger.warning(f"RATE LIMITED: {request.tool}.{request.method}")
                if span:
                    span.set_attribute("rate_limited", True)
                    span.end()
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded for '{request.tool}' ({permission.rate_limit})",
                )

        result = await _forward_to_mcp_server(request)
        duration_ms = (time.time() - start_time) * 1000

        if span:
            span.set_attribute("duration_ms", duration_ms)
            span.set_attribute("success", True)

        if permission and permission.audit:
            audit_logger.log_invocation(
                audit_id=audit_id,
                tool=request.tool,
                method=request.method,
                status="success",
                duration_ms=duration_ms,
            )

        if span:
            span.end()

        return ToolInvokeResponse(
            success=True,
            result=result,
            audit_id=audit_id,
            duration_ms=duration_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = str(e)

        if span:
            span.set_attribute("success", False)
            span.set_attribute("error", error_msg)
            span.set_attribute("duration_ms", duration_ms)
            span.end()

        audit_logger.log_invocation(
            audit_id=audit_id,
            tool=request.tool,
            method=request.method,
            status="error",
            duration_ms=duration_ms,
            error=error_msg,
        )

        return ToolInvokeResponse(
            success=False,
            error=error_msg,
            audit_id=audit_id,
            duration_ms=duration_ms,
        )


async def _forward_to_mcp_server(request: ToolInvokeRequest) -> Any:
    """
    Forward the request to the actual MCP server.

    Note: In a full implementation, this would discover and connect to
    the appropriate MCP server. For now, we return a placeholder.
    """
    logger.info(f"Forwarding to MCP: {request.tool}.{request.method}")
    return {"forwarded": True, "tool": request.tool, "method": request.method}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8070)
