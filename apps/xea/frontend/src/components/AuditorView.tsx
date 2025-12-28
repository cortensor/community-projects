/**
 * AuditorView - Technical deep-dive for auditors with raw evidence data
 */

import { EvidenceBundle, ClaimAggregation } from '../api';

interface AuditorViewProps {
    bundle: EvidenceBundle;
}

function MinerResponseCard({ claim }: { claim: ClaimAggregation }) {
    return (
        <div
            className="rounded-xl p-4"
            style={{
                background: 'var(--color-bg)',
                border: '1px solid var(--color-border)',
            }}
        >
            <div className="flex items-center justify-between mb-3">
                <span
                    className="font-mono text-sm font-bold"
                    style={{ color: 'var(--color-accent)' }}
                >
                    {claim.id.toUpperCase()}
                </span>
                <span
                    className="text-xs px-2 py-1 rounded-full font-medium"
                    style={{
                        background: claim.final_recommendation === 'supported'
                            ? 'var(--color-success-soft)'
                            : claim.final_recommendation === 'disputed'
                                ? 'var(--color-danger-soft)'
                                : 'var(--color-warning-soft)',
                        color: claim.final_recommendation === 'supported'
                            ? 'var(--color-success)'
                            : claim.final_recommendation === 'disputed'
                                ? 'var(--color-danger)'
                                : 'var(--color-warning)',
                    }}
                >
                    {claim.final_recommendation?.replace(/_/g, ' ')}
                </span>
            </div>

            {/* Claim Text */}
            <p className="text-sm mb-4" style={{ color: 'var(--color-text-secondary)' }}>
                {claim.text}
            </p>

            {/* Raw Scores Table */}
            <div className="mb-4">
                <h4 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-muted)' }}>
                    Score Breakdown
                </h4>
                <div
                    className="grid grid-cols-4 gap-2 text-center text-xs p-3 rounded-lg"
                    style={{ background: 'var(--color-bg-secondary)' }}
                >
                    <div>
                        <p className="font-mono font-bold" style={{ color: 'var(--color-accent)' }}>
                            {(claim.poi_agreement * 100).toFixed(0)}%
                        </p>
                        <p style={{ color: 'var(--color-text-muted)' }}>PoI</p>
                    </div>
                    <div>
                        <p className="font-mono font-bold" style={{ color: 'var(--color-accent)' }}>
                            {claim.pouw_mean.toFixed(2)}
                        </p>
                        <p style={{ color: 'var(--color-text-muted)' }}>PoUW μ</p>
                    </div>
                    <div>
                        <p className="font-mono font-bold" style={{ color: 'var(--color-text)' }}>
                            ±{((claim.pouw_ci_95[1] - claim.pouw_ci_95[0]) / 2).toFixed(2)}
                        </p>
                        <p style={{ color: 'var(--color-text-muted)' }}>95% CI</p>
                    </div>
                    <div>
                        <p className="font-mono font-bold" style={{ color: 'var(--color-text)' }}>
                            {claim.miner_responses?.length || 0}
                        </p>
                        <p style={{ color: 'var(--color-text-muted)' }}>Miners</p>
                    </div>
                </div>
            </div>

            {/* Miner Responses */}
            {claim.miner_responses && claim.miner_responses.length > 0 && (
                <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-muted)' }}>
                        Individual Miner Responses ({claim.miner_responses.length})
                    </h4>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                        {claim.miner_responses.map((resp, idx) => (
                            <div
                                key={idx}
                                className="p-3 rounded-lg text-xs"
                                style={{
                                    background: 'var(--color-bg-secondary)',
                                    border: '1px solid var(--color-border-subtle)',
                                }}
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <span className="font-mono" style={{ color: 'var(--color-text)' }}>
                                        Miner #{idx + 1}
                                    </span>
                                    <span
                                        className="px-2 py-0.5 rounded text-xs"
                                        style={{
                                            background: resp.verdict === 'verified'
                                                ? 'var(--color-success-soft)'
                                                : resp.verdict === 'refuted'
                                                    ? 'var(--color-danger-soft)'
                                                    : 'var(--color-warning-soft)',
                                            color: resp.verdict === 'verified'
                                                ? 'var(--color-success)'
                                                : resp.verdict === 'refuted'
                                                    ? 'var(--color-danger)'
                                                    : 'var(--color-warning)',
                                        }}
                                    >
                                        {resp.verdict}
                                    </span>
                                </div>
                                {resp.rationale && (
                                    <p className="mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                                        <strong>Rationale:</strong> {resp.rationale}
                                    </p>
                                )}
                                {resp.evidence_links && resp.evidence_links.length > 0 && (
                                    <div>
                                        <strong style={{ color: 'var(--color-text-muted)' }}>Evidence:</strong>
                                        <ul className="mt-1 space-y-1">
                                            {resp.evidence_links.map((link, i) => (
                                                <li key={i}>
                                                    <a
                                                        href={link}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="underline"
                                                        style={{ color: 'var(--color-accent)' }}
                                                    >
                                                        {link.slice(0, 50)}...
                                                    </a>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                                {resp.scores && (
                                    <div className="mt-2 pt-2" style={{ borderTop: '1px dashed var(--color-border)' }}>
                                        <span style={{ color: 'var(--color-text-muted)' }}>
                                            Composite: {resp.scores.composite?.toFixed(2)}
                                        </span>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Outliers */}
            {claim.outliers && claim.outliers.length > 0 && (
                <div
                    className="mt-3 p-2 rounded text-xs"
                    style={{
                        background: 'var(--color-warning-soft)',
                        color: 'var(--color-warning)',
                    }}
                >
                    ⚠️ Outliers: {claim.outliers.join(', ')}
                </div>
            )}
        </div>
    );
}

export function AuditorView({ bundle }: AuditorViewProps) {
    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>
                        🔬 Technical Evidence Audit
                    </h2>
                    <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                        Raw miner responses and verification data
                    </p>
                </div>
            </div>

            {/* Computation Hash */}
            <div
                className="rounded-xl p-4"
                style={{
                    background: 'var(--color-bg)',
                    border: '1px solid var(--color-border)',
                }}
            >
                <h4 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-muted)' }}>
                    Verification Hash
                </h4>
                <code
                    className="text-xs font-mono block p-3 rounded-lg break-all"
                    style={{
                        background: 'var(--color-bg-secondary)',
                        color: 'var(--color-accent)',
                    }}
                >
                    {bundle.computation_hash || 'Not computed'}
                </code>
                <p className="text-xs mt-2" style={{ color: 'var(--color-text-muted)' }}>
                    Use this hash to independently verify the evidence bundle
                </p>
            </div>

            {/* Overall Metrics */}
            <div className="grid grid-cols-4 gap-4">
                <div
                    className="rounded-xl p-4 text-center"
                    style={{ background: 'var(--color-accent-soft)' }}
                >
                    <p className="text-2xl font-bold font-mono" style={{ color: 'var(--color-accent)' }}>
                        {(bundle.overall_poi_agreement * 100).toFixed(0)}%
                    </p>
                    <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>PoI Agreement</p>
                </div>
                <div
                    className="rounded-xl p-4 text-center"
                    style={{ background: 'var(--color-success-soft)' }}
                >
                    <p className="text-2xl font-bold font-mono" style={{ color: 'var(--color-success)' }}>
                        {bundle.overall_pouw_score.toFixed(2)}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>PoUW Score</p>
                </div>
                <div
                    className="rounded-xl p-4 text-center"
                    style={{ background: 'var(--color-bg)', border: '1px solid var(--color-border)' }}
                >
                    <p className="text-2xl font-bold font-mono" style={{ color: 'var(--color-text)' }}>
                        {bundle.miners_responded || 0}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Miners</p>
                </div>
                <div
                    className="rounded-xl p-4 text-center"
                    style={{ background: 'var(--color-bg)', border: '1px solid var(--color-border)' }}
                >
                    <p className="text-2xl font-bold font-mono" style={{ color: 'var(--color-text)' }}>
                        {bundle.claims?.length || 0}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Claims</p>
                </div>
            </div>

            {/* Network Metadata */}
            {bundle.network_metadata && (
                <div
                    className="rounded-xl p-4"
                    style={{
                        background: 'var(--color-bg)',
                        border: '1px solid var(--color-border)',
                    }}
                >
                    <h4 className="text-xs font-semibold uppercase tracking-wide mb-3" style={{ color: 'var(--color-text-muted)' }}>
                        Network Metadata
                    </h4>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                            <span style={{ color: 'var(--color-text-muted)' }}>Network:</span>
                            <span className="ml-2 font-mono" style={{ color: 'var(--color-accent)' }}>
                                {bundle.network_metadata.network_used}
                            </span>
                        </div>
                        <div>
                            <span style={{ color: 'var(--color-text-muted)' }}>Quorum Target:</span>
                            <span className="ml-2 font-mono" style={{ color: 'var(--color-text)' }}>
                                {bundle.network_metadata.miner_quorum_target}
                            </span>
                        </div>
                        <div>
                            <span style={{ color: 'var(--color-text-muted)' }}>Fallback:</span>
                            <span className="ml-2 font-mono" style={{ color: 'var(--color-text)' }}>
                                {bundle.network_metadata.fallback_attempted ? 'Yes' : 'No'}
                            </span>
                        </div>
                    </div>
                </div>
            )}

            {/* Per-Claim Raw Data */}
            <div>
                <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--color-text)' }}>
                    Per-Claim Evidence ({bundle.claims?.length || 0})
                </h3>
                <div className="space-y-4">
                    {bundle.claims?.map((claim) => (
                        <MinerResponseCard key={claim.id} claim={claim} />
                    ))}
                </div>
            </div>

            {/* Raw JSON (Collapsible) */}
            <details
                className="rounded-xl overflow-hidden"
                style={{
                    background: 'var(--color-bg)',
                    border: '1px solid var(--color-border)',
                }}
            >
                <summary
                    className="px-4 py-3 cursor-pointer font-medium text-sm"
                    style={{ color: 'var(--color-text-secondary)' }}
                >
                    📄 View Raw JSON Bundle
                </summary>
                <pre
                    className="p-4 text-xs overflow-auto max-h-96"
                    style={{
                        background: 'var(--color-bg-secondary)',
                        color: 'var(--color-text-muted)',
                    }}
                >
                    {JSON.stringify(bundle, null, 2)}
                </pre>
            </details>
        </div>
    );
}

export default AuditorView;
