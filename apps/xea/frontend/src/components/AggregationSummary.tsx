import React from 'react';
import { EvidenceBundle, ClaimAggregation } from '../api';
import { PoITooltip, PoUWTooltip } from './Tooltip';

interface AggregationSummaryProps {
    bundle: EvidenceBundle;
}

function getRecommendationColor(rec: string): string {
    switch (rec) {
        case 'supported': return 'text-verdict-supported';
        case 'disputed': return 'text-verdict-disputed';
        case 'supported_with_caution': return 'text-verdict-caution';
        default: return 'text-gray-400';
    }
}

function getOverallVerdict(bundle: EvidenceBundle): {
    label: string;
    color: string;
    description: string;
} {
    const poi = bundle.overall_poi_agreement;
    const pouw = bundle.overall_pouw_score;

    if (poi >= 0.8 && pouw >= 0.7) {
        return {
            label: 'Safe to Vote',
            color: 'bg-verdict-supported',
            description: 'High agreement and quality scores indicate reliable verification.',
        };
    } else if (poi < 0.5 || pouw < 0.5) {
        return {
            label: 'Requires Revision',
            color: 'bg-verdict-disputed',
            description: 'Significant disagreement or quality concerns detected.',
        };
    } else {
        return {
            label: 'Vote with Caution',
            color: 'bg-verdict-caution',
            description: 'Mixed signals suggest additional review may be beneficial.',
        };
    }
}

function ClaimCard({ claim }: { claim: ClaimAggregation }) {
    const recColor = getRecommendationColor(claim.final_recommendation);
    const recLabel = claim.final_recommendation.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    const ciRange = (claim.pouw_ci_95[1] - claim.pouw_ci_95[0]) / 2;

    return (
        <div className="bg-xea-bg-secondary rounded-lg p-4 border border-xea-border">
            <div className="flex items-start justify-between mb-3">
                <div>
                    <span className="text-xea-accent font-semibold">{claim.id.toUpperCase()}</span>
                    {claim.text && (
                        <p className="text-sm text-gray-300 mt-1 line-clamp-2">{claim.text}</p>
                    )}
                </div>
                <span className={`text-sm font-semibold ${recColor}`}>
                    {recLabel}
                </span>
            </div>

            <div className="grid grid-cols-3 gap-3">
                <PoITooltip>
                    <div className="metric-card cursor-help">
                        <span className="metric-value text-xl">
                            {Math.round(claim.poi_agreement * 100)}%
                        </span>
                        <span className="metric-label">PoI Agreement</span>
                    </div>
                </PoITooltip>

                <PoUWTooltip>
                    <div className="metric-card cursor-help">
                        <span className="metric-value text-xl">
                            {claim.pouw_mean.toFixed(2)}
                            <span className="text-sm text-gray-400 font-normal ml-1">
                                ±{ciRange.toFixed(2)}
                            </span>
                        </span>
                        <span className="metric-label">PoUW Score</span>
                    </div>
                </PoUWTooltip>

                <div className="metric-card">
                    <span className="metric-value text-xl">{claim.miner_responses.length}</span>
                    <span className="metric-label">Validators</span>
                </div>
            </div>

            {claim.outliers.length > 0 && (
                <div className="mt-3 text-xs text-verdict-caution">
                    ⚠️ Outliers detected: {claim.outliers.join(', ')}
                </div>
            )}
        </div>
    );
}

export function AggregationSummary({ bundle }: AggregationSummaryProps) {
    const verdict = getOverallVerdict(bundle);
    const overallCiRange = (bundle.overall_ci_95[1] - bundle.overall_ci_95[0]) / 2;

    return (
        <div className="card space-y-6">
            <h3 className="text-lg font-semibold">Aggregation Results</h3>

            {/* Overall Proposal Verdict */}
            <div className={`${verdict.color} rounded-lg p-6 text-center`}>
                <p className="text-sm text-black/70 mb-1">Governance Recommendation</p>
                <h2 className="text-2xl font-bold text-black mb-2">{verdict.label}</h2>
                <p className="text-sm text-black/80">{verdict.description}</p>
            </div>

            {/* Overall Metrics */}
            <div className="grid grid-cols-2 gap-4">
                <PoITooltip>
                    <div className="metric-card cursor-help">
                        <span className="metric-value gradient-text">
                            {Math.round(bundle.overall_poi_agreement * 100)}%
                        </span>
                        <span className="metric-label">Overall PoI Agreement</span>
                    </div>
                </PoITooltip>

                <PoUWTooltip>
                    <div className="metric-card cursor-help">
                        <span className="metric-value gradient-text">
                            {bundle.overall_pouw_score.toFixed(2)}
                            <span className="text-lg text-gray-400 font-normal ml-1">
                                ±{overallCiRange.toFixed(2)}
                            </span>
                        </span>
                        <span className="metric-label">Overall PoUW Score</span>
                    </div>
                </PoUWTooltip>
            </div>

            {/* Critical Flags */}
            {bundle.critical_flags.length > 0 && (
                <div className="bg-verdict-disputed/10 border border-verdict-disputed/30 rounded-lg p-4">
                    <h4 className="text-verdict-disputed font-semibold mb-2">⚠️ Critical Flags</h4>
                    <ul className="text-sm text-gray-300 space-y-1">
                        {bundle.critical_flags.map((flag, i) => (
                            <li key={i}>• {flag}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Per-Claim Cards */}
            <div>
                <h4 className="text-sm text-gray-400 mb-3">Per-Claim Analysis</h4>
                <div className="space-y-3">
                    {bundle.claims.map((claim) => (
                        <ClaimCard key={claim.id} claim={claim} />
                    ))}
                </div>
            </div>
        </div>
    );
}

export default AggregationSummary;
