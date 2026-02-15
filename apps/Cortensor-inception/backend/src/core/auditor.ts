import type { EvidenceBundle } from "../phases/phase3_4/schema";
import type { Attestation } from "../phases/phase3_4/signer";
import type { AttestorKey } from "../phases/phase3_4/keys";
import { verifyBundle } from "../phases/phase3_4/verify";

export function audit(bundle: EvidenceBundle, attestation: Attestation, key: AttestorKey): boolean {
  return verifyBundle(bundle, attestation, key);
}
