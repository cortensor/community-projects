import fs from "fs";
import path from "path";
import { runFullPipeline } from "../src/utils/fullPipeline";

const sessionId = Number(process.argv[2] || process.env.SESSION_ID || 141);
const prompt = process.argv[3] || process.env.PROMPT || "Summarize why trust in AI should be earned.";
const keyPath = process.argv[4] || process.env.ATTESTOR_KEY || "attestor.key";
const outDir = process.argv[5] || process.env.OUT_DIR || "./out";

async function run() {
  if (!sessionId) throw new Error("sessionId required");

  const keyPem = fs.readFileSync(keyPath, "utf8");

  console.log(`Running full pipeline for session=${sessionId} prompt="${prompt}"`);

  const simulateFlag = process.argv.includes("--simulate") || process.env.SIMULATE === "1";

const result = await runFullPipeline({ sessionId, prompt, decisionId: `decision-${Date.now()}`, attestorKeyPem: keyPem, simulate: simulateFlag });

  // Ensure out dir exists
  fs.mkdirSync(outDir, { recursive: true });

  const ts = Date.now();
  const bundlePath = path.join(outDir, `bundle-${ts}.json`);
  const attestationPath = path.join(outDir, `attestation-${ts}.json`);

  fs.writeFileSync(bundlePath, JSON.stringify(result.bundle, null, 2));
  fs.writeFileSync(attestationPath, JSON.stringify(result.attestation, null, 2));

  console.log("FULL PIPELINE RESULT:");
  console.log(`- decision: ${result.envelope.decision}`);
  console.log(`- agreementState: ${result.envelope.agreementState}`);
  console.log(`- hash: ${result.hash}`);
  console.log(`- attestation.signer: ${result.attestation.signer}`);
  console.log(`- auditOk: ${result.auditOk}`);
  console.log(`Bundle written to: ${bundlePath}`);
  console.log(`Attestation written to: ${attestationPath}`);

  if (!result.auditOk) {
    console.error("Audit failed — evidence verification did not pass");
    process.exit(2);
  }

  process.exit(0);
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
