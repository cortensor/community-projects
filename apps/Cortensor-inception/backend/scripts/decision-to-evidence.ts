import fs from "fs";
import { runPhase3_4 } from "../src/phases/phase3_4";

const envelopePath = process.argv[2] || process.env.ENVELOPE_FILE;
const privateKeyPath = process.argv[3] || process.env.ATTESTOR_KEY || "attestor.key";
const decisionId = process.argv[4] || process.env.DECISION_ID || "decision-001";
const sessionId = Number(process.argv[5] || process.env.SESSION_ID || 141);
const taskIds = (process.argv[6] || process.env.TASK_IDS || "0").split(",").map((s) => Number(s));

if (!envelopePath) {
  console.error("Usage: decision-to-evidence.ts <envelope.json> [privateKeyFile]");
  process.exit(1);
}

async function run() {
  const ePath = envelopePath!;
  const kPath = privateKeyPath!;

  let envelope: any;
  let privateKey = "";

  try {
    envelope = JSON.parse(fs.readFileSync(ePath, "utf8"));
  } catch (err: any) {
    console.error(`Failed to read or parse envelope at ${ePath}:`, (err && err.message) || err);
    process.exit(2);
  }

  try {
    privateKey = fs.readFileSync(kPath, "utf8");
  } catch (err: any) {
    console.error(`Failed to read private key at ${kPath}:`, (err && err.message) || err);
    process.exit(2);
  }

  const result = runPhase3_4(
    decisionId,
    envelope,
    { sessionId, taskIds },
    {
      id: "backend-attestor",
      privateKeyPem: privateKey,
      publicKeyPem: "",
      type: "rsa-2048",
    }
  );

  console.log("EVIDENCE RESULT");
  console.dir(result, { depth: null });
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
