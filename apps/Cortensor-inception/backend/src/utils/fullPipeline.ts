import fs from "fs";
import { submitInference } from "../adapters/cortensor/tasks";
import { SessionQueueV2 } from "../adapters/cortensor/client";
import { runPhase3_3 } from "../phases/phase3_3";
import { runPhase3_4 } from "../phases/phase3_4";
import { audit } from "../core/auditor";

export type FullPipelineResult = {
  envelope: any;
  bundle: any;
  hash: string;
  attestation: any;
  auditOk: boolean;
};

export async function waitForClaimsForSession(sessionId: number, timeoutMs = 120_000): Promise<any[]> {
  return new Promise((resolve, reject) => {
    const onEvent = async (sId: any, tId: any) => {
      if (Number(sId) !== sessionId) return;

      try {
        const [miners, outputs] = await SessionQueueV2.getTaskResults(sId, tId);

        const claims = miners.map((miner: string, i: number) => ({
          kind: "TrustedInferenceClaim",
          source: "cortensor",
          miner,
          output: outputs[i],
          authenticated: true,
          provenance: { sessionId: Number(sId), taskId: Number(tId), network: "cortensor" },
          receivedAt: Date.now(),
        }));

        SessionQueueV2.off("TaskEnded", onEvent as any);
        resolve(claims);
      } catch (err) {
        SessionQueueV2.off("TaskEnded", onEvent as any);
        reject(err);
      }
    };

    SessionQueueV2.on("TaskEnded", onEvent as any);

    const timer = setTimeout(() => {
      SessionQueueV2.off("TaskEnded", onEvent as any);
      reject(new Error("Timeout waiting for TaskEnded for session"));
    }, timeoutMs);

    // clear timer on resolution
    Promise.resolve().then(() => timer && clearTimeout(timer));
  });
}

export async function runFullPipeline(opts: { sessionId: number; prompt: string; decisionId?: string; attestorKeyPem?: string; taskIds?: number[]; simulate?: boolean }): Promise<FullPipelineResult> {
  const sessionId = opts.sessionId;
  const prompt = opts.prompt || "Summarize why trust in AI should be earned.";

  let claims: any[];

  if (opts.simulate) {
    // Simulated claims (useful when running locally without a real Cortensor session)
    console.log("[simulate] Generating fake claims...");

    claims = [
      { kind: "TrustedInferenceClaim", source: "cortensor", miner: "miner-1", output: "Summary A", authenticated: true, provenance: { sessionId, taskId: 1, network: "cortensor" }, receivedAt: Date.now() },
      { kind: "TrustedInferenceClaim", source: "cortensor", miner: "miner-2", output: "Summary A", authenticated: true, provenance: { sessionId, taskId: 1, network: "cortensor" }, receivedAt: Date.now() },
      { kind: "TrustedInferenceClaim", source: "cortensor", miner: "miner-3", output: "Summary B", authenticated: true, provenance: { sessionId, taskId: 1, network: "cortensor" }, receivedAt: Date.now() },
    ];
  } else {
    // 1) Submit task
    try {
      await submitInference(sessionId, { type: "chat", message: prompt });
    } catch (err: any) {
      throw new Error(`Failed to submit task to Cortensor SessionV2: ${err.message || err}`);
    }

    // 2) Wait for TaskEnded
    try {
      claims = await waitForClaimsForSession(sessionId);
    } catch (err: any) {
      throw new Error(`Timeout or error waiting for TaskEnded events: ${err.message || err}`);
    }
  }

  // 3) runPhase3_3
  const envelope = runPhase3_3(claims);

  // 4) runPhase3_4
  const keyPem = opts.attestorKeyPem || "";

  if (!keyPem) throw new Error("attestorKeyPem required for signing in automated pipeline");

  // If a public key is not provided we derive it from the private key for local validation.
  const derivedPublicKey = (() => {
    try {
      const k = require("crypto").createPublicKey(keyPem).export({ type: "pkcs1", format: "pem" }).toString();
      return k;
    } catch (e) {
      return "";
    }
  })();

  const { bundle, hash, attestation } = runPhase3_4(opts.decisionId || "decision-1", envelope, { sessionId, taskIds: opts.taskIds || [] }, {
    id: "backend-attestor",
    privateKeyPem: keyPem,
    publicKeyPem: derivedPublicKey,
    type: "rsa-2048",
  });

  // 5) audit
  const auditOk = audit(bundle, attestation, { id: "backend-attestor", publicKeyPem: derivedPublicKey, privateKeyPem: "", type: "rsa-2048" });

  return { envelope, bundle, hash, attestation, auditOk };
}
