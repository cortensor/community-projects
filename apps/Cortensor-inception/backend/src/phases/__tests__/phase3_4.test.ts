import { test, expect } from "vitest";
import { canonicalize } from "../phase3_4/canonical";
import { hashEvidence } from "../phase3_4/hash";
import { buildEvidenceBundle } from "../phase3_4/schema";
import { runPhase3_4 } from "../phase3_4";
import { verifyBundle } from "../phase3_4/verify";
import { assertImmutable } from "../phase3_4/immutability";
import { AttestorKey } from "../phase3_4/keys";
import crypto from "crypto";

function makeEnvelope(): any {
  return {
    decision: "ESCALATE",
    rationale: "test",
    winningHash: undefined,
    agreementState: "ESCALATED",
    evidence: { totalClaims: 2, groupCount: 1, distinctMiners: 2, replayHash: "abc" },
  };
}

test("canonicalize order invariance", () => {
  const a = { b: 1, a: 2 };
  const b = { a: 2, b: 1 };

  expect(canonicalize(a)).toBe(canonicalize(b));
});

test("hash + sign + verify roundtrip", () => {
  const envelope = makeEnvelope();
  // Use runPhase3_4 to build the bundle and produce the canonical hash so we
  // avoid nondeterminism from Date.now() inside buildEvidenceBundle.
  const { publicKey, privateKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
  const key: AttestorKey = {
    id: "k1",
    type: "rsa-2048",
    privateKeyPem: privateKey.export({ type: "pkcs1", format: "pem" }).toString(),
    publicKeyPem: publicKey.export({ type: "pkcs1", format: "pem" }).toString(),
  };

  const { bundle: outBundle, hash: outHash, attestation } = runPhase3_4("d1", envelope, { sessionId: 1, taskIds: [1] }, key as AttestorKey);

  // Recompute the hash from the returned bundle and ensure it matches the
  // attested hash supplied by runPhase3_4.
  const recomputed = hashEvidence(outBundle);
  expect(outHash).toBe(recomputed);
  expect(verifyBundle(outBundle, attestation, key as AttestorKey)).toBeTruthy();
});

test("immutability guard throws on mismatch", () => {
  expect(() => assertImmutable("a", "b")).toThrow("Evidence immutability violation");
  expect(() => assertImmutable(undefined, "b")).not.toThrow();
});
