import fs from "fs";
import path from "path";
import { runPhase3_3 } from "../src/phases/phase3_3";
import { runPhase3_4 } from "../src/phases/phase3_4";
import { audit } from "../src/core/auditor";

const pattern = (process.argv[2] || process.env.SIM_PATTERN || "unanimous").toLowerCase();
const sessionId = Number(process.argv[3] || process.env.SESSION_ID || 141);
const keyPath = process.argv[4] || process.env.ATTESTOR_KEY || "attestor.key";
const outDir = process.argv[5] || process.env.OUT_DIR || "./out-sim-variants";

function makeClaimsFor(pattern: string) {
  const ts = Date.now();
  switch (pattern) {
    case "unanimous":
      return [
        { kind: "TrustedInferenceClaim", source: "cortensor", miner: "miner-1", output: "Summary X", authenticated: true, provenance: { sessionId, taskId: 1, network: "cortensor" }, receivedAt: ts },
        { kind: "TrustedInferenceClaim", source: "cortensor", miner: "miner-2", output: "Summary X", authenticated: true, provenance: { sessionId, taskId: 1, network: "cortensor" }, receivedAt: ts },
        { kind: "TrustedInferenceClaim", source: "cortensor", miner: "miner-3", output: "Summary X", authenticated: true, provenance: { sessionId, taskId: 1, network: "cortensor" }, receivedAt: ts },
      ];

    case "conflict":
      return [
        { kind: "TrustedInferenceClaim", source: "cortensor", miner: "miner-1", output: "Alpha", authenticated: true, provenance: { sessionId, taskId: 1, network: "cortensor" }, receivedAt: ts },
        { kind: "TrustedInferenceClaim", source: "cortensor", miner: "miner-2", output: "Beta", authenticated: true, provenance: { sessionId, taskId: 1, network: "cortensor" }, receivedAt: ts },
        { kind: "TrustedInferenceClaim", source: "cortensor", miner: "miner-3", output: "Gamma", authenticated: true, provenance: { sessionId, taskId: 1, network: "cortensor" }, receivedAt: ts },
      ];

    default:
      // partial / default
      return [
        { kind: "TrustedInferenceClaim", source: "cortensor", miner: "miner-1", output: "Summary A", authenticated: true, provenance: { sessionId, taskId: 1, network: "cortensor" }, receivedAt: ts },
        { kind: "TrustedInferenceClaim", source: "cortensor", miner: "miner-2", output: "Summary A", authenticated: true, provenance: { sessionId, taskId: 1, network: "cortensor" }, receivedAt: ts },
        { kind: "TrustedInferenceClaim", source: "cortensor", miner: "miner-3", output: "Summary B", authenticated: true, provenance: { sessionId, taskId: 1, network: "cortensor" }, receivedAt: ts },
      ];
  }
}

async function run() {
  if (!sessionId) throw new Error("sessionId required");

  const claims = makeClaimsFor(pattern);
  console.log(`[simulate] pattern=${pattern} claims: ${claims.map((c) => c.output).join(", ")}`);

  // cast to bypass literal-type narrowing in this simple script
  const envelope = runPhase3_3(claims as any);

  const keyPem = fs.readFileSync(keyPath, "utf8");

  // derive public key from private
  const derivedPublicKey = (() => {
    try {
      return require("crypto").createPublicKey(keyPem).export({ type: "pkcs1", format: "pem" }).toString();
    } catch (e) {
      return "";
    }
  })();

  const decisionId = `decision-${pattern}-${Date.now()}`;

  const { bundle, hash, attestation } = runPhase3_4(decisionId, envelope, { sessionId, taskIds: [] }, {
    id: "backend-attestor",
    privateKeyPem: keyPem,
    publicKeyPem: derivedPublicKey,
    type: "rsa-2048",
  });

  const auditOk = audit(bundle, attestation, { id: "backend-attestor", publicKeyPem: derivedPublicKey, privateKeyPem: "", type: "rsa-2048" });

  fs.mkdirSync(outDir, { recursive: true });

  const ts = Date.now();
  const bundlePath = path.join(outDir, `bundle-${pattern}-${ts}.json`);
  const attPath = path.join(outDir, `attestation-${pattern}-${ts}.json`);

  fs.writeFileSync(bundlePath, JSON.stringify(bundle, null, 2));
  fs.writeFileSync(attPath, JSON.stringify(attestation, null, 2));

  console.log("RESULT:");
  console.log(`- pattern: ${pattern}`);
  console.log(`- decision: ${envelope.decision}`);
  console.log(`- agreementState: ${envelope.agreementState}`);
  console.log(`- hash: ${hash}`);
  console.log(`- attestation.signer: ${attestation.signer}`);
  console.log(`- auditOk: ${auditOk}`);
  console.log(`Bundle written to: ${bundlePath}`);
  console.log(`Attestation written to: ${attPath}`);

  if (!auditOk) process.exit(2);
  process.exit(0);
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
