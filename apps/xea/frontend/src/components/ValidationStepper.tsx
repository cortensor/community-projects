/**
 * ValidationStepper - Shows validation progress through canonical stages
 */

const stages = [
    { key: 'dispatching', label: 'Sending to Network', icon: '📡' },
    { key: 'waiting', label: 'Waiting for Miners', icon: '⏳' },
    { key: 'partial', label: 'Receiving Responses', icon: '📥' },
    { key: 'aggregating', label: 'Computing Evidence', icon: '🔬' },
    { key: 'completed', label: 'Complete', icon: '✅' },
];

interface MinerStats {
    requested: number;
    received: number;
    quorum_target: number;
}

interface ValidationStepperProps {
    currentStage: string;
    minerStats?: MinerStats;
    claimsValidated?: number;
    claimsTotal?: number;
    retriesAttempted?: number;
    lastHeartbeat?: string;
    networkUsed?: string;  // NEW: testnet1 | testnet0
}

function getStageIndex(stage: string): number {
    const idx = stages.findIndex(s => s.key === stage);
    return idx >= 0 ? idx : 0;
}

function formatTimeAgo(isoString?: string): string {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 10) return 'just now';
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 120) return '1 min ago';
    return `${Math.floor(seconds / 60)} mins ago`;
}

export function ValidationStepper({
    currentStage,
    minerStats,
    claimsValidated = 0,
    claimsTotal = 0,
    retriesAttempted = 0,
    lastHeartbeat,
    networkUsed = 'testnet0',
}: ValidationStepperProps) {
    const currentIndex = getStageIndex(currentStage);
    const isComplete = currentStage === 'completed';
    const isFailed = currentStage === 'failed';

    return (
        <div
            className="rounded-xl p-5"
            style={{
                background: 'var(--color-bg-secondary)',
                border: '1px solid var(--color-border)',
            }}
        >
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <span className="text-lg">📡</span>
                    <h3 className="font-semibold" style={{ color: 'var(--color-text)' }}>
                        Decentralized Validation
                    </h3>
                    {/* Network Badge */}
                    <span
                        className="text-xs px-2 py-1 rounded font-medium"
                        style={{
                            background: 'var(--color-accent-soft, rgba(99, 102, 241, 0.15))',
                            color: 'var(--color-accent)',
                        }}
                    >
                        🌐 {networkUsed}
                    </span>
                </div>
                {lastHeartbeat && (
                    <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        Last update: {formatTimeAgo(lastHeartbeat)}
                    </span>
                )}
            </div>

            {/* Stage Stepper */}
            <div className="flex items-center justify-between mb-6">
                {stages.map((stage, index) => {
                    const isActive = index === currentIndex;
                    const isPast = index < currentIndex || isComplete;
                    const isCurrent = isActive && !isComplete;

                    return (
                        <div key={stage.key} className="flex flex-col items-center flex-1">
                            {/* Stage Icon */}
                            <div
                                className={`
                                    w-10 h-10 rounded-full flex items-center justify-center text-lg
                                    transition-all duration-300
                                    ${isCurrent ? 'animate-pulse' : ''}
                                `}
                                style={{
                                    background: isPast
                                        ? 'var(--color-success)'
                                        : isCurrent
                                            ? 'var(--color-accent)'
                                            : 'var(--color-bg)',
                                    border: isPast || isCurrent
                                        ? 'none'
                                        : '2px solid var(--color-border)',
                                    color: isPast || isCurrent ? 'white' : 'var(--color-text-muted)',
                                }}
                            >
                                {isPast ? '✓' : stage.icon}
                            </div>

                            {/* Stage Label */}
                            <span
                                className="text-xs mt-2 text-center"
                                style={{
                                    color: isActive || isPast
                                        ? 'var(--color-text)'
                                        : 'var(--color-text-muted)',
                                    fontWeight: isActive ? 600 : 400,
                                }}
                            >
                                {stage.label}
                            </span>

                            {/* Connector Line */}
                            {index < stages.length - 1 && (
                                <div
                                    className="absolute h-0.5 w-full top-5 left-1/2"
                                    style={{
                                        background: isPast ? 'var(--color-success)' : 'var(--color-border)',
                                        display: 'none', // Hide for now, complex positioning
                                    }}
                                />
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Progress Stats */}
            <div
                className="rounded-lg p-4"
                style={{
                    background: 'var(--color-bg)',
                    border: '1px solid var(--color-border-subtle)',
                }}
            >
                <div className="grid grid-cols-3 gap-4 text-sm">
                    {/* Claims Progress */}
                    <div>
                        <p className="text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>
                            Claims
                        </p>
                        <p className="font-semibold" style={{ color: 'var(--color-text)' }}>
                            {claimsValidated} / {claimsTotal}
                        </p>
                    </div>

                    {/* Responses */}
                    {minerStats && (
                        <div>
                            <p className="text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>
                                Responses
                            </p>
                            <p className="font-semibold" style={{ color: 'var(--color-text)' }}>
                                {minerStats.received} / {minerStats.requested}
                            </p>
                        </div>
                    )}

                    {/* Retries */}
                    <div>
                        <p className="text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>
                            Retries
                        </p>
                        <p className="font-semibold" style={{
                            color: retriesAttempted > 0 ? 'var(--color-warning)' : 'var(--color-text)',
                        }}>
                            {retriesAttempted}
                        </p>
                    </div>
                </div>
            </div>

            {/* Info Message */}
            <p
                className="text-xs mt-4 text-center"
                style={{ color: 'var(--color-text-muted)' }}
            >
                ℹ️ This typically takes 30-60 seconds due to decentralized inference.
            </p>

            {/* Failed State */}
            {isFailed && (
                <div
                    className="mt-4 p-3 rounded-lg text-sm"
                    style={{
                        background: 'var(--color-danger-soft)',
                        color: 'var(--color-danger)',
                    }}
                >
                    ❌ Validation failed. Please retry.
                </div>
            )}
        </div>
    );
}

export default ValidationStepper;
