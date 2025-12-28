import React, { useState, useEffect } from 'react';
import { api, IngestResponse } from '../api';

interface ProposalInputProps {
    onIngestComplete: (result: IngestResponse, autoValidate: boolean) => void;
    previousProposalId?: string; // If updating an existing proposal
}

interface RecentProposal {
    proposal_id: string;
    proposal_hash: string;
    version_number: number;
    created_at: string;
    claim_count: number;
}

export function ProposalInput({ onIngestComplete, previousProposalId }: ProposalInputProps) {
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Versioning state
    const [isUpdate, setIsUpdate] = useState(false);
    const [selectedProposalId, setSelectedProposalId] = useState<string | null>(previousProposalId || null);
    const [recentProposals, setRecentProposals] = useState<RecentProposal[]>([]);
    const [loadingProposals, setLoadingProposals] = useState(false);

    // Load recent proposals on mount
    useEffect(() => {
        loadRecentProposals();
    }, []);

    const loadRecentProposals = async () => {
        setLoadingProposals(true);
        try {
            // Try to get recent history which has proposal IDs
            const history = await api.getRecentHistory(5);
            const proposals: RecentProposal[] = history
                .filter((h: any) => h.proposal_id)
                .map((h: any) => ({
                    proposal_id: h.proposal_id || h.job_id,
                    proposal_hash: h.proposal_hash,
                    version_number: h.version_number || 1,
                    created_at: h.created_at,
                    claim_count: h.claims_count,
                }));
            setRecentProposals(proposals);
        } catch (err) {
            console.error('Failed to load recent proposals:', err);
        }
        setLoadingProposals(false);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;

        setLoading(true);
        setError(null);

        try {
            // Detect if input is URL or text
            const isUrl = input.trim().startsWith('http');
            const request: any = isUrl ? { url: input.trim() } : { text: input.trim() };

            // Add previous_proposal_id if updating
            if (isUpdate && selectedProposalId) {
                request.previous_proposal_id = selectedProposalId;
            }

            const result = await api.ingest(request);

            // Show claim diff info if this was an update
            if (result.claim_diff) {
                console.log('Claim diff:', result.claim_diff);
            }

            onIngestComplete(result, true); // Auto-start validation
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to ingest proposal');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="card">
            <form onSubmit={handleSubmit} className="space-y-4">
                {/* New vs Update Toggle */}
                <div className="flex gap-2 mb-4">
                    <button
                        type="button"
                        onClick={() => { setIsUpdate(false); setSelectedProposalId(null); }}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${!isUpdate
                                ? 'bg-accent text-white'
                                : 'bg-transparent border border-gray-600 text-gray-400'
                            }`}
                        style={{
                            background: !isUpdate ? 'var(--color-accent)' : 'transparent',
                            borderColor: !isUpdate ? 'var(--color-accent)' : 'var(--color-border)',
                            color: !isUpdate ? 'white' : 'var(--color-text-muted)',
                        }}
                    >
                        🆕 New Proposal
                    </button>
                    <button
                        type="button"
                        onClick={() => setIsUpdate(true)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${isUpdate
                                ? 'bg-accent text-white'
                                : 'bg-transparent border border-gray-600 text-gray-400'
                            }`}
                        style={{
                            background: isUpdate ? 'var(--color-accent)' : 'transparent',
                            borderColor: isUpdate ? 'var(--color-accent)' : 'var(--color-border)',
                            color: isUpdate ? 'white' : 'var(--color-text-muted)',
                        }}
                    >
                        🔄 Update Existing (v2, v3...)
                    </button>
                </div>

                {/* Proposal Selector (shown when updating) */}
                {isUpdate && (
                    <div
                        className="p-4 rounded-lg mb-4"
                        style={{
                            background: 'var(--color-accent-soft)',
                            border: '1px solid var(--color-accent)',
                        }}
                    >
                        <label
                            className="block text-sm font-medium mb-2"
                            style={{ color: 'var(--color-text)' }}
                        >
                            Select proposal to update:
                        </label>

                        {loadingProposals ? (
                            <p style={{ color: 'var(--color-text-muted)' }}>Loading...</p>
                        ) : recentProposals.length === 0 ? (
                            <div>
                                <p style={{ color: 'var(--color-text-muted)' }} className="text-sm">
                                    No previous proposals found. Submit a new proposal first.
                                </p>
                                <input
                                    type="text"
                                    placeholder="Or enter proposal ID manually..."
                                    className="input-field mt-2"
                                    value={selectedProposalId || ''}
                                    onChange={(e) => setSelectedProposalId(e.target.value || null)}
                                />
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {recentProposals.map((p) => (
                                    <button
                                        key={p.proposal_id}
                                        type="button"
                                        onClick={() => setSelectedProposalId(p.proposal_id)}
                                        className={`w-full text-left p-3 rounded-lg transition-all ${selectedProposalId === p.proposal_id
                                                ? 'ring-2 ring-accent'
                                                : ''
                                            }`}
                                        style={{
                                            background: selectedProposalId === p.proposal_id
                                                ? 'var(--color-bg)'
                                                : 'var(--color-bg-secondary)',
                                            border: selectedProposalId === p.proposal_id
                                                ? '2px solid var(--color-accent)'
                                                : '1px solid var(--color-border)',
                                        }}
                                    >
                                        <div className="flex justify-between items-center">
                                            <span
                                                className="font-medium text-sm"
                                                style={{ color: 'var(--color-text)' }}
                                            >
                                                {p.proposal_id}
                                            </span>
                                            <span
                                                className="text-xs px-2 py-1 rounded"
                                                style={{
                                                    background: 'var(--color-accent-soft)',
                                                    color: 'var(--color-accent)',
                                                }}
                                            >
                                                v{p.version_number}
                                            </span>
                                        </div>
                                        <div
                                            className="text-xs mt-1"
                                            style={{ color: 'var(--color-text-muted)' }}
                                        >
                                            {p.claim_count} claims • {new Date(p.created_at).toLocaleDateString()}
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}

                        {selectedProposalId && (
                            <div
                                className="mt-3 p-2 rounded text-sm"
                                style={{
                                    background: 'var(--color-success-soft)',
                                    color: 'var(--color-success)',
                                }}
                            >
                                ✓ Will create new version for: {selectedProposalId}
                            </div>
                        )}
                    </div>
                )}

                {/* Proposal Text/URL Input */}
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={isUpdate
                        ? "Paste the UPDATED proposal text..."
                        : "Paste DAO proposal text OR Snapshot/Forum URL..."
                    }
                    className="input-field min-h-[160px] resize-y"
                    disabled={loading}
                />

                <div className="flex items-center justify-between">
                    <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                        {isUpdate
                            ? "Xea will detect what changed and only revalidate modified claims"
                            : "Supports: Snapshot, Tally, Commonwealth, or raw proposal text"
                        }
                    </p>

                    <button
                        type="submit"
                        disabled={loading || !input.trim() || (isUpdate && !selectedProposalId)}
                        className="btn-primary flex items-center gap-2"
                    >
                        {loading ? (
                            <>
                                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                                Processing...
                            </>
                        ) : (
                            <>
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                {isUpdate ? 'Verify Updated Proposal' : 'Verify Proposal with Xea'}
                            </>
                        )}
                    </button>
                </div>

                {error && (
                    <div
                        className="rounded-lg p-3"
                        style={{
                            background: 'var(--color-danger-soft)',
                            border: '1px solid var(--color-danger)',
                            color: 'var(--color-danger)',
                        }}
                    >
                        {error}
                    </div>
                )}
            </form>
        </div>
    );
}

export default ProposalInput;
