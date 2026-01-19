"""Demo: Cortensor Governance Agent.

This demo shows a complete workflow:
1. Connect to Cortensor MCP server
2. Analyze a DeFi governance proposal
3. Validate results through Cortensor network
4. Generate evidence bundle
"""

import json
import logging
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cortensor_agent import GovernanceAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


SAMPLE_PROPOSAL = """
Proposal: Implement quadratic voting for protocol upgrades

Summary:
- Each token holder gets votes proportional to sqrt(tokens held)
- Minimum 1000 tokens required to participate
- 7-day voting period with 3-day timelock after passing
- Emergency proposals can bypass with 80% supermajority

Rationale:
Quadratic voting reduces plutocratic control by making it expensive for
whales to dominate decisions. A holder with 1M tokens gets 1000 votes,
while 1000 holders with 1000 tokens each get 31,623 total votes.

Implementation:
- Snapshot-based voting at proposal creation
- On-chain vote tallying with quadratic formula
- Timelock contract for execution delay
"""


def main():
    print("=" * 60)
    print("Cortensor Governance Agent Demo")
    print("=" * 60)
    print()

    agent = GovernanceAgent()

    try:
        # Step 1: Connect
        print("[1/4] Connecting to Cortensor MCP server...")
        if not agent.connect(session_name="governance-demo", min_nodes=2):
            print("Failed to connect. Check network and try again.")
            return 1
        print("Connected successfully.")
        print()

        # Step 2: Analyze
        print("[2/4] Analyzing governance proposal...")
        print("-" * 40)
        print(SAMPLE_PROPOSAL.strip()[:200] + "...")
        print("-" * 40)
        print()

        result = agent.analyze_proposal(SAMPLE_PROPOSAL, validate=True)

        # Step 3: Show results
        print("[3/4] Analysis Results")
        print("-" * 40)
        print(f"Task ID: {result.task_id}")
        print(f"Validated: {result.validated}")
        if result.validation_score is not None:
            print(f"Validation Score: {result.validation_score:.2f}")
        print()
        print("Analysis:")
        print(result.analysis[:500] + "..." if len(result.analysis) > 500 else result.analysis)
        print("-" * 40)
        print()

        # Step 4: Evidence bundle
        print("[4/4] Generating evidence bundle...")
        evidence = agent.generate_evidence_bundle(result)

        print(f"Bundle ID: {evidence.bundle_id}")
        print(f"Integrity Hash: {evidence.integrity_hash[:32]}...")
        print()

        # Save evidence bundle
        output_file = Path(__file__).parent / f"evidence_{evidence.bundle_id}.json"
        with open(output_file, "w") as f:
            json.dump(evidence.to_dict(), f, indent=2)
        print(f"Evidence bundle saved to: {output_file}")

        print()
        print("=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)

        return 0

    except Exception as e:
        logger.exception("Demo failed")
        print(f"Error: {e}")
        return 1

    finally:
        agent.close()


if __name__ == "__main__":
    sys.exit(main())
