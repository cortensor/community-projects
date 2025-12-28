/**
 * VersionBadge - Clean version indicator
 */

interface VersionBadgeProps {
    versionNumber: number;
    previousHash?: string;
    showDiff?: boolean;
    onViewHistory?: () => void;
}

export const VersionBadge = ({
    versionNumber,
    previousHash,
    showDiff = false,
    onViewHistory,
}: VersionBadgeProps) => {
    const isUpdate = previousHash != null;

    return (
        <div className="inline-flex items-center gap-2 animate-fade-in">
            {/* Version */}
            <span
                className="px-2.5 py-1 rounded text-xs font-semibold"
                style={{
                    background: 'var(--color-accent-soft)',
                    color: 'var(--color-accent)',
                }}
            >
                v{versionNumber}
            </span>

            {isUpdate && (
                <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                    ← v{versionNumber - 1}
                </span>
            )}

            {showDiff && isUpdate && (
                <span
                    className="px-2 py-0.5 rounded text-xs font-medium"
                    style={{
                        background: 'var(--color-warning-soft)',
                        color: 'var(--color-warning)',
                    }}
                >
                    Changes
                </span>
            )}

            {onViewHistory && versionNumber > 1 && (
                <button
                    onClick={onViewHistory}
                    className="text-xs underline transition-colors"
                    style={{ color: 'var(--color-text-muted)' }}
                >
                    History
                </button>
            )}
        </div>
    );
};

export default VersionBadge;
