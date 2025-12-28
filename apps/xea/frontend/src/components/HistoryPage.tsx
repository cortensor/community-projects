/**
 * HistoryPage - Validation history list (fetches from API)
 */

import { useState, useEffect } from 'react';
import { api, HistoryItem, EvidenceBundle } from '../api';

export function HistoryPage() {
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedBundle, setSelectedBundle] = useState<EvidenceBundle | null>(null);

    useEffect(() => {
        loadHistory();
    }, []);

    const loadHistory = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await api.getHistory();
            setHistory(data);
        } catch (err: any) {
            console.error('Failed to load history:', err);
            setError('Failed to load history. Please try again.');
        }
        setLoading(false);
    };

    const viewEvidence = async (jobId: string) => {
        try {
            const item = await api.getHistoryItem(jobId);
            if (item.evidence_json) {
                setSelectedBundle(item.evidence_json);
            } else {
                // Try to fetch from evidence endpoint
                const bundle = await api.getEvidence(jobId, 'delegate');
                setSelectedBundle(bundle as EvidenceBundle);
            }
        } catch (err) {
            console.error('Failed to load evidence:', err);
        }
    };

    const getVerdictColor = (verdict?: string) => {
        switch (verdict) {
            case 'verified': return 'var(--color-success)';
            case 'refuted': return 'var(--color-danger)';
            default: return 'var(--color-warning)';
        }
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
                        Validation History
                    </h1>
                    <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                        View past validation results and evidence bundles
                    </p>
                </div>
                <button
                    onClick={loadHistory}
                    className="px-4 py-2 rounded-lg text-sm font-medium"
                    style={{
                        background: 'var(--color-bg)',
                        border: '1px solid var(--color-border)',
                        color: 'var(--color-text)',
                    }}
                >
                    🔄 Refresh
                </button>
            </div>

            {/* Error Message */}
            {error && (
                <div
                    className="p-4 rounded-lg"
                    style={{
                        background: 'var(--color-danger-soft)',
                        color: 'var(--color-danger)'
                    }}
                >
                    {error}
                </div>
            )}

            {/* History List */}
            {loading ? (
                <div
                    className="text-center py-12 rounded-xl"
                    style={{
                        background: 'var(--color-bg)',
                        border: '1px solid var(--color-border)',
                    }}
                >
                    <div
                        className="animate-spin w-8 h-8 border-2 border-current border-t-transparent rounded-full mx-auto mb-4"
                        style={{ color: 'var(--color-accent)' }}
                    />
                    <p style={{ color: 'var(--color-text-muted)' }}>Loading history...</p>
                </div>
            ) : history.length === 0 ? (
                <div
                    className="text-center py-16 rounded-xl"
                    style={{
                        background: 'var(--color-bg)',
                        border: '2px dashed var(--color-border)'
                    }}
                >
                    <div className="text-5xl mb-4">📋</div>
                    <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--color-text)' }}>
                        No Validation History
                    </h3>
                    <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
                        Submit a proposal on the Home tab to start validating claims
                    </p>
                    <div
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg"
                        style={{
                            background: 'var(--color-accent-soft)',
                            color: 'var(--color-accent)',
                        }}
                    >
                        <span>💡</span>
                        <span className="text-sm">Validated proposals will appear here</span>
                    </div>
                </div>
            ) : (
                <div className="space-y-3">
                    {history.map((item) => (
                        <div
                            key={item.job_id}
                            className="p-4 rounded-xl cursor-pointer transition-transform hover:scale-[1.01]"
                            style={{
                                background: 'var(--color-bg)',
                                border: '1px solid var(--color-border)',
                            }}
                            onClick={() => viewEvidence(item.job_id)}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div
                                        className="w-12 h-12 rounded-xl flex items-center justify-center text-xl"
                                        style={{
                                            background: `${getVerdictColor(item.overall_verdict)}20`,
                                            color: getVerdictColor(item.overall_verdict),
                                        }}
                                    >
                                        {item.overall_verdict === 'verified' ? '✓' :
                                            item.overall_verdict === 'refuted' ? '✗' : '?'}
                                    </div>
                                    <div>
                                        <div className="font-semibold" style={{ color: 'var(--color-text)' }}>
                                            {item.proposal_title || item.proposal_hash.slice(0, 24) + '...'}
                                        </div>
                                        <div className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                                            {item.claims_count} claims • {formatDate(item.created_at)}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span
                                        className="px-3 py-1 rounded-full text-xs font-medium"
                                        style={{
                                            background: item.status === 'completed'
                                                ? 'var(--color-success-soft)'
                                                : 'var(--color-warning-soft)',
                                            color: item.status === 'completed'
                                                ? 'var(--color-success)'
                                                : 'var(--color-warning)',
                                        }}
                                    >
                                        {item.status}
                                    </span>
                                    <span style={{ color: 'var(--color-text-muted)' }}>→</span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Evidence Modal */}
            {selectedBundle && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center p-6"
                    style={{ background: 'rgba(0, 0, 0, 0.7)' }}
                    onClick={() => setSelectedBundle(null)}
                >
                    <div
                        className="max-w-2xl w-full max-h-[80vh] overflow-auto rounded-xl p-6"
                        style={{
                            background: 'var(--color-bg-elevated)',
                            border: '1px solid var(--color-border)',
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-bold" style={{ color: 'var(--color-text)' }}>
                                Evidence Bundle
                            </h3>
                            <button
                                onClick={() => setSelectedBundle(null)}
                                className="text-2xl"
                                style={{ color: 'var(--color-text-muted)' }}
                            >
                                ×
                            </button>
                        </div>
                        <pre
                            className="text-xs p-4 rounded-lg overflow-auto"
                            style={{
                                background: 'var(--color-bg)',
                                color: 'var(--color-text-secondary)',
                                maxHeight: '60vh',
                            }}
                        >
                            {JSON.stringify(selectedBundle, null, 2)}
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
}

export default HistoryPage;
