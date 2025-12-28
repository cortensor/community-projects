import { Claim, MinerResponse, JobProgress } from '../api';
import { ValidationStepper } from './ValidationStepper';

interface LiveMinerPanelProps {
    claims: Claim[];
    progress: JobProgress;
    minerResponses: Map<string, MinerResponse[]>;
    status: 'queued' | 'running' | 'completed' | 'failed';
    connected: boolean;
    // NEW: Stage tracking props
    currentStage?: string;
    retriesAttempted?: number;
    lastHeartbeat?: string;
}

export function LiveMinerPanel({
    claims,
    progress,
    minerResponses,
    status,
    connected,
    currentStage,
    retriesAttempted,
    lastHeartbeat,
}: LiveMinerPanelProps) {
    const progressPercent = progress.miners_contacted > 0
        ? (progress.miners_responded / progress.miners_contacted) * 100
        : 0;

    const getVerdictColor = (verdict: string) => {
        switch (verdict) {
            case 'verified': return 'bg-verdict-supported text-black';
            case 'refuted': return 'bg-verdict-disputed text-white';
            case 'partial': return 'bg-verdict-caution text-black';
            default: return 'bg-gray-600 text-white';
        }
    };

    return (
        <div className="space-y-6">
            {/* Validation Stepper (NEW) */}
            <ValidationStepper
                currentStage={currentStage || (status === 'running' ? 'waiting' : status === 'completed' ? 'completed' : 'dispatching')}
                claimsValidated={progress.claims_validated}
                claimsTotal={progress.claims_total}
                retriesAttempted={retriesAttempted}
                lastHeartbeat={lastHeartbeat}
                minerStats={{
                    requested: progress.miners_contacted,
                    received: progress.miners_responded,
                    quorum_target: 3,
                }}
            />

            {/* Per-Claim Progress */}
            <div className="card">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                        Claim Validation
                        {status === 'running' && (
                            <span className="flex items-center gap-1.5">
                                <span className="relative flex h-3 w-3">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-xea-accent opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-3 w-3 bg-xea-accent"></span>
                                </span>
                            </span>
                        )}
                        {status === 'completed' && (
                            <span className="badge badge-supported">Complete</span>
                        )}
                    </h3>
                    <div className="flex items-center gap-2 text-sm">
                        <span className={`w-2 h-2 rounded-full ${connected ? 'bg-verdict-supported' : 'bg-verdict-disputed'}`} />
                        <span className="text-gray-400">{connected ? 'Connected' : 'Polling'}</span>
                    </div>
                </div>

                <div className="space-y-4">
                    {claims.map((claim) => {
                        const responses = minerResponses.get(claim.id) || [];
                        const claimProgress = responses.length > 0 ? 100 : 0;

                        return (
                            <div
                                key={claim.id}
                                className="rounded-lg p-4"
                                style={{
                                    background: 'var(--color-bg)',
                                    border: '1px solid var(--color-border-subtle)',
                                }}
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <span style={{ color: 'var(--color-accent)' }} className="font-semibold text-sm">
                                        {claim.id.toUpperCase()}
                                    </span>
                                    <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                        {responses.length > 0 ? '✓ Validated' : '⏳ Pending'}
                                    </span>
                                </div>

                                <p className="text-sm mb-3 line-clamp-1" style={{ color: 'var(--color-text-secondary)' }}>
                                    {claim.text}
                                </p>

                                {/* Progress bar */}
                                <div className="progress-bar mb-3">
                                    <div
                                        className="progress-fill"
                                        style={{ width: `${claimProgress}%` }}
                                    />
                                </div>

                                {/* Verdict badges */}
                                <div className="flex flex-wrap gap-2">
                                    {responses.map((resp, idx) => (
                                        <span
                                            key={idx}
                                            className={`badge ${getVerdictColor(resp.verdict)}`}
                                            title={resp.miner_id}
                                        >
                                            {resp.miner_id.startsWith('cortensor') ? '🌐 Cortensor' : resp.miner_id}:{' '}
                                            {resp.verdict === 'verified' ? 'Verified' : resp.verdict === 'refuted' ? 'Refuted' : 'Unverifiable'}
                                        </span>
                                    ))}
                                    {responses.length === 0 && (
                                        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                            Waiting for decentralized inference...
                                        </span>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}

export default LiveMinerPanel;
