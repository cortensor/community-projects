import type { InferenceResult } from "../../core/inference/inference.types";

export interface RouterInferenceRequest {
  prompt: string;
  timeoutMs: number;
  minValidators: number;
}

export interface RouterAdapter {
  runInference(request: RouterInferenceRequest): Promise<InferenceResult[]>;
}
