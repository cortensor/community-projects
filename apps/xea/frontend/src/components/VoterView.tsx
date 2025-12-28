/**
 * VoterView - Clean, focused dashboard for quick governance decisions
 */

import { VoterViewData } from '../api';

interface VoterViewProps {
    data: VoterViewData;
}

const riskConfig = {
    LOW: {
        gradient: 'linear-gradient(135deg, #059669, #10b981)',
        bgSoft: 'rgba(16, 185, 129, 0.15)',
        color: '#10b981',
        icon: '✓',
        label: 'Low Risk',
        description: 'Claims verified with high confidence',
    },
    MEDIUM: {
        gradient: 'linear-gradient(135deg, #d97706, #f59e0b)',
        bgSoft: 'rgba(245, 158, 11, 0.15)',
        color: '#f59e0b',
        icon: '⚡',
        label: 'Medium Risk',
        description: 'Some claims require attention',
    },
    HIGH: {
        gradient: 'linear-gradient(135deg, #dc2626, #ef4444)',
        bgSoft: 'rgba(239, 68, 68, 0.15)',
        color: '#ef4444',
        icon: '⚠',
        label: 'High Risk',
        description: 'Critical issues detected',
    },
};

const recommendationConfig = {
    Approve: {
        gradient: 'linear-gradient(135deg, #059669, #10b981)',
        icon: '✓',
        text: 'Approve',
    },
    Caution: {
        gradient: 'linear-gradient(135deg, #d97706, #f59e0b)',
        icon: '⚡',
        text: 'Vote with Caution',
    },
    Reject: {
        gradient: 'linear-gradient(135deg, #dc2626, #ef4444)',
        icon: '✕',
        text: 'Consider Rejecting',
    },
};

export const VoterView = ({ data }: VoterViewProps) => {
    const risk = riskConfig[data.risk_level];
    const rec = recommendationConfig[data.recommendation];

    return (
        <div className="space-y-6">
            {/* Hero Section - Recommendation + Risk */}
            <div
                className="rounded-2xl p-6 text-center relative overflow-hidden"
                style={{ background: rec.gradient }}
            >
                <div className="relative z-10">
                    <p className="text-white/70 text-xs uppercase tracking-wider mb-2">Recommendation</p>
                    <div className="flex items-center justify-center gap-3">
                        <span className="text-4xl">{rec.icon}</span>
                        <h2 className="text-3xl font-bold text-white">{rec.text}</h2>
                    </div>
                    <div className="mt-4 flex items-center justify-center gap-2">
                        <span
                            className="px-3 py-1 rounded-full text-sm font-medium"
                            style={{ background: 'rgba(255,255,255,0.2)', color: 'white' }}
                        >
                            {risk.icon} {risk.label}
                        </span>
                    </div>
                </div>
                {/* Background decoration */}
                <div
                    className="absolute top-0 right-0 w-48 h-48 rounded-full opacity-20"
                    style={{
                        background: 'radial-gradient(circle, white 0%, transparent 70%)',
                        transform: 'translate(30%, -30%)'
                    }}
                />
            </div>

            {/* Key Findings */}
            {data.key_flags.length > 0 ? (
                <div
                    className="rounded-xl p-5"
                    style={{
                        background: 'var(--color-bg)',
                        border: '1px solid var(--color-border)',
                    }}
                >
                    <div className="flex items-center gap-2 mb-4">
                        <span className="text-lg">🔍</span>
                        <h3 className="font-semibold" style={{ color: 'var(--color-text)' }}>
                            Key Findings
                        </h3>
                        <span
                            className="ml-auto text-xs px-2 py-1 rounded-full font-medium"
                            style={{ background: risk.bgSoft, color: risk.color }}
                        >
                            {data.key_flags.length} items
                        </span>
                    </div>
                    <div className="space-y-3">
                        {data.key_flags.map((flag, idx) => (
                            <div
                                key={idx}
                                className="flex items-start gap-3 p-3 rounded-lg"
                                style={{
                                    background: 'var(--color-bg-secondary)',
                                    border: '1px solid var(--color-border-subtle)',
                                }}
                            >
                                <span
                                    className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                                    style={{ background: 'var(--color-accent-soft)', color: 'var(--color-accent)' }}
                                >
                                    {idx + 1}
                                </span>
                                <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                                    {flag}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            ) : (
                <div
                    className="rounded-xl p-6 text-center"
                    style={{
                        background: 'var(--color-success-soft)',
                        border: '1px solid rgba(16, 185, 129, 0.2)',
                    }}
                >
                    <span className="text-2xl mb-2 block">✓</span>
                    <p className="font-medium" style={{ color: 'var(--color-success)' }}>
                        No critical flags detected
                    </p>
                    <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
                        Claims appear well-supported
                    </p>
                </div>
            )}

            {/* Bottom Info */}
            <div className="text-center pt-2">
                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                    💡 Switch to <strong>Delegate</strong> view for detailed claim-by-claim analysis
                </p>
            </div>
        </div>
    );
};

export default VoterView;
