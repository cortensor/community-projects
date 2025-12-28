/**
 * RecentHistory - Shows last 3 validation results on home page
 */

import { useState, useEffect } from 'react';
import { api, HistoryItem } from '../api';

interface RecentHistoryProps {
    onViewHistory: () => void;
}

export function RecentHistory({ onViewHistory }: RecentHistoryProps) {
    const [items, setItems] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadRecentHistory();
    }, []);

    const loadRecentHistory = async () => {
        try {
            const data = await api.getRecentHistory(3);
            setItems(data);
        } catch (err) {
            console.error('Failed to load recent history:', err);
        } finally {
            setLoading(false);
        }
    };

    const getVerdictColor = (verdict?: string) => {
        switch (verdict) {
            case 'verified': return 'var(--color-success)';
            case 'refuted': return 'var(--color-danger)';
            default: return 'var(--color-warning)';
        }
    };

    const getVerdictIcon = (verdict?: string) => {
        switch (verdict) {
            case 'verified': return '✓';
            case 'refuted': return '✗';
            default: return '?';
        }
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };

    if (loading) {
        return null; // Don't show loading state for this small component
    }

    if (items.length === 0) {
        return null; // Don't show section if no history
    }

    return (
        <div
            className="mt-8 pt-6"
            style={{ borderTop: '1px solid var(--color-border)' }}
        >
            <div className="flex items-center justify-between mb-4">
                <h3
                    className="text-sm font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--color-text-muted)' }}
                >
                    Recent Validations
                </h3>
                <button
                    onClick={onViewHistory}
                    className="text-xs font-medium"
                    style={{ color: 'var(--color-accent)' }}
                >
                    View All →
                </button>
            </div>

            <div className="space-y-2">
                {items.map((item) => (
                    <div
                        key={item.job_id}
                        className="flex items-center justify-between p-3 rounded-lg"
                        style={{
                            background: 'var(--color-bg)',
                            border: '1px solid var(--color-border)',
                        }}
                    >
                        <div className="flex items-center gap-3">
                            <div
                                className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold"
                                style={{
                                    background: `${getVerdictColor(item.overall_verdict)}20`,
                                    color: getVerdictColor(item.overall_verdict),
                                }}
                            >
                                {getVerdictIcon(item.overall_verdict)}
                            </div>
                            <div>
                                <div
                                    className="text-sm font-medium"
                                    style={{ color: 'var(--color-text)' }}
                                >
                                    {item.proposal_title || item.proposal_hash.slice(0, 20) + '...'}
                                </div>
                                <div
                                    className="text-xs"
                                    style={{ color: 'var(--color-text-muted)' }}
                                >
                                    {item.claims_count} claims • {formatDate(item.created_at)}
                                </div>
                            </div>
                        </div>
                        <span
                            className="px-2 py-1 rounded text-xs font-medium"
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
                    </div>
                ))}
            </div>
        </div>
    );
}

export default RecentHistory;
