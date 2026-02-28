import { GoogleGenerativeAI } from "@google/generative-ai";

export interface ReasoningPayload {
  systemInstruction: string;
  context: string;
  maxTokens?: number;
}

export class GeminiIntelligence {
  private genAI: GoogleGenerativeAI | null = null;
  private model: string;

  constructor(apiKey: string) {
    if (apiKey && apiKey !== "mock-gemini-key") {
      this.genAI = new GoogleGenerativeAI(apiKey);
    }
    this.model = "gemini-3-flash-preview"; // Target model for rapid reasoning
  }

  /**
   * Executes a reasoning prompt injected with upstream topological context.
   */
  public async executeReasoning(payload: ReasoningPayload): Promise<string> {
    if (!this.genAI) {
      console.warn("[GEMINI_WARN] Returning mock fallback logic (No API Key).");
      return this._mockResponse(payload);
    }

    try {
      console.log(`[GEMINI_EXEC] Booting ${this.model} | Context Size: ${payload.context.length} bytes`);
      
      const model = this.genAI.getGenerativeModel({ 
        model: this.model,
        systemInstruction: payload.systemInstruction 
      });

      const result = await model.generateContent(payload.context);
      const response = await result.response;
      return response.text();
    } catch (error: any) {
      console.error("[GEMINI_ERROR]", error.message);
      return `[GEMINI_ERROR] Failed to execute reasoning: ${error.message}`;
    }
  }

  private _mockResponse(payload: ReasoningPayload): string {
    return `[GEMINI_MOCK_SUCCESS]\nInterpreted prompt instructions successfully.\nSynthesized Context Data:\n${payload.context.substring(0, 50)}...\nDetected vulnerabilities mapping to standard vectors.`;
  }
}
