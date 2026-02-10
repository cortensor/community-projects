#!/usr/bin/env python3
"""Demo: Cortensor Delegate-Validate Workflow

This demo demonstrates the competitive hackathon submission pattern:
1. Delegate tasks to Cortensor miners via /delegate endpoint
2. Validate results via /validate endpoint (PoI + PoUW)
3. Export session log for submission

Usage:
    CORTENSOR_MOCK_MODE=true python examples/delegate_validate_demo.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cortensor_client import CortensorClient, CortensorConfig


async def run_delegate_validate_workflow():
    """Run the full delegate-validate workflow."""

    print("=" * 70)
    print("CORTENSOR DELEGATE-VALIDATE WORKFLOW DEMO")
    print("Hackathon #4 Competitive Submission Pattern")
    print("=" * 70)

    # Configure client
    config = CortensorConfig.from_env()
    print(f"\nConfiguration:")
    print(f"  Router URL: {config.router_url}")
    print(f"  Session ID: {config.session_id}")
    print(f"  Mock Mode: {config.mock_mode}")
    print(f"  Timeout: {config.timeout}s")

    async with CortensorClient(config) as client:

        # ========================================
        # STEP 1: Delegate Task to Miners
        # ========================================
        print("\n" + "=" * 70)
        print("STEP 1: DELEGATE - Submit task to Cortensor miners")
        print("=" * 70)

        task_prompt = """
Analyze the following DeFi governance proposal and provide a structured assessment:

Proposal: Implement quadratic voting for protocol upgrades
- Each token holder gets votes proportional to sqrt(tokens)
- Minimum 1000 tokens required to participate
- 7-day voting period with 3-day timelock

Provide your analysis in the following format:
1. Summary (2-3 sentences)
2. Key Benefits (bullet points)
3. Potential Risks (bullet points)
4. Recommendation (approve/reject with reasoning)
"""

        print(f"\nTask Prompt:\n{'-' * 40}")
        print(task_prompt.strip())
        print(f"{'-' * 40}")

        print("\nDelegating to Cortensor network (k=3 redundancy)...")
        delegate_result = await client.delegate(
            prompt=task_prompt,
            k_redundancy=3,
            max_tokens=2048,
        )

        print(f"\nDelegate Result:")
        print(f"  Task ID: {delegate_result.task_id}")
        print(f"  Consensus Score: {delegate_result.consensus.score:.2f}")
        print(f"  Miners Responded: {delegate_result.consensus.total_miners}")
        print(f"  Latency: {delegate_result.total_latency_ms:.0f}ms")
        print(f"  Verified: {delegate_result.is_verified}")

        print(f"\nResponse Content:\n{'-' * 40}")
        print(delegate_result.content[:500] + "..." if len(delegate_result.content) > 500 else delegate_result.content)
        print(f"{'-' * 40}")

        # Show miner details
        print(f"\nMiner Responses:")
        for mr in delegate_result.miner_responses:
            print(f"  - {mr.miner_id}: {mr.model} ({mr.latency_ms:.0f}ms)")

        # ========================================
        # STEP 2: Validate Results via PoI
        # ========================================
        print("\n" + "=" * 70)
        print("STEP 2: VALIDATE - Verify results via /validate endpoint")
        print("=" * 70)

        # Get the primary miner for validation
        primary_miner = delegate_result.miner_responses[0] if delegate_result.miner_responses else None
        if primary_miner:
            print(f"\nValidating result from miner: {primary_miner.miner_id}")
            print("Using k-redundant re-inference (k=3)...")

            validation_result = await client.validate(
                task_id=delegate_result.task_id,
                miner_address=primary_miner.miner_id,
                result_data=primary_miner.content,
                k_redundancy=3,
            )

            print(f"\nValidation Result:")
            print(f"  Task ID: {validation_result.task_id}")
            print(f"  Is Valid: {validation_result.is_valid}")
            print(f"  Confidence: {validation_result.confidence:.2f}")
            print(f"  K Miners Validated: {validation_result.k_miners_validated}")
            print(f"  Method: {validation_result.validation_details.get('method', 'N/A')}")

            if validation_result.attestation:
                print(f"\nAttestation (JWS):")
                att_preview = validation_result.attestation[:80] + "..." if len(validation_result.attestation) > 80 else validation_result.attestation
                print(f"  {att_preview}")

        # ========================================
        # STEP 3: Run Another Task (for richer session log)
        # ========================================
        print("\n" + "=" * 70)
        print("STEP 3: Additional Delegation (to demonstrate workflow)")
        print("=" * 70)

        task2_prompt = "What are the key security considerations for implementing quadratic voting in a smart contract?"

        print(f"\nTask 2: {task2_prompt[:60]}...")
        result2 = await client.delegate(prompt=task2_prompt, k_redundancy=3)
        print(f"  Task ID: {result2.task_id}")
        print(f"  Consensus: {result2.consensus.score:.2f}")

        # Validate task 2
        if result2.miner_responses:
            val2 = await client.validate(
                task_id=result2.task_id,
                miner_address=result2.miner_responses[0].miner_id,
                result_data=result2.miner_responses[0].content,
            )
            print(f"  Validation: {'PASS' if val2.is_valid else 'FAIL'} (confidence: {val2.confidence:.2f})")

        # ========================================
        # STEP 4: Export Session Log for Submission
        # ========================================
        print("\n" + "=" * 70)
        print("STEP 4: EXPORT - Generate session log for hackathon submission")
        print("=" * 70)

        session_log = client.get_session_log()
        if session_log:
            print(f"\nSession Summary:")
            print(f"  Session ID: {session_log.session_id}")
            print(f"  Session Name: {session_log.session_name}")
            print(f"  Total Delegates: {session_log.total_delegates}")
            print(f"  Total Validates: {session_log.total_validates}")
            print(f"  Total Entries: {len(session_log.entries)}")

            # Export to file
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            export_path = f"session_log_{timestamp}.json"
            client.export_session_log(export_path)
            print(f"\n  Session log exported to: {export_path}")

            # Show session log preview
            print(f"\nSession Log Preview:")
            print("-" * 40)
            log_dict = session_log.to_dict()
            preview = json.dumps(log_dict, indent=2)
            if len(preview) > 1500:
                print(preview[:1500] + "\n... (truncated)")
            else:
                print(preview)

    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)

    print("""
This demo demonstrated the competitive hackathon submission pattern:

1. DELEGATE: Tasks submitted via /delegate endpoint (not /completions)
   - k-redundant inference across multiple miners
   - Consensus calculated from miner responses

2. VALIDATE: Results verified via /validate endpoint
   - k-redundant re-inference for PoI verification
   - Signed attestation (JWS/EIP-712) generated
   - Confidence score returned

3. EXPORT: Session log exported for submission
   - Complete audit trail of all operations
   - Request/response pairs with timestamps
   - Evidence for hackathon judging

To run with real Cortensor network:
    export CORTENSOR_MOCK_MODE=false
    export CORTENSOR_ROUTER_URL=https://router1-t0.cortensor.app
    export CORTENSOR_API_KEY=your-api-key
    python examples/delegate_validate_demo.py
""")


if __name__ == "__main__":
    asyncio.run(run_delegate_validate_workflow())
