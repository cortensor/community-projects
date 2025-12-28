/**
 * Xea Governance Oracle - API Client
 * 
 * TypeScript client for interacting with the backend API.
 */

import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ============================================================================
// Base Types
// ============================================================================

export interface ClaimCanonical {
    numbers: number[];
    addresses: string[];
    urls: string[];
}

export interface Claim {
    id: string;
    text: string;
    paragraph_index: number;
    char_range: [number, number];
    type: 'factual' | 'numeric' | 'temporal' | 'comparative' | 'procedural' | 'conditional';
    canonical: ClaimCanonical;
}

export interface MinerScores {
    accuracy: number;
    omission_risk: number;
    evidence_quality: number;
    governance_relevance: number;
    composite: number;
}

export interface MinerResponse {
    miner_id: string;
    claim_id: string;
    verdict: 'verified' | 'refuted' | 'unverifiable' | 'partial';
    rationale: string;
    evidence_links: string[];
    embedding?: number[];
    scores: MinerScores;
}

// ============================================================================
// Versioning Types
// ============================================================================

export interface ClaimDiffItem {
    claim_id: string;
    status: 'unchanged' | 'modified' | 'new' | 'removed';
    similarity_score?: number;
    prev_claim_text?: string;
    curr_claim_text?: string;
    numeric_delta?: Record<string, number>;
}

export interface ClaimDiff {
    unchanged: string[];
    modified: ClaimDiffItem[];
    new: string[];
    removed: string[];
}

export interface ProposalVersion {
    proposal_id: string;
    version_number: number;
    proposal_hash: string;
    previous_hash?: string;
    created_at: string;
    claim_ids: string[];
}

export interface ProposalHistory {
    proposal_id: string;
    versions: ProposalVersion[];
    latest_version: number;
}

// ============================================================================
// Ingest Types
// ============================================================================

export interface IngestRequest {
    url?: string;
    text?: string;
    previous_proposal_id?: string;  // For versioning
}

export interface IngestResponse {
    proposal_id: string;
    version_number: number;
    proposal_hash: string;
    previous_hash?: string;
    canonical_text: string;
    claims: Claim[];
    claim_diff?: ClaimDiff;
}

// ============================================================================
// Validation Types
// ============================================================================

export interface ValidateRequest {
    proposal_hash: string;
}

export interface ValidateResponse {
    job_id: string;
    proposal_hash: string;
    status: 'queued' | 'running' | 'completed' | 'failed';
    created_at: string;
    estimated_completion?: string;
}

export interface JobProgress {
    claims_total: number;
    claims_validated: number;
    miners_contacted: number;
    miners_responded: number;
}

export interface StatusResponse {
    job_id: string;
    status: 'queued' | 'running' | 'completed' | 'failed';
    progress: JobProgress;
    partial_results: MinerResponse[];
    started_at?: string;
    updated_at?: string;
    completed_at?: string;
    ready_for_aggregation: boolean;
    // Stage tracking (NEW)
    current_stage?: string;
    retries_attempted?: number;
    last_heartbeat?: string;
    quorum_target?: number;
}

// ============================================================================
// Aggregation Types
// ============================================================================

export interface ClaimAggregation {
    id: string;
    text: string;
    poi_agreement: number;
    mode_verdict: string;
    embedding_dispersion: number;
    pouw_mean: number;
    pouw_ci_95: [number, number];
    outliers: string[];
    final_recommendation: 'supported' | 'disputed' | 'supported_with_caution';
    miner_responses: MinerResponse[];
    was_revalidated?: boolean;  // NEW: true if this claim was revalidated (vs inherited)
}

export interface EvidenceBundle {
    proposal_hash: string;
    job_id: string;
    // Versioning metadata (NEW)
    proposal_id?: string;
    version_number?: number;
    claim_diff?: ClaimDiff;
    validation_scope?: 'full' | 'selective';
    revalidated_claims?: string[];
    // Claims
    claims: ClaimAggregation[];
    overall_poi_agreement: number;
    overall_pouw_score: number;
    overall_ci_95: [number, number];
    critical_flags: string[];
    timestamp: string;
    // Resilience metadata
    redundancy_level?: 'full' | 'reduced' | 'minimal';
    miners_requested?: number;
    miners_responded?: number;
    missing_miners?: string[];
    confidence_adjustment_factor?: number;
    // Verification
    computation_hash?: string;
    replay_version?: string;
    verification_instructions?: {
        algorithm: string;
        components: string[];
        cli_command: string;
    };
    // Network metadata (NEW)
    network_metadata?: {
        network_used: string;
        fallback_attempted: boolean;
        miner_quorum_target: number;
    };
}

// ============================================================================
// View Types
// ============================================================================

export type ViewRole = 'voter' | 'delegate' | 'auditor';

export interface VoterViewData {
    proposal_hash: string;
    risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
    recommendation: 'Approve' | 'Caution' | 'Reject';
    key_flags: string[];
    rubric_id?: string;
}

export interface DelegateClaimView {
    id: string;
    text: string;
    verdict: string;
    recommendation: string;
    poi_agreement: number;
    pouw_mean: number;
    pouw_ci_95: [number, number];
    has_disagreement: boolean;
}

export interface DelegateViewData {
    proposal_hash: string;
    claims: DelegateClaimView[];
    overall_poi_agreement: number;
    overall_pouw_score: number;
    overall_ci_95: [number, number];
    flags: string[];
    rubric_id?: string;
}

export interface AggregateRequest {
    job_id: string;
    publish?: boolean;
}

export interface AggregateResponse {
    job_id: string;
    evidence_bundle: EvidenceBundle;
    ipfs_cid?: string;
}

export interface AttestRequest {
    job_id: string;
    publish?: boolean;
}

export interface AttestResponse {
    job_id: string;
    proposal_hash: string;
    ipfs_cid?: string;
    signature: string;
    signer: string;
    message_hash: string;
    verification_instructions: {
        step_1: string;
        step_2: string;
        step_3: string;
        step_4: string;
    };
}

// ============================================================================
// WebSocket Types
// ============================================================================

export interface WSMinerResponseMessage {
    type: 'miner_response';
    job_id: string;
    claim_id: string;
    miner_id: string;
    verdict: string;
    timestamp: string;
}

export interface WSStatusMessage {
    type: 'status';
    job_id: string;
    status: string;
    progress: JobProgress;
}

export interface WSAggregateMessage {
    type: 'aggregate';
    job_id: string;
    evidence_bundle: EvidenceBundle;
}

export type WSMessage = WSMinerResponseMessage | WSStatusMessage | WSAggregateMessage;

// ============================================================================
// API Client
// ============================================================================

class XeaApiClient {
    private client: AxiosInstance;

    constructor(baseURL: string = API_BASE_URL) {
        this.client = axios.create({
            baseURL,
            headers: {
                'Content-Type': 'application/json',
            },
        });
    }

    /**
     * Ingest a proposal from URL or text
     */
    async ingest(request: IngestRequest): Promise<IngestResponse> {
        const response = await this.client.post<IngestResponse>('/ingest', request);
        return response.data;
    }

    /**
     * Get proposal version history
     */
    async getProposalHistory(proposalId: string): Promise<ProposalHistory> {
        const response = await this.client.get<ProposalHistory>(`/proposal/${proposalId}/history`);
        return response.data;
    }

    /**
     * Start validation job for a proposal
     */
    async validate(request: ValidateRequest): Promise<ValidateResponse> {
        const response = await this.client.post<ValidateResponse>('/validate', request);
        return response.data;
    }

    /**
     * Get status of a validation job
     */
    async getStatus(jobId: string): Promise<StatusResponse> {
        const response = await this.client.get<StatusResponse>(`/status/${jobId}`);
        return response.data;
    }

    /**
     * Aggregate validation results into evidence bundle
     */
    async aggregate(request: AggregateRequest): Promise<AggregateResponse> {
        const response = await this.client.post<AggregateResponse>('/aggregate', request);
        return response.data;
    }

    /**
     * Create attestation for evidence bundle
     */
    async attest(request: AttestRequest): Promise<AttestResponse> {
        const response = await this.client.post<AttestResponse>('/attest', request);
        return response.data;
    }

    /**
     * Get evidence bundle by job ID with optional view
     */
    async getEvidence(jobId: string, view?: ViewRole): Promise<EvidenceBundle | VoterViewData | DelegateViewData> {
        const url = view ? `/evidence/${jobId}?view=${view}` : `/evidence/${jobId}`;
        const response = await this.client.get(url);
        return response.data;
    }

    /**
     * Get voter view (simplified)
     */
    async getVoterView(jobId: string): Promise<VoterViewData> {
        return this.getEvidence(jobId, 'voter') as Promise<VoterViewData>;
    }

    /**
     * Get delegate view (detailed)
     */
    async getDelegateView(jobId: string): Promise<DelegateViewData> {
        return this.getEvidence(jobId, 'delegate') as Promise<DelegateViewData>;
    }

    /**
     * Health check
     */
    async health(): Promise<{ status: string; version: string }> {
        const response = await this.client.get('/health');
        return response.data;
    }

    /**
     * Get validation history list
     */
    async getHistory(limit: number = 50, offset: number = 0): Promise<HistoryItem[]> {
        const response = await this.client.get<HistoryItem[]>('/history', {
            params: { limit, offset }
        });
        return response.data;
    }

    /**
     * Get recent history for home page
     */
    async getRecentHistory(limit: number = 3): Promise<HistoryItem[]> {
        const response = await this.client.get<HistoryItem[]>('/history/recent', {
            params: { limit }
        });
        return response.data;
    }

    /**
     * Get a specific history item
     */
    async getHistoryItem(jobId: string): Promise<HistoryItem> {
        const response = await this.client.get<HistoryItem>(`/history/${jobId}`);
        return response.data;
    }

    /**
     * Save a history item
     */
    async saveHistory(data: {
        job_id: string;
        proposal_id?: string;
        version_number?: number;
        proposal_hash: string;
        proposal_title?: string;
        claims_count?: number;
        status?: string;
        overall_verdict?: string;
        confidence_score?: number;
        ipfs_cid?: string;
        network_used?: string;
    }): Promise<{ status: string }> {
        const response = await this.client.post('/history', null, { params: data });
        return response.data;
    }
}

// History item type
export interface HistoryItem {
    job_id: string;
    proposal_hash: string;
    proposal_title?: string;
    created_at: string;
    completed_at?: string;
    status: string;
    claims_count: number;
    overall_verdict?: string;
    confidence_score?: number;
    ipfs_cid?: string;
    network_used?: string;
    evidence_json?: EvidenceBundle;
}

export const api = new XeaApiClient();
export const WS_BASE_URL = API_BASE_URL.replace('http', 'ws');
export default api;
