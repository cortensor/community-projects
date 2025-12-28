import fs from "fs";
import { audit } from "../src/core/auditor";

const bundlePath = process.argv[2] || process.env.BUNDLE_FILE;
const attestationPath = process.argv[3] || process.env.ATTESTATION_FILE;
const publicKeyPath = process.argv[4] || process.env.ATTESTOR_PUB || "attestor.pub";

if (!bundlePath || !attestationPath) {
  console.error("Usage: audit.ts <bundle.json> <attestation.json> [publicKey.pem]");
  process.exit(1);
}

async function run() {
  const bPath = bundlePath!;
  const aPath = attestationPath!;
  const pPath = publicKeyPath || "";

  let bundle: any;
  let attestation: any;
  let publicKey = "";

  try {
    bundle = JSON.parse(fs.readFileSync(bPath, "utf8"));
  } catch (err: any) {
    console.error(`Failed to read or parse bundle at ${bPath}:`, (err && err.message) || err);
    process.exit(2);
  }

  try {
    attestation = JSON.parse(fs.readFileSync(aPath, "utf8"));
  } catch (err: any) {
    console.error(`Failed to read or parse attestation at ${aPath}:`, (err && err.message) || err);
    process.exit(2);
  }

  if (pPath) {
    try {
      publicKey = fs.readFileSync(pPath, "utf8");
    } catch (err: any) {
      console.warn(`Could not read public key at ${pPath}:`, (err && err.message) || err);
    }
  }

  const ok = audit(bundle, attestation, {
    id: "backend-attestor",
    publicKeyPem: publicKey,
    privateKeyPem: "",
    type: "rsa-2048",
  });

  console.log("AUDIT RESULT:", ok);
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
