"""Quick test: Verify MCP connection to Cortensor Router."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cortensor_agent.client import CortensorMCPClient


def main():
    print("Cortensor MCP Connection Test")
    print("=" * 40)

    client = CortensorMCPClient()

    try:
        # Connect
        print("Connecting to Cortensor MCP...")
        session = client.connect()
        print(f"Session ID: {session.mcp_session_id}")
        print(f"Protocol: {session.protocol_version}")

        # List tools
        print("\nAvailable MCP Tools:")
        tools = client.list_tools()
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description'][:50]}...")

        print("\n" + "=" * 40)
        print("MCP Connection: SUCCESS")
        print("=" * 40)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    finally:
        client.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
