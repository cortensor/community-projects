export type Verdict = 'true' | 'false' | 'uncertain';

export interface ClaimCheckRequest {
  claim: string;
  context_url?: string | null;
  context_text?: string | null;
  num_miners?: number;
  client_reference?: string | null;
}

export interface Citation {
  source: string;
  url: string | null;
  description?: string | null;
}

export interface MinerVote {
  miner_id: string;
  verdict: Verdict;
  confidence: number;
  notes?: string | null;
  citations?: Citation[];
}

export interface ClaimCheckResponse {
  verdict: Verdict;
  confidence: number;
  dispersion: number;
  reasoning: string;
  citations: Citation[];
  miner_votes?: MinerVote[];
  validation?: {
    verdict: 'normal' | 'abnormal' | 'inconclusive';
    score: number; // 0-10 evaluator score
    notes: string;
    task_id?: number;
    session_id?: number;
    status?: 'ok' | 'timeout' | 'error';
  };
  task_id?: number;
}
