import { NextRequest, NextResponse } from "next/server";

// Environment variables for Cortensor Router
const CORTENSOR_ROUTER_URL = process.env.CORTENSOR_ROUTER_URL || "";
const CORTENSOR_API_KEY = process.env.CORTENSOR_API_KEY || "default-dev-token";
const CORTENSOR_SESSION_ID = process.env.CORTENSOR_SESSION_ID || "124";
const USE_MOCK = process.env.USE_MOCK === "true" || !CORTENSOR_ROUTER_URL;

// Demo responses for fallback/demo mode
const DEMO_RESPONSES: Record<string, { summary: string; bulletPoints: string[] }> = {
    default: {
        summary: "Based on analysis of the query, here are the key research findings compiled from decentralized inference.",
        bulletPoints: [
            "Decentralized AI inference distributes computation across multiple nodes for reliability and trust",
            "Proof of Inference (PoI) validates that multiple miners produced consistent results",
            "Proof of Useful Work (PoUW) scores the quality and usefulness of AI outputs",
            "Multi-layer blockchain architecture (L1-L3) enables scalable AI orchestration",
            "Token-based incentives align miner behavior with network quality goals",
        ],
    },
    cortensor: {
        summary: "Cortensor is a decentralized AI inference protocol combining distributed computing with blockchain-based validation for trustworthy AI.",
        bulletPoints: [
            "Cortensor enables decentralized AI inference across a global network of nodes",
            "Router nodes handle task allocation and intelligent workload distribution",
            "Miner nodes execute inference tasks and earn rewards for quality work",
            "PoI/PoUW mechanisms provide cryptographic proofs of computation validity",
            "L3 AppChain handles privacy-preserving AI computations",
            "ERC-8004 integration enables agent identity and discoverability",
        ],
    },
    ai: {
        summary: "The latest trends in AI focus on decentralization, verifiable computation, and agentic applications that can act autonomously.",
        bulletPoints: [
            "Agentic AI systems can perform tasks autonomously with minimal human intervention",
            "Decentralized inference reduces single points of failure and increases trust",
            "Verifiable AI uses cryptographic proofs to validate model outputs",
            "Multi-model consensus improves accuracy and reduces hallucinations",
            "Web3 integration enables tokenized incentives for AI service providers",
        ],
    },
};

// Parse Cortensor response into structured format
function parseResearchOutput(rawOutput: string): { summary: string; bulletPoints: string[] } {
    const lines = rawOutput.split("\n").filter((line) => line.trim());
    const bulletPoints: string[] = [];
    let summary = "";

    for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("-") || trimmed.startsWith("•") || trimmed.match(/^\d+\./)) {
            bulletPoints.push(trimmed.replace(/^[-•\d+.]\s*/, ""));
        } else if (!summary) {
            summary = trimmed;
        }
    }

    // If no bullet points found, split summary into bullet points
    if (bulletPoints.length === 0 && summary) {
        const sentences = summary.split(/[.!?]+/).filter((s) => s.trim());
        return {
            summary: sentences[0] + ".",
            bulletPoints: sentences.slice(1).map((s) => s.trim()).filter(Boolean),
        };
    }

    return { summary: summary || "Research completed successfully.", bulletPoints };
}

// Call real Cortensor Router API
async function callCortensorAPI(query: string, url?: string): Promise<{
    summary: string;
    bulletPoints: string[];
    sessionId: string;
    taskId: string;
}> {
    // Use session ID from environment (pre-created on dashboard)
    const sessionId = CORTENSOR_SESSION_ID;

    // Build prompt for research
    const prompt = url
        ? `You are a research assistant. Analyze this URL: ${url}\n\nResearch question: ${query}\n\nProvide a concise summary followed by 5 key bullet points. Format your response clearly with a summary paragraph and bullet points starting with "-".`
        : `You are a research assistant. Research question: ${query}\n\nProvide a concise summary followed by 5 key bullet points. Format your response clearly with a summary paragraph and bullet points starting with "-".`;

    // Call completions endpoint (session ID in path) with 15s timeout for UX
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout

    const completionResponse = await fetch(`${CORTENSOR_ROUTER_URL}/api/v1/completions/${sessionId}`, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${CORTENSOR_API_KEY}`,
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            session_id: parseInt(sessionId),
            prompt,
            stream: false,
            timeout: 30,
        }),
        signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!completionResponse.ok) {
        const errorText = await completionResponse.text();
        throw new Error(`Cortensor API error: ${completionResponse.status} - ${errorText}`);
    }

    const result = await completionResponse.json();
    const rawOutput = result.output || result.text || result.content || "";
    const taskId = result.task_id?.toString() || "0";

    const parsed = parseResearchOutput(rawOutput);

    return {
        summary: parsed.summary,
        bulletPoints: parsed.bulletPoints,
        sessionId,
        taskId,
    };
}

// Get demo response based on query
function getDemoResponse(query: string): { summary: string; bulletPoints: string[] } {
    const lowerQuery = query.toLowerCase();

    if (lowerQuery.includes("cortensor") || lowerQuery.includes("decentralized inference")) {
        return DEMO_RESPONSES.cortensor;
    } else if (lowerQuery.includes("ai") || lowerQuery.includes("artificial intelligence")) {
        return DEMO_RESPONSES.ai;
    }

    return DEMO_RESPONSES.default;
}

export async function POST(request: NextRequest) {
    try {
        const { query, url } = await request.json();

        if (!query || typeof query !== "string") {
            return NextResponse.json(
                { error: "Query is required" },
                { status: 400 }
            );
        }

        let result: {
            summary: string;
            bulletPoints: string[];
            sessionId: string;
            taskId: string;
            isDemo: boolean;
        };

        if (USE_MOCK) {
            // Demo mode
            await new Promise((resolve) => setTimeout(resolve, 1500)); // Simulate delay

            const demoResponse = getDemoResponse(query);
            result = {
                ...demoResponse,
                sessionId: Math.floor(Math.random() * 100 + 1).toString(),
                taskId: Math.floor(Math.random() * 10).toString(),
                isDemo: true,
            };
        } else {
            // Real Cortensor API
            try {
                const apiResult = await callCortensorAPI(query, url);
                result = { ...apiResult, isDemo: false };
            } catch (apiError) {
                console.error("Cortensor API error, falling back to demo:", apiError);
                // Fallback to demo on API error
                const demoResponse = getDemoResponse(query);
                result = {
                    ...demoResponse,
                    sessionId: Math.floor(Math.random() * 100 + 1).toString(),
                    taskId: Math.floor(Math.random() * 10).toString(),
                    isDemo: true,
                };
            }
        }

        const sources = url ? [url] : ["https://docs.cortensor.network"];

        return NextResponse.json({
            summary: result.summary,
            bulletPoints: result.bulletPoints,
            sources,
            sessionId: result.sessionId,
            taskId: result.taskId,
            verified: !result.isDemo, // Only verified if real API
            isDemo: result.isDemo,
            model: "meta-llama-3.1-8b-instruct",
            timestamp: new Date().toISOString(),
        });
    } catch (error) {
        console.error("Research API error:", error);
        return NextResponse.json(
            { error: "Failed to process research request" },
            { status: 500 }
        );
    }
}
