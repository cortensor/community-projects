// Cortensor Router API integration for InsightAI

export interface CortensorConfig {
    routerUrl: string;
    apiKey?: string;
}

export interface DelegateRequest {
    task_request_input: string;
    web_url?: string;
}

export interface DelegateResponse {
    output: string;
    session_id?: string;
    task_id?: string;
    model?: string;
    miners?: string[];
}

export interface ResearchResult {
    query: string;
    summary: string;
    bulletPoints: string[];
    sources: string[];
    sessionId?: string;
    taskId?: string;
    timestamp: Date;
    verified: boolean;
}

const DEFAULT_ROUTER_URL = process.env.NEXT_PUBLIC_CORTENSOR_ROUTER_URL || 'https://dashboard-testnet0.cortensor.network';

/**
 * Call Cortensor's /delegate endpoint for research tasks
 * This uses the thin agent SDK layer that fetches web content and processes with LLM
 */
export async function delegateResearch(
    query: string,
    urls: string[] = [],
    config?: Partial<CortensorConfig>
): Promise<ResearchResult> {
    const routerUrl = config?.routerUrl || DEFAULT_ROUTER_URL;

    try {
        // For demo/development, use the completions endpoint
        const response = await fetch(`/api/research`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query,
                urls,
            }),
        });

        if (!response.ok) {
            throw new Error(`Research request failed: ${response.statusText}`);
        }

        const data = await response.json();

        return {
            query,
            summary: data.summary || '',
            bulletPoints: data.bulletPoints || [],
            sources: data.sources || urls,
            sessionId: data.sessionId,
            taskId: data.taskId,
            timestamp: new Date(),
            verified: data.verified || false,
        };
    } catch (error) {
        console.error('Cortensor delegate error:', error);
        throw error;
    }
}

/**
 * Parse structured research output from LLM response
 */
export function parseResearchOutput(rawOutput: string): {
    summary: string;
    bulletPoints: string[];
    sources: string[];
} {
    const lines = rawOutput.split('\n').filter(line => line.trim());
    const bulletPoints: string[] = [];
    const sources: string[] = [];
    let summary = '';

    for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.match(/^\d+\./)) {
            bulletPoints.push(trimmed.replace(/^[-•]\s*/, '').replace(/^\d+\.\s*/, ''));
        } else if (trimmed.startsWith('http') || trimmed.includes('Source:')) {
            sources.push(trimmed.replace('Source:', '').trim());
        } else if (!summary && trimmed.length > 50) {
            summary = trimmed;
        }
    }

    if (!summary && bulletPoints.length > 0) {
        summary = `Found ${bulletPoints.length} key insights from the research.`;
    }

    return { summary, bulletPoints, sources };
}

/**
 * Get verification URL for a Cortensor session/task
 */
export function getVerificationUrl(sessionId: string, taskId?: string): string {
    const base = 'https://dashboard-testnet0.cortensor.network/session';
    return taskId ? `${base}/${sessionId}/${taskId}` : `${base}/${sessionId}`;
}
