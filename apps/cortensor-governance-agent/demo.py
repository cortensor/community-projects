#!/usr/bin/env python3
"""Demo: Cortensor Governance Agent

This demo shows how the governance agent connects to the Cortensor network
and analyzes DeFi governance proposals.
"""

import json
import sys
sys.path.insert(0, 'src')

from cortensor_agent import CortensorClient, GovernanceAgent


def demo_mcp_connection():
    """Demo MCP connection to public router."""
    print("=" * 60)
    print("Demo: MCP Connection to Cortensor Public Router")
    print("=" * 60)

    client = CortensorClient(mode="mcp")

    print("\n1. Connecting to Cortensor MCP server...")
    session = client.connect()
    print(f"   Session ID: {session.mcp_session_id}")
    print(f"   Protocol: {session.protocol_version}")

    print("\n2. Listing available tools...")
    tools = client.list_tools()
    for tool in tools:
        print(f"   - {tool['name']}")

    print("\n3. Getting router info...")
    about = client.get_about()
    if about.success:
        inner_data = about.data
        # MCP wraps the response
        if "success" in inner_data:
            print(f"   Backend status: {inner_data.get('success', 'unknown')}")
        else:
            print(f"   Data: {list(inner_data.keys())}")
    else:
        print(f"   Error: {about.error}")

    client.close()
    print("\n   Connection closed.")


def demo_rest_connection():
    """Demo REST API connection to VPS router."""
    print("\n" + "=" * 60)
    print("Demo: REST API Connection to Self-Hosted Router")
    print("=" * 60)

    client = CortensorClient(
        mode="rest",
        rest_endpoint="http://45.32.121.182:5010",
        api_key="hackathon-cortensor-2026"
    )

    print("\n1. Connecting to VPS router...")
    client.connect()
    print("   Connected!")

    print("\n2. Getting router status...")
    status = client.get_status()
    if status.success:
        print(f"   Uptime: {status.data.get('uptime')} seconds")
        print(f"   Active sessions: {status.data.get('active_sessions')}")
        print(f"   Connected miners: {status.data.get('connected_miners')}")
    else:
        print(f"   Error: {status.error}")

    print("\n3. Getting router info...")
    about = client.get_about()
    if about.success:
        print(f"   Router address: {about.data.get('from_address')}")
        print(f"   x402 enabled: {about.data.get('x402_enabled')}")
        print(f"   Endpoints: {len(about.data.get('endpoints', []))}")
    else:
        print(f"   Error: {about.error}")

    print("\n4. Listing available miners...")
    miners = client.get_miners()
    if miners.success:
        stats = miners.data.get("stats", {})
        print(f"   Total miners: {stats.get('total_count', 0)}")
        print(f"   Ephemeral: {stats.get('ephemeral_count', 0)}")
        print(f"   Dedicated: {stats.get('dedicated_count', 0)}")
    else:
        print(f"   Error: {miners.error}")

    client.close()
    print("\n   Connection closed.")


def demo_governance_analysis():
    """Demo governance proposal analysis (mock)."""
    print("\n" + "=" * 60)
    print("Demo: Governance Proposal Analysis")
    print("=" * 60)

    # Sample proposal
    proposal = """
    Proposal: Increase Protocol Fee from 0.3% to 0.5%

    Summary:
    This proposal suggests increasing the protocol fee on all swaps
    from the current 0.3% to 0.5%. The additional revenue would be
    directed to the treasury for future development.

    Rationale:
    - Current fee is below market average
    - Treasury needs funding for security audits
    - Competitors charge 0.5-1.0%

    Timeline:
    - Discussion: 7 days
    - Voting: 5 days
    - Implementation: Immediate after passing
    """

    print("\n1. Proposal to analyze:")
    print("-" * 40)
    print(proposal.strip())
    print("-" * 40)

    print("\n2. Creating governance agent...")
    # Use REST client for demo since public MCP has backend issues
    client = CortensorClient(
        mode="rest",
        rest_endpoint="http://45.32.121.182:5010",
        api_key="hackathon-cortensor-2026"
    )
    agent = GovernanceAgent(client=client)

    print("\n3. Connecting to Cortensor...")
    # Note: This will fail because no miners are connected
    # In production, the session creation would work
    try:
        connected = agent.connect(session_name="governance-demo")
        if connected:
            print("   Connected! Running analysis...")
            result = agent.analyze_proposal(proposal, validate=True)

            print("\n4. Analysis Result:")
            print(f"   Task ID: {result.task_id}")
            print(f"   Validated: {result.validated}")
            if result.validation_score:
                print(f"   Validation Score: {result.validation_score}")
            print(f"\n   Analysis:\n{result.analysis[:500]}...")

            print("\n5. Generating evidence bundle...")
            evidence = agent.generate_evidence_bundle(result)
            print(f"   Bundle ID: {evidence.bundle_id}")
            print(f"   Integrity Hash: {evidence.integrity_hash}")

        else:
            print("   Connection failed (expected - no miners available)")
            print("   In production, sessions are created via dashboard first.")

    except Exception as e:
        print(f"   Error: {e}")
        print("   Note: This is expected when no miners are connected.")
        print("   In production, use dashboard to create sessions first.")

    finally:
        agent.close()


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("   CORTENSOR GOVERNANCE AGENT DEMO")
    print("   Hackathon #4 Submission")
    print("=" * 60)

    # Demo 1: MCP connection
    demo_mcp_connection()

    # Demo 2: REST API connection
    demo_rest_connection()

    # Demo 3: Governance analysis
    demo_governance_analysis()

    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
