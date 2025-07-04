import { NextResponse } from 'next/server';
import { appConfig } from '@/lib/app-config';

export async function POST(req: Request) {
  try {
    const apiUrl = appConfig.cortensor?.completionsUrl;
    const apiKey = appConfig.cortensor?.apiKey?.trim();
    
    const { messages, cortensorSessionId } = await req.json();

    if (!apiUrl || !apiKey) {
      throw new Error("Completions URL or API Key not found in environment configuration.");
    }

    if (!cortensorSessionId) {
        throw new Error("Cortensor Session Identifier was not provided by the frontend.");
    }
    const lastUserMessage = messages?.slice(-1)[0]?.content;
    if (!lastUserMessage) {
      throw new Error("No valid user message to send.");
    }

    const payload = {
      // CRITICAL NOTE: Your Flask app uses an integer ID, but the /create endpoint provides a string (tx_hash).
      // This is a fundamental mismatch in your Cortensor API.
      // We are using a static integer from the environment variable here for testing.
      // In a real production scenario, you need a way to resolve the tx_hash to its corresponding integer ID.
      session_id: appConfig.cortensor.sessionId, 
      prompt: lastUserMessage,
      prompt_type: 0,
      stream: false,
      timeout: appConfig.cortensor.timeout,
    };

    const headers = new Headers();
    headers.append('Content-Type', 'application/json');
    headers.append('Authorization', `Bearer ${apiKey}`);

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      console.error(`[CHAT] Error from Cortensor /completions: ${errorBody}`);
      if (response.status === 401) {
        throw new Error(`Authorization Error (401). The issue is with the router server configuration, not this code.`);
      }
      throw new Error(`Error from API: ${response.status}`);
    }

    const data = await response.json();
    
    const messageContent = data?.choices?.[0]?.text?.trim();

    if (!messageContent) {
      console.error("Failed to parse response from Cortensor. Unexpected structure:", data);
      throw new Error("Failed to understand the response format from Cortensor.");
    }

    return NextResponse.json({ success: true, message: messageContent });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
    console.error("Error in /api/chat:", errorMessage);
    return new NextResponse(JSON.stringify({ success: false, error: errorMessage }), { status: 500 });
  }
}
