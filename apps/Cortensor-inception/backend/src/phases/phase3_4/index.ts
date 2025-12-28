import type { DecisionEnvelope } from "../phase3_3/envelope";
import { buildEvidenceBundle } from "./bundle";
import { hashEvidence } from "./hash";
import { signBundle } from "./signer";
import type { AttestorKey } from "./keys";

export function runPhase3_4(
  decisionId: string,
  envelope: DecisionEnvelope,
  provenance: {
    sessionId: number;
    taskIds: number[];
  },
  key: AttestorKey
) {
  const bundle = buildEvidenceBundle(decisionId, envelope, provenance);

  const hash = hashEvidence(bundle);
  const attestation = signBundle(hash, key);

  return {
    bundle,
    hash,
    attestation,
  };
}
