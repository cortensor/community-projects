import { NextResponse } from 'next/server';
import { appConfig } from '@/lib/app-config';

export async function POST(req: Request) {
  try {
    const apiUrl = appConfig.cortensor?.createUrl;
    const apiKey = appConfig.cortensor?.apiKey?.trim();

    // Configuration validation
    if (!apiUrl || !apiKey) {
      throw new Error("Create session URL or API Key not found in environment configuration.");
    }

    // Payload for creating a session, based on your curl example
    const createPayload = {
      name: "Web Chat Session",
      metadata: "Session created from web-based AI Chatbot",
      address: "0x0000000000000000000000000000000000000000",
      minNumOfNodes: 0,
      maxNumOfNodes: 0,
      redundant: 1,
      numOfValidatorNodes: 0,
      mode: 0,
      reserveEphemeralNodes: false,
    };

    const headers = new Headers();
    headers.append('Content-Type', 'application/json');
    headers.append('Authorization', `Bearer ${apiKey}`);

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(createPayload),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      console.error(`[CREATE] Failed to create session on Cortensor: ${errorBody}`);
      throw new Error(`Error from Cortensor /create API: ${response.status}`);
    }

    const data = await response.json();
    
    // The server returns a 'tx_hash', not a numerical session_id
    const cortensorIdentifier = data?.tx_hash;

    if (!cortensorIdentifier) {
      throw new Error("The response from /create did not contain a 'tx_hash'.");
    }

    // Send this identifier back to the frontend as the session ID
    return NextResponse.json({ success: true, cortensorSessionId: cortensorIdentifier });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
    console.error("Error in /api/session/create:", errorMessage);
    return NextResponse.json({ success: false, error: errorMessage }, { status: 500 });
  }
}
