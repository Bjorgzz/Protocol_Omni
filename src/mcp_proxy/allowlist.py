"""
Tool Allowlist - YAML-based Default Deny configuration.

All tools are denied unless explicitly listed in the allowlist.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ToolPermission:
    """Permission configuration for a single tool."""
    name: str
    methods: Set[str] = field(default_factory=set)
    rate_limit: str = "60/min"
    audit: bool = True

    def allows_method(self, method: str) -> bool:
        if "*" in self.methods:
            return True
        return method in self.methods

    def parse_rate_limit(self) -> tuple[int, int]:
        count, period = self.rate_limit.split("/")
        period_seconds = {"sec": 1, "min": 60, "hour": 3600}.get(period, 60)
        return int(count), period_seconds


class ToolAllowlist:
    """
    Manages tool permissions with Default Deny policy.

    Example config:
        policy: deny
        allowed_tools:
          mcp_ssh-mcp:
            methods: [ssh_execute, ssh_connect]
            rate_limit: 10/min
    """

    def __init__(self, config_path: Optional[str] = None):
        self.policy = "deny"
        self.allowed_tools: Dict[str, ToolPermission] = {}
        self.denied_tools: Set[str] = set()

        if config_path:
            self.load(config_path)

    def load(self, config_path: str) -> None:
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Allowlist not found: {config_path}, using empty allowlist")
            return

        with open(path) as f:
            config = yaml.safe_load(f)

        self.policy = config.get("policy", "deny")

        for tool_name, tool_config in config.get("allowed_tools", {}).items():
            methods = set(tool_config.get("methods", ["*"]))
            self.allowed_tools[tool_name] = ToolPermission(
                name=tool_name,
                methods=methods,
                rate_limit=tool_config.get("rate_limit", "60/min"),
                audit=tool_config.get("audit", True),
            )

        self.denied_tools = set(config.get("denied_tools", []))

        logger.info(f"Loaded allowlist: {len(self.allowed_tools)} tools permitted")

    def is_allowed(self, tool_name: str, method: str) -> bool:
        if tool_name in self.denied_tools:
            return False

        if self.policy == "deny":
            if tool_name not in self.allowed_tools:
                return False
            return self.allowed_tools[tool_name].allows_method(method)

        return tool_name not in self.denied_tools

    def get_permission(self, tool_name: str) -> Optional[ToolPermission]:
        return self.allowed_tools.get(tool_name)

    def list_allowed_tools(self) -> List[str]:
        return list(self.allowed_tools.keys())
