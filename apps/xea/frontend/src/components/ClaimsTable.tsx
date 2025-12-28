import { Claim, MinerResponse, ClaimDiff } from '../api';
import { ClaimRow } from './ClaimRow';

export type ClaimDiffStatus = 'new' | 'modified' | 'unchanged' | 'removed';

interface ClaimsTableProps {
    claims: Claim[];
    claimStatuses: Map<string, 'pending' | 'validating' | 'completed'>;
    minerResponses: Map<string, MinerResponse[]>;
    totalMiners: number;
    claimDiff?: ClaimDiff;  // Optional: for showing diff badges
}

/**
 * Get diff status for a claim
 */
function getClaimDiffStatus(claimId: string, claimDiff?: ClaimDiff): ClaimDiffStatus | null {
    if (!claimDiff) return null;

    if (claimDiff.new.includes(claimId)) return 'new';
    if (claimDiff.modified.some(m => m.claim_id === claimId)) return 'modified';
    if (claimDiff.unchanged.includes(claimId)) return 'unchanged';
    if (claimDiff.removed.includes(claimId)) return 'removed';

    return null;
}

export function ClaimsTable({ claims, claimStatuses, minerResponses, totalMiners, claimDiff }: ClaimsTableProps) {
    if (claims.length === 0) {
        return (
            <div className="card text-center text-gray-400 py-8">
                No claims extracted yet
            </div>
        );
    }

    const hasDiff = claimDiff && (claimDiff.new.length > 0 || claimDiff.modified.length > 0);

    return (
        <div className="card">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">
                    Extracted Claims ({claims.length})
                </h3>
                <div className="flex items-center gap-4 text-sm text-gray-400">
                    {/* Diff status indicators (only when diff exists) */}
                    {hasDiff && (
                        <>
                            <span className="flex items-center gap-1">
                                <span className="w-2 h-2 rounded-full" style={{ background: 'var(--color-success)' }} />
                                New
                            </span>
                            <span className="flex items-center gap-1">
                                <span className="w-2 h-2 rounded-full" style={{ background: 'var(--color-warning)' }} />
                                Modified
                            </span>
                        </>
                    )}
                    {/* Validation status indicators */}
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-gray-600" />
                        Pending
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-xea-accent animate-pulse" />
                        Validating
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-verdict-supported" />
                        Completed
                    </span>
                </div>
            </div>

            <div className="space-y-3">
                {claims.map((claim) => {
                    const status = claimStatuses.get(claim.id) || 'pending';
                    const responses = minerResponses.get(claim.id) || [];
                    const diffStatus = getClaimDiffStatus(claim.id, claimDiff);

                    return (
                        <ClaimRow
                            key={claim.id}
                            claim={claim}
                            status={status}
                            minerCount={responses.length}
                            totalMiners={totalMiners}
                            diffStatus={diffStatus}
                        />
                    );
                })}
            </div>
        </div>
    );
}

export default ClaimsTable;
