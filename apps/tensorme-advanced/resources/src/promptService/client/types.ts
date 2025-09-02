export interface StreamChunk {
  content: string;
  thinking?: string;
  title?: string;
  historySummary?: string;
  isThinking?: boolean;
  isComplete?: boolean;
}

export interface SingleShotResponse {
  content: string;
  thinking?: string;
  title?: string;
  historySummary?: string;
}

export interface ClientPromptServiceInterface {
  parseStreamChunk(data: any): StreamChunk | null;
  parseSingleShot(data: any): SingleShotResponse | null;
}