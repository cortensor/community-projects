import { InferenceResultSchema, ProofOfInferenceSchema } from "./inference.schema";
import type { InferenceBatch } from "./batch.types";
import type { VerifiedInference } from "./verified.types";
import { sha256 } from "../../utils/hash";

export function verifyInferenceBatch(batch: InferenceBatch) {
  const verified: VerifiedInference[] = [];
  const discarded: Array<{ nodeId?: string; reason: string }> = [];

  for (const r of batch.results) {
    // structural validation
    const parse = InferenceResultSchema.safeParse(r);
    if (!parse.success) {
      discarded.push({ nodeId: (r as any)?.nodeId, reason: "schema_invalid" });
      continue;
    }

    const inf = parse.data;

    // PoI presence already enforced by schema, check proofHash integrity
    try {
      const payloadStr = JSON.stringify(inf.poi.proofPayload);
      const computed = sha256(payloadStr);
      if (computed !== inf.poi.proofHash) {
        discarded.push({ nodeId: inf.nodeId, reason: "proofHash_mismatch" });
        continue;
      }
    } catch (e) {
      discarded.push({ nodeId: inf.nodeId, reason: "proofHash_error" });
      continue;
    }

    // timeout check: receivedAt - batch.requestedAt <= timeoutMs
    if (inf.receivedAt - batch.requestedAt > batch.policy.timeoutMs) {
      discarded.push({ nodeId: inf.nodeId, reason: "timeout_exceeded" });
      continue;
    }

    // output non-empty enforced by schema

    // nodeId presence enforced by schema as non-empty

    // Accept
    verified.push({ nodeId: inf.nodeId, output: inf.output, latencyMs: inf.latencyMs });
  }

  return { verified, discarded };
}
