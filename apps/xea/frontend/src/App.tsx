import { useState, useEffect } from 'react';
import { api, IngestResponse, EvidenceBundle, MinerResponse, JobProgress, ViewRole, VoterViewData, ProposalHistory } from './api';
import { useJobStream } from './hooks/useJobStream';
import { ProposalInput } from './components/ProposalInput';
import { ClaimsTable } from './components/ClaimsTable';
import { LiveMinerPanel } from './components/LiveMinerPanel';
import { AggregationSummary } from './components/AggregationSummary';
import { EvidencePanel } from './components/EvidencePanel';
import { ViewToggle } from './components/ViewToggle';
import { VoterView } from './components/VoterView';
import { AuditorView } from './components/AuditorView';
import { RedundancyIndicator } from './components/RedundancyIndicator';
import { VerificationPanel } from './components/VerificationPanel';
import { ThemeToggle } from './components/ThemeToggle';
import { ClaimDiffSummary } from './components/ClaimDiffSummary';
import { Navigation } from './components/Navigation';
import { DocsPage } from './components/DocsPage';
import { HistoryPage } from './components/HistoryPage';
import { LandingPage } from './components/LandingPage';
import { RecentHistory } from './components/RecentHistory';

type AppStage = 'input' | 'validating' | 'aggregating' | 'complete';
type AppTab = 'home' | 'docs' | 'history';

function App() {
    // Landing page state
    const [showLanding, setShowLanding] = useState(true);

    // Navigation tab
    const [activeTab, setActiveTab] = useState<AppTab>('home');

    const [stage, setStage] = useState<AppStage>('input');
    const [proposal, setProposal] = useState<IngestResponse | null>(null);
    const [jobId, setJobId] = useState<string | null>(null);
    const [evidenceBundle, setEvidenceBundle] = useState<EvidenceBundle | null>(null);
    const [ipfsCid, setIpfsCid] = useState<string | undefined>();
    const [error, setError] = useState<string | null>(null);

    // View role for evidence display
    const [viewRole, setViewRole] = useState<ViewRole>('delegate');
    const [voterViewData, setVoterViewData] = useState<VoterViewData | null>(null);

    // Versioning state (NEW)
    const [proposalHistory, setProposalHistory] = useState<ProposalHistory | null>(null);

    // WebSocket for live updates
    const stream = useJobStream(stage === 'validating' ? jobId : null);

    // Polling fallback for status (WebSocket may not always be available)
    const [polledProgress, setPolledProgress] = useState<JobProgress | null>(null);
    const [polledResponses, setPolledResponses] = useState<MinerResponse[]>([]);

    // Stage tracking for progress visibility (NEW)
    const [currentStage, setCurrentStage] = useState<string>('received');
    const [retriesAttempted, setRetriesAttempted] = useState<number>(0);
    const [lastHeartbeat, setLastHeartbeat] = useState<string>('');

    const minerResponses = stream.connected ? stream.minerResponses :
        new Map<string, MinerResponse[]>(
            Object.entries(
                polledResponses.reduce((acc, r) => {
                    if (!acc[r.claim_id]) acc[r.claim_id] = [];
                    acc[r.claim_id].push(r);
                    return acc;
                }, {} as Record<string, MinerResponse[]>)
            )
        );

    const progress = stream.connected ? stream.progress : polledProgress || {
        claims_total: proposal?.claims.length || 0,
        claims_validated: 0,
        miners_contacted: 0,
        miners_responded: 0,
    };

    // Poll for status when not connected via WebSocket
    useEffect(() => {
        if (stage !== 'validating' || !jobId || stream.connected) return;

        const poll = async () => {
            try {
                const status = await api.getStatus(jobId);
                setPolledProgress(status.progress);
                setPolledResponses(status.partial_results);

                // Update stage tracking (NEW)
                if (status.current_stage) setCurrentStage(status.current_stage);
                if (status.retries_attempted !== undefined) setRetriesAttempted(status.retries_attempted);
                if (status.last_heartbeat) setLastHeartbeat(status.last_heartbeat);

                if (status.status === 'completed') {
                    handleValidationComplete();
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        };

        const interval = setInterval(poll, 2000);
        poll(); // Initial poll

        return () => clearInterval(interval);
    }, [stage, jobId, stream.connected]);

    // Handle WebSocket-based completion
    useEffect(() => {
        if (stream.status === 'completed' && stage === 'validating') {
            handleValidationComplete();
        }
    }, [stream.status]);

    const handleIngestComplete = async (result: IngestResponse, autoValidate: boolean) => {
        setProposal(result);
        setError(null);

        if (autoValidate) {
            try {
                const validateResponse = await api.validate({ proposal_hash: result.proposal_hash });
                setJobId(validateResponse.job_id);
                setStage('validating');
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Failed to start validation');
            }
        }
    };

    const handleValidationComplete = async () => {
        if (!jobId || !proposal) return;

        setStage('aggregating');

        try {
            const aggregateResponse = await api.aggregate({ job_id: jobId, publish: true });
            setEvidenceBundle(aggregateResponse.evidence_bundle);
            setIpfsCid(aggregateResponse.ipfs_cid);
            setStage('complete');

            // Save to history
            try {
                await api.saveHistory({
                    job_id: jobId,
                    proposal_id: proposal.proposal_id,
                    version_number: proposal.version_number,
                    proposal_hash: proposal.proposal_hash,
                    proposal_title: proposal.canonical_text.slice(0, 100),
                    claims_count: proposal.claims.length,
                    status: 'completed',
                    overall_verdict: aggregateResponse.evidence_bundle.overall_poi_agreement > 0.7 ? 'verified' :
                        aggregateResponse.evidence_bundle.overall_poi_agreement > 0.4 ? 'partial' : 'disputed',
                    confidence_score: aggregateResponse.evidence_bundle.overall_poi_agreement,
                    ipfs_cid: aggregateResponse.ipfs_cid,
                    network_used: aggregateResponse.evidence_bundle.network_metadata?.network_used,
                });
            } catch (historyErr) {
                console.error('Failed to save history:', historyErr);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to aggregate results');
            setStage('validating');
        }
    };

    const getClaimStatuses = (): Map<string, 'pending' | 'validating' | 'completed'> => {
        const statuses = new Map<string, 'pending' | 'validating' | 'completed'>();
        if (!proposal) return statuses;

        proposal.claims.forEach(claim => {
            const responses = minerResponses.get(claim.id) || [];
            if (stage === 'complete' || (evidenceBundle && evidenceBundle.claims.find(c => c.id === claim.id))) {
                statuses.set(claim.id, 'completed');
            } else if (responses.length > 0) {
                statuses.set(claim.id, 'validating');
            } else {
                statuses.set(claim.id, 'pending');
            }
        });

        return statuses;
    };

    const handleReset = () => {
        setStage('input');
        setProposal(null);
        setJobId(null);
        setEvidenceBundle(null);
        setIpfsCid(undefined);
        setError(null);
        setPolledProgress(null);
        setPolledResponses([]);
        setViewRole('delegate');
        setVoterViewData(null);
        setProposalHistory(null);
    };

    // Fetch voter view when switching to voter role
    useEffect(() => {
        if (stage === 'complete' && jobId && viewRole === 'voter' && !voterViewData) {
            api.getVoterView(jobId)
                .then(setVoterViewData)
                .catch(console.error);
        }
    }, [viewRole, stage, jobId, voterViewData]);

    // Fetch proposal history when we have a proposal_id
    useEffect(() => {
        if (proposal?.proposal_id && !proposalHistory) {
            api.getProposalHistory(proposal.proposal_id)
                .then(setProposalHistory)
                .catch(console.error);
        }
    }, [proposal?.proposal_id, proposalHistory]);

    // Show landing page first
    if (showLanding) {
        return <LandingPage onStart={() => setShowLanding(false)} />;
    }

    return (
        <div className="min-h-screen" style={{ background: 'var(--color-bg)' }}>
            {/* Navigation Header */}
            <Navigation activeTab={activeTab} onTabChange={setActiveTab} />

            {/* Theme Toggle - Fixed position */}
            <div className="fixed top-4 right-4 z-50">
                <ThemeToggle />
            </div>

            {/* Main Content Area - Conditional Layout */}
            <main className="max-w-7xl mx-auto px-6 py-8">
                {/* Non-Complete Stages: Simple centered container */}
                {(activeTab !== 'home' || stage !== 'complete') && (
                    <div
                        className="max-w-4xl mx-auto rounded-2xl p-6 md:p-8"
                        style={{
                            background: 'var(--color-bg-secondary)',
                            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12), 0 0 1px rgba(0, 0, 0, 0.1)',
                            border: '1px solid var(--color-border)',
                        }}
                    >
                        {/* Tab Content */}
                        {activeTab === 'docs' && <DocsPage />}
                        {activeTab === 'history' && <HistoryPage />}
                        {activeTab === 'home' && stage !== 'complete' && (
                            <div className="space-y-6">
                                {/* Stage Indicator */}
                                {stage !== 'input' && (
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-4">
                                            <Step number={1} label="Ingest" active={false} complete={true} />
                                            <Connector complete={true} />
                                            <Step
                                                number={2}
                                                label="Validate"
                                                active={stage === 'validating'}
                                                complete={stage === 'aggregating'}
                                            />
                                            <Connector complete={stage === 'aggregating'} />
                                            <Step
                                                number={3}
                                                label="Results"
                                                active={stage === 'aggregating'}
                                                complete={false}
                                            />
                                        </div>
                                        <button onClick={handleReset} className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                                            Start Over
                                        </button>
                                    </div>
                                )}

                                {/* Error Display */}
                                {error && (
                                    <div
                                        className="rounded-lg p-4"
                                        style={{
                                            background: 'var(--color-danger-soft)',
                                            border: '1px solid rgba(239, 68, 68, 0.3)',
                                            color: 'var(--color-danger)',
                                        }}
                                    >
                                        {error}
                                    </div>
                                )}

                                {/* Proposal Input (Stage 1) */}
                                {stage === 'input' && (
                                    <section>
                                        <h2 className="text-xl font-semibold mb-4" style={{ color: 'var(--color-text)' }}>
                                            📥 Verify a DAO Proposal
                                        </h2>
                                        <ProposalInput onIngestComplete={handleIngestComplete} />

                                        {/* Recent History on Home Page */}
                                        <RecentHistory onViewHistory={() => setActiveTab('history')} />
                                    </section>
                                )}

                                {/* Claims Table (shown during validation) */}
                                {proposal && stage !== 'input' && (
                                    <section>
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="flex items-center gap-3">
                                                <h2 className="text-xl font-semibold" style={{ color: 'var(--color-text)' }}>
                                                    📋 Extracted Claims
                                                </h2>
                                                {/* Version Badge */}
                                                {proposal.version_number && proposal.version_number > 1 && (
                                                    <span
                                                        className="px-2 py-1 rounded text-xs font-bold"
                                                        style={{
                                                            background: 'var(--color-accent-soft)',
                                                            color: 'var(--color-accent)',
                                                        }}
                                                    >
                                                        v{proposal.version_number}
                                                    </span>
                                                )}
                                            </div>
                                        </div>

                                        {/* Claim Diff Summary - shows what changed from previous version */}
                                        {proposal.claim_diff && proposal.version_number && proposal.version_number > 1 && (
                                            <div className="mb-4">
                                                <ClaimDiffSummary
                                                    diff={proposal.claim_diff}
                                                    versionNumber={proposal.version_number}
                                                />
                                            </div>
                                        )}

                                        <ClaimsTable
                                            claims={proposal.claims}
                                            claimStatuses={getClaimStatuses()}
                                            minerResponses={minerResponses}
                                            totalMiners={5}
                                            claimDiff={proposal.claim_diff}
                                        />
                                    </section>
                                )}

                                {/* Live Miner Panel (Stage 2) */}
                                {stage === 'validating' && proposal && (
                                    <section>
                                        <LiveMinerPanel
                                            claims={proposal.claims}
                                            progress={progress}
                                            minerResponses={minerResponses}
                                            status={stream.connected ? stream.status : 'running'}
                                            connected={stream.connected}
                                            currentStage={currentStage}
                                            retriesAttempted={retriesAttempted}
                                            lastHeartbeat={lastHeartbeat}
                                        />
                                    </section>
                                )}

                                {/* Loading state during aggregation */}
                                {stage === 'aggregating' && (
                                    <div className="card text-center py-12">
                                        <svg className="animate-spin h-10 w-10 mx-auto mb-4" style={{ color: 'var(--color-accent)' }} viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                        </svg>
                                        <p style={{ color: 'var(--color-text-muted)' }}>Aggregating miner responses...</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* Complete Stage: Two-Box Layout (Main Left + Evidence Right) */}
                {activeTab === 'home' && stage === 'complete' && evidenceBundle && (
                    <div className="grid lg:grid-cols-4 gap-6">
                        {/* LEFT: Main Content Box (3/4 width) */}
                        <div
                            className="lg:col-span-3 rounded-2xl p-6 md:p-8"
                            style={{
                                background: 'var(--color-bg-secondary)',
                                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12), 0 0 1px rgba(0, 0, 0, 0.1)',
                                border: '1px solid var(--color-border)',
                            }}
                        >
                            <div className="space-y-6">
                                {/* Header with View Toggle */}
                                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                                    <div className="flex items-center gap-3">
                                        <span className="text-2xl">📊</span>
                                        <div>
                                            <h2 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>
                                                Verification Results
                                            </h2>
                                            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                                                {evidenceBundle.claims?.length || 0} claims verified via Cortensor
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <ViewToggle value={viewRole} onChange={setViewRole} />
                                        <button
                                            onClick={handleReset}
                                            className="text-sm px-3 py-1.5 rounded-lg"
                                            style={{
                                                background: 'var(--color-bg)',
                                                color: 'var(--color-text-muted)',
                                                border: '1px solid var(--color-border)',
                                            }}
                                        >
                                            New Validation
                                        </button>
                                    </div>
                                </div>

                                {/* Redundancy Status */}
                                {evidenceBundle.redundancy_level && (
                                    <RedundancyIndicator
                                        level={evidenceBundle.redundancy_level}
                                        minersRequested={evidenceBundle.miners_requested}
                                        minersResponded={evidenceBundle.miners_responded}
                                        confidenceAdjustment={evidenceBundle.confidence_adjustment_factor}
                                    />
                                )}

                                {/* Role-based content - subtle fade for seamless switching */}
                                <div
                                    key={viewRole}
                                    className="animate-fadeIn"
                                    style={{ minHeight: '400px' }}
                                >
                                    {viewRole === 'voter' && voterViewData ? (
                                        <VoterView data={voterViewData} />
                                    ) : viewRole === 'auditor' ? (
                                        <AuditorView bundle={evidenceBundle} />
                                    ) : (
                                        <AggregationSummary bundle={evidenceBundle} />
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* RIGHT: Evidence Sidebar Box (1/4 width) */}
                        <div className="lg:col-span-1">
                            <div
                                className="sticky top-24 rounded-2xl p-5 space-y-5"
                                style={{
                                    background: 'var(--color-bg-secondary)',
                                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12), 0 0 1px rgba(0, 0, 0, 0.1)',
                                    border: '1px solid var(--color-border)',
                                }}
                            >
                                {/* Header */}
                                <div className="flex items-center gap-2">
                                    <span className="text-lg">🔐</span>
                                    <h3 className="font-bold" style={{ color: 'var(--color-text)' }}>
                                        Evidence
                                    </h3>
                                </div>

                                {/* Evidence Panel */}
                                <EvidencePanel
                                    jobId={jobId!}
                                    bundle={evidenceBundle}
                                    ipfsCid={ipfsCid}
                                />

                                {/* Verification */}
                                {evidenceBundle.computation_hash && (
                                    <div
                                        className="pt-4"
                                        style={{ borderTop: '1px solid var(--color-border)' }}
                                    >
                                        <VerificationPanel
                                            computationHash={evidenceBundle.computation_hash}
                                            replayVersion={evidenceBundle.replay_version}
                                            cliCommand={evidenceBundle.verification_instructions?.cli_command}
                                        />
                                    </div>
                                )}

                                {/* Network Badge */}
                                <div
                                    className="rounded-lg p-3 text-center"
                                    style={{
                                        background: 'var(--color-success-soft)',
                                        border: '1px solid rgba(16, 185, 129, 0.2)',
                                    }}
                                >
                                    <p className="text-xs font-medium" style={{ color: 'var(--color-success)' }}>
                                        ✓ Verified on Cortensor
                                    </p>
                                    <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
                                        testnet0
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </main>

            {/* Footer */}
            <footer
                className="border-t mt-8"
                style={{ borderColor: 'var(--color-border)' }}
            >
                <div className="max-w-6xl mx-auto px-6 py-6 text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
                    Xea Governance Oracle v0.1.0 • Powered by decentralized inference on Cortensor
                </div>
            </footer>
        </div>
    );
}

// Helper components for stage indicator
function Step({ number, label, active, complete }: { number: number; label: string; active: boolean; complete: boolean }) {
    return (
        <div className="flex items-center gap-2">
            <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold`}
                style={{
                    background: complete
                        ? 'var(--color-success)'
                        : active
                            ? 'var(--color-accent)'
                            : 'var(--color-bg)',
                    color: complete || active ? 'white' : 'var(--color-text-muted)',
                    border: !complete && !active ? '1px solid var(--color-border)' : 'none',
                }}
            >
                {complete ? '✓' : number}
            </div>
            <span
                className="text-sm"
                style={{ color: active || complete ? 'var(--color-text)' : 'var(--color-text-muted)' }}
            >
                {label}
            </span>
        </div>
    );
}

function Connector({ complete }: { complete: boolean }) {
    return (
        <div
            className="w-8 h-0.5"
            style={{ background: complete ? 'var(--color-success)' : 'var(--color-border)' }}
        />
    );
}

export default App;
