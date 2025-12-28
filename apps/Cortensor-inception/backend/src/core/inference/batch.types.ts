import type { InferenceResult } from "./inference.types";

export interface InferenceBatch {
  taskHash: string;
  requestedAt: number;
  policy: {
    minValidators: number;
    timeoutMs: number;
  };
  results: InferenceResult[];
}
