import { useState } from 'react';
import { Claim } from '../api';
import { ClaimDiffStatus } from './ClaimsTable';

interface ClaimRowProps {
    claim: Claim;
    status: 'pending' | 'validating' | 'completed';
    minerCount?: number;
    totalMiners?: number;
    diffStatus?: ClaimDiffStatus | null;
}

/**
 * Diff badge configuration
 */
const diffBadgeConfig: Record<ClaimDiffStatus, { label: string; color: string; bg: string }> = {
    new: {
        label: 'NEW',
        color: 'var(--color-success)',
        bg: 'var(--color-success-soft)'
    },
    modified: {
        label: 'MODIFIED',
        color: 'var(--color-warning)',
        bg: 'var(--color-warning-soft)'
    },
    unchanged: {
        label: '', // Don't show badge for unchanged
        color: 'var(--color-text-muted)',
        bg: 'transparent'
    },
    removed: {
        label: 'REMOVED',
        color: 'var(--color-danger)',
        bg: 'var(--color-danger-soft)'
    },
};

export function ClaimRow({ claim, status, minerCount = 0, totalMiners = 5, diffStatus }: ClaimRowProps) {
    const [expanded, setExpanded] = useState(false);

    const statusBadge = {
        pending: 'badge-pending',
        validating: 'badge-validating animate-pulse-subtle',
        completed: 'badge-supported',
    }[status];

    const statusLabel = {
        pending: 'Pending',
        validating: `Validating (${minerCount}/${totalMiners})`,
        completed: 'Completed',
    }[status];

    const diffBadge = diffStatus ? diffBadgeConfig[diffStatus] : null;
    const showDiffBadge = diffBadge && diffBadge.label;

    return (
        <div
            className="rounded-lg border overflow-hidden"
            style={{
                background: 'var(--color-bg-secondary)',
                borderColor: showDiffBadge ? diffBadge.color : 'var(--color-border)',
                borderLeftWidth: showDiffBadge ? '3px' : '1px',
            }}
        >
            <div
                className="p-4 cursor-pointer transition-colors"
                onClick={() => setExpanded(!expanded)}
                style={{ background: showDiffBadge ? `${diffBadge.bg}` : 'transparent' }}
            >
                <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                            <span style={{ color: 'var(--color-accent)' }} className="font-semibold text-sm">
                                {claim.id.toUpperCase()}
                            </span>
                            <span
                                className="text-xs px-2 py-0.5 rounded"
                                style={{
                                    background: 'var(--color-bg)',
                                    color: 'var(--color-text-muted)',
                                }}
                            >
                                {claim.type}
                            </span>

                            {/* Diff Badge */}
                            {showDiffBadge && (
                                <span
                                    className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                                    style={{
                                        background: diffBadge.bg,
                                        color: diffBadge.color,
                                    }}
                                >
                                    {diffBadge.label}
                                </span>
                            )}
                        </div>
                        <p style={{ color: 'var(--color-text)' }} className="line-clamp-2">
                            {claim.text}
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        <span className={`badge ${statusBadge}`}>
                            {statusLabel}
                        </span>
                        <svg
                            className={`w-5 h-5 transition-transform ${expanded ? 'rotate-180' : ''}`}
                            style={{ color: 'var(--color-text-muted)' }}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </div>
                </div>
            </div>

            {expanded && (
                <div
                    className="px-4 pb-4 pt-3"
                    style={{ borderTop: '1px solid var(--color-border-subtle)' }}
                >
                    <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                            <p style={{ color: 'var(--color-text-muted)' }} className="mb-1">Paragraph</p>
                            <p style={{ color: 'var(--color-text-secondary)' }}>#{claim.paragraph_index + 1}</p>
                        </div>
                        <div>
                            <p style={{ color: 'var(--color-text-muted)' }} className="mb-1">Character Range</p>
                            <p style={{ color: 'var(--color-text-secondary)' }}>{claim.char_range[0]}–{claim.char_range[1]}</p>
                        </div>
                        <div>
                            <p style={{ color: 'var(--color-text-muted)' }} className="mb-1">Type</p>
                            <p style={{ color: 'var(--color-text-secondary)' }} className="capitalize">{claim.type}</p>
                        </div>
                    </div>

                    {claim.canonical && (
                        <div className="mt-3 pt-3" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
                            <p style={{ color: 'var(--color-text-muted)' }} className="text-sm mb-2">Canonicalized Data</p>
                            <div className="flex flex-wrap gap-2">
                                {claim.canonical.numbers?.length > 0 && (
                                    <span
                                        className="text-xs px-2 py-1 rounded"
                                        style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}
                                    >
                                        Numbers: {claim.canonical.numbers.join(', ')}
                                    </span>
                                )}
                                {claim.canonical.addresses?.length > 0 && claim.canonical.addresses.map((addr, i) => (
                                    <span
                                        key={i}
                                        className="text-xs px-2 py-1 rounded font-mono"
                                        style={{ background: 'rgba(139, 92, 246, 0.15)', color: '#a78bfa' }}
                                    >
                                        {addr.slice(0, 6)}...{addr.slice(-4)}
                                    </span>
                                ))}
                                {claim.canonical.urls?.length > 0 && (
                                    <span
                                        className="text-xs px-2 py-1 rounded"
                                        style={{ background: 'rgba(34, 197, 94, 0.15)', color: '#4ade80' }}
                                    >
                                        URLs: {claim.canonical.urls.length}
                                    </span>
                                )}
                                {(!claim.canonical.numbers?.length && !claim.canonical.addresses?.length && !claim.canonical.urls?.length) && (
                                    <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                        No special values extracted
                                    </span>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default ClaimRow;
