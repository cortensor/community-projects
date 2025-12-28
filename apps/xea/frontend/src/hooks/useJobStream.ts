/**
 * WebSocket hook for streaming job updates
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { WS_BASE_URL, WSMessage, JobProgress, MinerResponse, EvidenceBundle } from '../api';

export interface JobStreamState {
    connected: boolean;
    status: 'queued' | 'running' | 'completed' | 'failed';
    progress: JobProgress;
    minerResponses: Map<string, MinerResponse[]>; // claim_id -> responses
    evidenceBundle: EvidenceBundle | null;
    error: string | null;
}

const initialProgress: JobProgress = {
    claims_total: 0,
    claims_validated: 0,
    miners_contacted: 0,
    miners_responded: 0,
};

export function useJobStream(jobId: string | null) {
    const [state, setState] = useState<JobStreamState>({
        connected: false,
        status: 'queued',
        progress: initialProgress,
        minerResponses: new Map(),
        evidenceBundle: null,
        error: null,
    });

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const connect = useCallback(() => {
        if (!jobId) return;

        // Close existing connection
        if (wsRef.current) {
            wsRef.current.close();
        }

        const ws = new WebSocket(`${WS_BASE_URL}/ws/jobs/${jobId}`);
        wsRef.current = ws;

        ws.onopen = () => {
            setState(prev => ({ ...prev, connected: true, error: null }));
        };

        ws.onmessage = (event) => {
            try {
                const message: WSMessage = JSON.parse(event.data);

                switch (message.type) {
                    case 'miner_response':
                        setState(prev => {
                            const newResponses = new Map(prev.minerResponses);
                            const claimResponses = newResponses.get(message.claim_id) || [];
                            // Add a partial response for display
                            claimResponses.push({
                                miner_id: message.miner_id,
                                claim_id: message.claim_id,
                                verdict: message.verdict as MinerResponse['verdict'],
                                rationale: '',
                                evidence_links: [],
                                scores: {
                                    accuracy: 0,
                                    omission_risk: 0,
                                    evidence_quality: 0,
                                    governance_relevance: 0,
                                    composite: 0,
                                },
                            });
                            newResponses.set(message.claim_id, claimResponses);
                            return {
                                ...prev,
                                minerResponses: newResponses,
                                progress: {
                                    ...prev.progress,
                                    miners_responded: prev.progress.miners_responded + 1,
                                },
                            };
                        });
                        break;

                    case 'status':
                        setState(prev => ({
                            ...prev,
                            status: message.status as JobStreamState['status'],
                            progress: message.progress,
                        }));
                        break;

                    case 'aggregate':
                        setState(prev => ({
                            ...prev,
                            status: 'completed',
                            evidenceBundle: message.evidence_bundle,
                        }));
                        break;
                }
            } catch (err) {
                console.error('Failed to parse WebSocket message:', err);
            }
        };

        ws.onerror = () => {
            setState(prev => ({ ...prev, error: 'WebSocket connection error' }));
        };

        ws.onclose = () => {
            setState(prev => ({ ...prev, connected: false }));

            // Attempt reconnect if job is still running
            if (state.status === 'running' || state.status === 'queued') {
                reconnectTimeoutRef.current = setTimeout(() => {
                    connect();
                }, 3000);
            }
        };
    }, [jobId, state.status]);

    useEffect(() => {
        if (jobId) {
            connect();
        }

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
        };
    }, [jobId, connect]);

    const disconnect = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
        }
    }, []);

    return {
        ...state,
        disconnect,
    };
}

export default useJobStream;
