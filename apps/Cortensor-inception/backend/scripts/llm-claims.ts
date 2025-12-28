import fs from "fs";
import path from "path";
import { generateLLMOutputs } from "../src/adapters/llm/client";
import { runPhase3_3 } from "../src/phases/phase3_3";
import { runPhase3_4 } from "../src/phases/phase3_4";
import { audit } from "../src/core/auditor";

const apiUrl = process.argv[2] || process.env.LLM_API_URL || "https://ollama-qwen.zeabur.app/api/chat";
const prompt = process.argv[3] || process.env.LLM_PROMPT || "Summarize why trust in AI should be earned.";
const miners = Number(process.argv[4] || process.env.LLM_MINERS || 3);
const temp = Number(process.argv[5] || process.env.LLM_TEMPERATURE || 0.7);
const keyPath = process.argv[6] || process.env.ATTESTOR_KEY || "attestor.key";
const outDir = process.argv[7] || process.env.OUT_DIR || "./out-llm";

async function run() {
  const outputs = await generateLLMOutputs({ apiUrl, prompt, n: miners, temperature: temp });

  const claims = outputs.map((out, i) => ({
    kind: "TrustedInferenceClaim",
    source: "llm",
    miner: `llm-${i + 1}`,
    output: out,
    authenticated: true,
    provenance: { sessionId: Number(process.env.SESSION_ID || 0), taskId: 0, network: "llm" },
    receivedAt: Date.now(),
  }));

  console.log("Generated claims:", claims.map((c) => c.output));

  const envelope = runPhase3_3(claims as any);

  const keyPem = fs.readFileSync(keyPath, "utf8");

  const derivedPublicKey = (() => {
    try {
      return require("crypto").createPublicKey(keyPem).export({ type: "pkcs1", format: "pem" }).toString();
    } catch (e) {
      return "";
    }
  })();

  const { bundle, hash, attestation } = runPhase3_4(`llm-run-${Date.now()}`, envelope, { sessionId: Number(process.env.SESSION_ID || 0), taskIds: [] }, {
    id: "backend-attestor",
    privateKeyPem: keyPem,
    publicKeyPem: derivedPublicKey,
    type: "rsa-2048",
  });

  const auditOk = audit(bundle, attestation, { id: "backend-attestor", publicKeyPem: derivedPublicKey, privateKeyPem: "", type: "rsa-2048" });

  fs.mkdirSync(outDir, { recursive: true });

  const ts = Date.now();
  const bundlePath = path.join(outDir, `bundle-llm-${ts}.json`);
  const attPath = path.join(outDir, `attestation-llm-${ts}.json`);

  fs.writeFileSync(bundlePath, JSON.stringify(bundle, null, 2));
  fs.writeFileSync(attPath, JSON.stringify(attestation, null, 2));

  console.log("RESULT:");
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
