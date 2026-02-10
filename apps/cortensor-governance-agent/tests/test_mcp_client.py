"""Test: Verify MCP connection to Cortensor Router.

This test verifies that the MCP client can:
1. Connect to Cortensor MCP server
2. List available tools
3. Call tools (even if backend returns errors)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cortensor_agent.client import CortensorMCPClient


def test_mcp_connection():
    """Test basic MCP connection."""
    client = CortensorMCPClient()

    # Test connect
    session = client.connect()
    assert session is not None
    assert session.mcp_session_id is not None
    print(f"Connected: {session.mcp_session_id}")

    client.close()
    print("test_mcp_connection PASSED")


def test_list_tools():
    """Test listing MCP tools."""
    client = CortensorMCPClient()
    client.connect()

    tools = client.list_tools()
    assert len(tools) > 0

    tool_names = [t["name"] for t in tools]
    print(f"Tools: {tool_names}")

    # Verify expected tools exist
    assert "cortensor_completions" in tool_names
    assert "cortensor_validate" in tool_names
    assert "cortensor_create_session" in tool_names

    client.close()
    print("test_list_tools PASSED")


def test_call_tool():
    """Test calling an MCP tool."""
    client = CortensorMCPClient()
    client.connect()

    # Call a tool - even if backend returns error, MCP layer should work
    result = client.call_tool("cortensor_ping", {})

    # Result should be returned (success=True means MCP call succeeded)
    assert result is not None
    print(f"Ping result: {result}")

    client.close()
    print("test_call_tool PASSED")


if __name__ == "__main__":
    print("=" * 50)
    print("Cortensor MCP Client Tests")
    print("=" * 50)

    test_mcp_connection()
    test_list_tools()
    test_call_tool()

    print()
    print("All tests passed!")
