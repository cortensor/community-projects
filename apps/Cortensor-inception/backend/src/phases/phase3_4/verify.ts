import crypto from "crypto";
import type { EvidenceBundle } from "./schema";
import { hashEvidence } from "./hash";
import type { Attestation } from "./signer";
import type { AttestorKey } from "./keys";

export function verifyBundle(
  bundle: EvidenceBundle,
  attestation: Attestation,
  key: AttestorKey
): boolean {
  if (attestation.keyType !== key.type) return false;

  const hash = hashEvidence(bundle);

  const verify = crypto.createVerify("RSA-SHA256");
  verify.update(hash);
  verify.end();

  return verify.verify(key.publicKeyPem, attestation.signature, "hex");
}
