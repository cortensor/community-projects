#!/usr/bin/env python3
"""Example: Basic usage of Cortensor MCP Gateway.

This example demonstrates how to use the Cortensor client
in mock mode for development and testing.
"""

import asyncio
import os
import sys

# Add parent directory to path for package imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cortensor_client import CortensorClient, CortensorConfig


async def basic_inference_example():
    """Demonstrate basic inference with mock mode."""
    print("=== Basic Inference Example ===\n")

    # Create config with mock mode enabled
    config = CortensorConfig(
        mock_mode=True,
        session_id=92,
    )

    async with CortensorClient(config) as client:
        # Check health
        is_healthy = await client.health_check()
        print(f"Router Health: {'OK' if is_healthy else 'FAILED'}")
        print(f"Mode: {'Mock' if config.mock_mode else 'Live'}\n")

        # Get available miners
        miners = await client.get_miners()
        print(f"Available Miners ({len(miners)}):")
        for m in miners[:3]:
            print(f"  - {m['id']}: {m['model']}")
        print()

        # Execute inference
        prompt = "Analyze the benefits and risks of decentralized AI inference."
        print(f"Prompt: {prompt}\n")

        response = await client.inference(prompt)

        print("=== Response ===")
        print(f"Task ID: {response.task_id}")
        print(f"Content:\n{response.content}\n")
        print(f"Consensus Score: {response.consensus.score:.2f}")
        print(f"Is Verified: {response.is_verified}")
        print(f"Miners: {response.consensus.agreement_count}/{response.consensus.total_miners}")
        print(f"Total Latency: {response.total_latency_ms:.0f}ms")

        if response.consensus.divergent_miners:
            print(f"Divergent Miners: {response.consensus.divergent_miners}")


async def multi_step_example():
    """Demonstrate multi-step workflow."""
    print("\n=== Multi-Step Workflow Example ===\n")

    config = CortensorConfig(mock_mode=True)

    async with CortensorClient(config) as client:
        # Step 1: Decompose task
        decompose_prompt = """Break down this task into sub-tasks:
Task: Evaluate a governance proposal for a DeFi protocol

Return as JSON with sub_tasks array."""

        print("Step 1: Task Decomposition")
        response1 = await client.inference(decompose_prompt)
        print(f"Consensus: {response1.consensus.score:.2f}")

        # Step 2: Execute analysis
        analysis_prompt = """Analyze the technical feasibility of implementing
on-chain voting with quadratic voting mechanism."""

        print("\nStep 2: Technical Analysis")
        response2 = await client.inference(analysis_prompt)
        print(f"Consensus: {response2.consensus.score:.2f}")

        # Step 3: Risk assessment
        risk_prompt = """Identify potential risks and attack vectors for
a quadratic voting implementation."""

        print("\nStep 3: Risk Assessment")
        response3 = await client.inference(risk_prompt)
        print(f"Consensus: {response3.consensus.score:.2f}")

        # Summary
        print("\n=== Workflow Summary ===")
        print(f"Total Steps: 3")
        print(f"Average Consensus: {(response1.consensus.score + response2.consensus.score + response3.consensus.score) / 3:.2f}")


if __name__ == "__main__":
    print("Cortensor MCP Gateway - Examples\n")
    print("=" * 50)

    asyncio.run(basic_inference_example())
    asyncio.run(multi_step_example())

    print("\n" + "=" * 50)
    print("Examples completed successfully!")
