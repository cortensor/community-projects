/**
 * ClaimDiffSummary - Shows what changed between proposal versions
 */

import { ClaimDiff } from '../api';

interface ClaimDiffSummaryProps {
    diff: ClaimDiff;
    versionNumber: number;
}

export const ClaimDiffSummary = ({ diff, versionNumber }: ClaimDiffSummaryProps) => {
    const hasChanges = diff.new.length > 0 || diff.modified.length > 0 || diff.removed.length > 0;

    if (!hasChanges) {
        return (
            <div
                className="px-4 py-3 rounded-lg text-sm"
                style={{
                    background: 'var(--color-bg)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text-muted)',
                }}
            >
                No changes from previous version
            </div>
        );
    }

    return (
        <div
            className="rounded-lg overflow-hidden"
            style={{
                background: 'var(--color-bg-secondary)',
                border: '1px solid var(--color-border)',
            }}
        >
            {/* Header */}
            <div
                className="px-4 py-3 flex items-center gap-2"
                style={{ borderBottom: '1px solid var(--color-border-subtle)' }}
            >
                <span className="text-lg">📋</span>
                <span className="font-semibold" style={{ color: 'var(--color-text)' }}>
                    Changes in v{versionNumber}
                </span>
            </div>

            {/* Stats */}
            <div className="p-4 flex gap-4">
                {diff.new.length > 0 && (
                    <div className="flex items-center gap-2">
                        <span
                            className="px-2 py-0.5 rounded text-xs font-semibold"
                            style={{
                                background: 'var(--color-success-soft)',
                                color: 'var(--color-success)',
                            }}
                        >
                            +{diff.new.length} NEW
                        </span>
                    </div>
                )}

                {diff.modified.length > 0 && (
                    <div className="flex items-center gap-2">
                        <span
                            className="px-2 py-0.5 rounded text-xs font-semibold"
                            style={{
                                background: 'var(--color-warning-soft)',
                                color: 'var(--color-warning)',
                            }}
                        >
                            ~{diff.modified.length} MODIFIED
                        </span>
                    </div>
                )}

                {diff.removed.length > 0 && (
                    <div className="flex items-center gap-2">
                        <span
                            className="px-2 py-0.5 rounded text-xs font-semibold"
                            style={{
                                background: 'var(--color-danger-soft)',
                                color: 'var(--color-danger)',
                            }}
                        >
                            -{diff.removed.length} REMOVED
                        </span>
                    </div>
                )}

                {diff.unchanged.length > 0 && (
                    <div className="flex items-center gap-2">
                        <span
                            className="text-xs"
                            style={{ color: 'var(--color-text-muted)' }}
                        >
                            {diff.unchanged.length} unchanged
                        </span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ClaimDiffSummary;
