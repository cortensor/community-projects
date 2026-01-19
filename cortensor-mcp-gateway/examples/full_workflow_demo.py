#!/usr/bin/env python3
"""Full workflow demo: Agent Swarm + Evidence Bundle generation.

Demonstrates the complete Cortensor MCP Gateway capabilities:
1. Multi-agent coordination (Planner -> Executor -> Validator -> Auditor)
2. PoI consensus verification
3. Evidence bundle generation with cryptographic integrity
"""

import asyncio
import os
import sys

# Add parent directory to path for package imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cortensor_client import CortensorClient, CortensorConfig
from src.agent_swarm import AgentCoordinator


async def run_full_workflow():
    """Execute a complete verifiable AI workflow."""
    print("=" * 60)
    print("Cortensor MCP Gateway - Full Workflow Demo")
    print("=" * 60)
    print()

    config = CortensorConfig(mock_mode=True)

    async with CortensorClient(config) as client:
        coordinator = AgentCoordinator(client)

        # Task: Analyze a governance proposal
        task = """Evaluate the following DeFi governance proposal:

Proposal: Implement quadratic voting for protocol upgrades
- Each token holder gets votes proportional to sqrt(tokens)
- Minimum 1000 tokens required to participate
- 7-day voting period with 3-day timelock

Provide analysis covering:
1. Technical feasibility
2. Economic implications
3. Security considerations
4. Recommendation"""

        print("Task Description:")
        print("-" * 40)
        print(task)
        print("-" * 40)
        print()

        # Execute the full workflow
        print("Executing workflow...")
        print()

        result = await coordinator.execute_workflow(
            task_description=task,
            skip_planning=False,
        )

        # Display results
        print("=" * 60)
        print("WORKFLOW RESULTS")
        print("=" * 60)
        print()

        print(f"Workflow ID: {result.workflow_id}")
        print(f"Verified: {result.is_verified}")
        print(f"Consensus Score: {result.consensus_score:.2f}")
        print(f"Execution Time: {result.execution_time_ms:.0f}ms")
        print()

        print("Execution Steps:")
        for i, step in enumerate(result.steps, 1):
            print(f"  {i}. {step['step']}: {step['status']}")
            if 'consensus_score' in step:
                print(f"     Consensus: {step['consensus_score']:.2f}")
        print()

        print("Final Output:")
        print("-" * 40)
        print(result.final_output[:500] + "..." if len(result.final_output) > 500 else result.final_output)
        print("-" * 40)
        print()

        # Retrieve evidence bundle
        if result.evidence_bundle_id:
            bundle = coordinator.get_evidence_bundle(result.evidence_bundle_id)
            if bundle:
                print("=" * 60)
                print("EVIDENCE BUNDLE")
                print("=" * 60)
                print()
                print(f"Bundle ID: {bundle.bundle_id}")
                print(f"Task ID: {bundle.task_id}")
                print(f"Created: {bundle.created_at.isoformat()}")
                print(f"Integrity Hash: {bundle.compute_hash()[:32]}...")
                print()

                print("Miner Responses Summary:")
                for mr in bundle.miner_responses[:3]:
                    print(f"  - {mr.get('miner_id', 'unknown')}: {mr.get('model', 'unknown')}")
                print()

                print("Consensus Info:")
                print(f"  Score: {bundle.consensus_info.get('average_score', 0):.2f}")
                print()

                print("Validation Result:")
                validation = bundle.validation_result.get('validation', {})
                print(f"  Valid: {validation.get('is_valid', False)}")
                print(f"  Consensus OK: {validation.get('consensus_ok', False)}")
                print()

                # Save evidence bundle to file
                bundle_path = os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    f"evidence_bundle_{bundle.bundle_id}.json"
                )
                with open(bundle_path, "w") as f:
                    f.write(bundle.to_json())
                print(f"Evidence bundle saved to: {bundle_path}")

        print()
        print("=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)


async def demo_mcp_tools():
    """Demonstrate MCP tool capabilities."""
    print()
    print("=" * 60)
    print("MCP Tools Demo")
    print("=" * 60)
    print()

    # Import MCP server components
    from src.mcp_server.server import CortensorMCPServer

    config = CortensorConfig(mock_mode=True)
    server = CortensorMCPServer(config)

    async with CortensorClient(config) as client:
        server.client = client

        # Demo: cortensor_inference
        print("1. cortensor_inference")
        print("-" * 40)
        result = await server._handle_inference({
            "prompt": "What are the key benefits of decentralized AI?",
            "consensus_threshold": 0.66,
        })
        print(result.content[0].text[:300] + "...")
        print()

        # Demo: cortensor_miners
        print("2. cortensor_miners")
        print("-" * 40)
        result = await server._handle_miners()
        print(result.content[0].text[:200] + "...")
        print()

        # Demo: cortensor_health
        print("3. cortensor_health")
        print("-" * 40)
        result = await server._handle_health()
        print(result.content[0].text)
        print()

    print("MCP tools demo completed!")


if __name__ == "__main__":
    print()
    asyncio.run(run_full_workflow())
    asyncio.run(demo_mcp_tools())
