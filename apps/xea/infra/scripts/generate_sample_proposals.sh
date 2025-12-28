#!/bin/bash
# Generate sample DAO proposals for testing

set -e

OUTPUT_DIR="${1:-./sample_proposals}"

echo "📝 Generating sample DAO proposals..."

mkdir -p "$OUTPUT_DIR"

# Sample proposal 1: Treasury allocation
cat > "$OUTPUT_DIR/treasury_allocation.md" << 'EOF'
# Proposal: Treasury Allocation for Developer Grants

## Summary
This proposal requests 50,000 USDC from the DAO treasury to fund developer grants for Q1 2025.

## Background
The DAO treasury currently holds approximately 500,000 USDC. This allocation represents 10% of total treasury funds.

## Specification

### Grant Distribution
- Smart Contract Development: 20,000 USDC
- Frontend Development: 15,000 USDC
- Documentation and Tutorials: 10,000 USDC
- Security Audits: 5,000 USDC

### Timeline
- Grant applications open: January 15, 2025
- Application deadline: February 15, 2025
- Grant disbursement: March 1, 2025

### Oversight
A 3-of-5 multisig consisting of core contributors will manage grant disbursements.

## Rationale
Developer grants have historically provided 3x ROI in terms of protocol value added.
The previous grant program funded 12 projects, 8 of which are now live on mainnet.

## Voting
- For: Approve the 50,000 USDC allocation
- Against: Reject the proposal
- Abstain: No vote
EOF

# Sample proposal 2: Protocol upgrade
cat > "$OUTPUT_DIR/protocol_upgrade.md" << 'EOF'
# Proposal: Protocol V2 Migration

## Summary
Upgrade the protocol to V2, introducing gas optimizations and new features.

## Technical Changes

### Gas Optimizations
The new V2 contracts reduce gas costs by approximately 40% for standard transactions.
Batch operations will see up to 60% gas reduction.

### New Features
1. Permit-based approvals (EIP-2612)
2. Flash loan support
3. Multi-hop routing optimization

### Migration Plan
- Phase 1: Deploy V2 contracts (Week 1)
- Phase 2: Run parallel testing (Weeks 2-3)
- Phase 3: Migrate liquidity (Week 4)
- Phase 4: Deprecate V1 (Week 8)

## Security
- Audit completed by Trail of Bits (December 2024)
- Bug bounty program: $500,000 maximum payout
- 2 critical issues identified and fixed pre-deployment

## Voting Period
7 days, standard quorum of 4% required.
EOF

# Sample proposal 3: Governance change
cat > "$OUTPUT_DIR/governance_change.md" << 'EOF'
# Proposal: Reduce Quorum Requirement

## Summary
Reduce the governance quorum from 4% to 2.5% of total token supply.

## Current State
- Current quorum: 4% (40,000,000 tokens)
- Average participation: 3.2%
- Proposals that failed quorum in 2024: 7

## Proposed Change
- New quorum: 2.5% (25,000,000 tokens)
- Implementation: Immediate upon proposal passage

## Analysis
Historical data shows:
- 78% of proposals would have passed with 2.5% quorum
- Average time to quorum would decrease from 4.2 days to 1.8 days
- Similar DAOs operate successfully with 2-3% quorum

## Risk Considerations
Lower quorum could potentially allow minority capture.
Mitigation: Maintain 7-day voting period for review.

## Voting
Simple majority required with 4% quorum (current rules apply to this proposal).
EOF

echo "✅ Generated 3 sample proposals in $OUTPUT_DIR/"
echo ""
echo "Files created:"
ls -la "$OUTPUT_DIR"
