export interface InferenceResult {
  nodeId: string; // Cortensor validator / miner ID
  output: string; // Raw model output
  poi: import("./poi.types").ProofOfInference; // Cryptographic proof
  latencyMs: number; // Execution latency
  receivedAt: number; // Timestamp (ms)
}
