"""Unit tests for MCP Tool Allowlist."""

import pytest

from mcp_proxy.allowlist import ToolAllowlist, ToolPermission


@pytest.mark.unit
class TestToolPermission:
    """Test ToolPermission dataclass."""

    def test_allows_wildcard_method(self):
        """Wildcard should allow all methods."""
        perm = ToolPermission(name="test_tool", methods={"*"})
        assert perm.allows_method("any_method") is True
        assert perm.allows_method("another_method") is True

    def test_allows_specific_method(self):
        """Specific methods should be checked."""
        perm = ToolPermission(name="test_tool", methods={"execute", "list"})
        assert perm.allows_method("execute") is True
        assert perm.allows_method("list") is True
        assert perm.allows_method("delete") is False

    def test_parse_rate_limit_per_minute(self):
        """Rate limit parsing for per-minute limits."""
        perm = ToolPermission(name="test", rate_limit="60/min")
        count, period = perm.parse_rate_limit()
        assert count == 60
        assert period == 60

    def test_parse_rate_limit_per_second(self):
        """Rate limit parsing for per-second limits."""
        perm = ToolPermission(name="test", rate_limit="10/sec")
        count, period = perm.parse_rate_limit()
        assert count == 10
        assert period == 1

    def test_parse_rate_limit_per_hour(self):
        """Rate limit parsing for per-hour limits."""
        perm = ToolPermission(name="test", rate_limit="1000/hour")
        count, period = perm.parse_rate_limit()
        assert count == 1000
        assert period == 3600


@pytest.mark.unit
class TestToolAllowlist:
    """Test ToolAllowlist class."""

    def test_default_deny_policy(self):
        """Default policy should be deny."""
        allowlist = ToolAllowlist()
        assert allowlist.policy == "deny"
        assert allowlist.is_allowed("any_tool", "any_method") is False

    def test_load_from_yaml(self, tmp_path):
        """Load allowlist from YAML file."""
        config = """
policy: deny
allowed_tools:
  mcp_ssh:
    methods: [ssh_execute, ssh_connect]
    rate_limit: 10/min
    audit: true
  mcp_github:
    methods: ["*"]
    rate_limit: 60/min
"""
        config_file = tmp_path / "allowlist.yaml"
        config_file.write_text(config)

        allowlist = ToolAllowlist(str(config_file))

        assert len(allowlist.allowed_tools) == 2
        assert allowlist.is_allowed("mcp_ssh", "ssh_execute") is True
        assert allowlist.is_allowed("mcp_ssh", "ssh_delete") is False
        assert allowlist.is_allowed("mcp_github", "any_method") is True

    def test_denied_tools_take_precedence(self, tmp_path):
        """Explicitly denied tools should be blocked."""
        config = """
policy: deny
allowed_tools:
  mcp_test:
    methods: ["*"]
denied_tools:
  - mcp_dangerous
"""
        config_file = tmp_path / "allowlist.yaml"
        config_file.write_text(config)

        allowlist = ToolAllowlist(str(config_file))

        assert allowlist.is_allowed("mcp_dangerous", "any") is False
        assert allowlist.is_allowed("mcp_test", "any") is True

    def test_unlisted_tool_denied_by_default(self, tmp_path):
        """Tools not in allowlist should be denied."""
        config = """
policy: deny
allowed_tools:
  mcp_allowed:
    methods: ["*"]
"""
        config_file = tmp_path / "allowlist.yaml"
        config_file.write_text(config)

        allowlist = ToolAllowlist(str(config_file))

        assert allowlist.is_allowed("mcp_unlisted", "method") is False

    def test_missing_config_file(self):
        """Missing config file should result in empty allowlist."""
        allowlist = ToolAllowlist("/nonexistent/path.yaml")
        assert len(allowlist.allowed_tools) == 0
        assert allowlist.is_allowed("any", "method") is False

    def test_get_permission(self, tmp_path):
        """Get permission returns ToolPermission or None."""
        config = """
policy: deny
allowed_tools:
  mcp_test:
    methods: [read, write]
    rate_limit: 30/min
"""
        config_file = tmp_path / "allowlist.yaml"
        config_file.write_text(config)

        allowlist = ToolAllowlist(str(config_file))

        perm = allowlist.get_permission("mcp_test")
        assert perm is not None
        assert perm.name == "mcp_test"
        assert perm.rate_limit == "30/min"

        assert allowlist.get_permission("nonexistent") is None

    def test_list_allowed_tools(self, tmp_path):
        """List allowed tools returns all permitted tool names."""
        config = """
policy: deny
allowed_tools:
  tool_a:
    methods: ["*"]
  tool_b:
    methods: [read]
  tool_c:
    methods: [write]
"""
        config_file = tmp_path / "allowlist.yaml"
        config_file.write_text(config)

        allowlist = ToolAllowlist(str(config_file))
        tools = allowlist.list_allowed_tools()

        assert len(tools) == 3
        assert "tool_a" in tools
        assert "tool_b" in tools
        assert "tool_c" in tools


@pytest.mark.unit
class TestAllowlistSecurityPolicy:
    """Test security policy enforcement."""

    def test_no_implicit_allow(self):
        """Without explicit permission, tools are denied."""
        allowlist = ToolAllowlist()
        assert allowlist.is_allowed("mcp_ssh", "ssh_execute") is False
        assert allowlist.is_allowed("mcp_browser", "navigate") is False

    def test_method_granularity(self, tmp_path):
        """Methods should be checked individually."""
        config = """
policy: deny
allowed_tools:
  mcp_file:
    methods: [read, list]
"""
        config_file = tmp_path / "allowlist.yaml"
        config_file.write_text(config)

        allowlist = ToolAllowlist(str(config_file))

        assert allowlist.is_allowed("mcp_file", "read") is True
        assert allowlist.is_allowed("mcp_file", "list") is True
        assert allowlist.is_allowed("mcp_file", "write") is False
        assert allowlist.is_allowed("mcp_file", "delete") is False
