// src/app/api/chat/route.ts
import { NextResponse } from 'next/server';
import { appConfig } from '@/lib/app-config';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

const EUREKA_SYSTEM_PROMPT = `<|SYSTEM|>
You are "Eureka," an advanced AI assistant. Your core attributes are:
1.  **Identity:** You are called Eureka.
2.  **Expertise:** You possess deep knowledge across various domains.
3.  **Contextual Memory:** When provided with conversation history, you seamlessly recall and integrate all previous details to maintain coherence.
4.  **Honesty & Transparency:** You acknowledge uncertainty and state any limitations.
5.  **Communication Style:** You communicate in clear, concise English.`;

export async function POST(req: Request) {
  try {
    const { messages, cortensorSessionId } = await req.json();

    const apiUrl = appConfig.cortensor.completionsUrl;
    const apiKey = appConfig.cortensor.apiKey;

    if (!apiUrl || !apiKey) throw new Error("Completions URL or API Key is not configured.");
    if (!cortensorSessionId) throw new Error("A static session ID is required from the frontend.");
    if (!messages || messages.length === 0) throw new Error("No valid messages array to send.");

    let formattedPrompt = EUREKA_SYSTEM_PROMPT;
    messages.forEach((message: ChatMessage) => {
      const role = message.role === 'user' ? 'USER' : 'ASSISTANT';
      formattedPrompt += `\n<|${role}|>\n${message.content}\n`;
    });
    formattedPrompt += "\n<|ASSISTANT|>\n";
    
    const payload = {
      session_id: parseInt(cortensorSessionId, 10),
      prompt: formattedPrompt,
      prompt_type: 1,
      stream: true,
      timeout: parseInt(process.env.LLM_TIMEOUT || '360', 10),
      max_tokens: parseInt(process.env.LLM_MAX_TOKENS || '4096', 10),
    };
    
    const headers = new Headers();
    headers.append('Content-Type', 'application/json');
    headers.append('Authorization', `Bearer ${apiKey}`);
    headers.append('Accept', 'text/event-stream');
    headers.append('Connection', 'keep-alive');

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(payload),
    });

    if (!response.body) throw new Error("No response body from Cortensor API.");
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let rawResponseData = "";

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        rawResponseData += decoder.decode(value, { stream: true });
    }
    
    console.log("Full raw data from miners:", rawResponseData);

    // FIX: Menggunakan RegEx untuk mengekstrak HANYA nilai dari field "text"
    const textMatches = rawResponseData.match(/"text"\s*:\s*"((?:\\.|[^"\\])*)"/g) || [];

    if (textMatches.length === 0) {
      throw new Error(`Could not find any 'text' fields in the raw response: "${rawResponseData}"`);
    }

    const allTextResponses = textMatches.map(match => {
      // Ekstrak konten dari dalam tanda kutip
      const content = match.substring(match.indexOf(':"') + 2, match.length - 1);
      // Decode karakter JSON escape seperti \n dan \"
      return JSON.parse(`"${content}"`);
    });

    const cleanedResponses = allTextResponses
      .map(res => res.replace(/<\/s>$/, '').trim())
      .filter(res => res.length > 0);

    if (cleanedResponses.length === 0) {
      throw new Error("All extracted text responses were empty after cleaning.");
    }

    const bestResponse = cleanedResponses.reduce((a, b) => a.length > b.length ? a : b);
    
    return NextResponse.json({ success: true, message: bestResponse });

  } catch (error: any) {
    console.error("Error in /api/chat:", error.message);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
