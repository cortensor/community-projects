import express from "express";
import fs from "fs";
import { z } from "zod";
import { runFullPipeline } from "../utils/fullPipeline";
import { audit } from "../core/auditor";
import { generateLLMOutputs } from "../adapters/llm/client";

const router = express.Router();

// Simple zod schemas to validate incoming requests
const SubmitSchema = z.object({ type: z.string(), claim: z.any(), context: z.any().optional(), risk: z.any().optional(), sessionId: z.preprocess((v) => Number(v), z.number().positive()) });
const LLMSchema = z.object({ prompt: z.string().min(1), miners: z.preprocess((v) => Number(v || 3), z.number().min(1).max(20)).optional(), temperature: z.preprocess((v) => Number(v || 0.7), z.number().min(0).max(1)).optional(), apiUrl: z.string().url().optional(), authenticated: z.boolean().optional(), sessionId: z.preprocess((v) => Number(v), z.number().positive()) });
const ProcessSchema = z.object({ text: z.string().min(1), miners: z.preprocess((v) => Number(v || 3), z.number().min(1).max(20)).optional(), temperature: z.preprocess((v) => Number(v || 0.7), z.number().min(0).max(1)).optional(), sessionId: z.preprocess((v) => Number(v), z.number().positive()) });

router.post("/submit", async (req, res) => {
  try {
    const parse = SubmitSchema.safeParse({ ...req.body, sessionId: req.body.sessionId || process.env.SESSION_ID });
    if (!parse.success) return res.status(400).json({ error: "invalid body", details: parse.error.format() });

    const { type, claim, context, risk, sessionId } = parse.data;

    const attestorKeyPath = process.env.ATTESTOR_KEY || "attestor.key";
    let privateKeyPem = "";
    try {
      privateKeyPem = fs.readFileSync(attestorKeyPath, "utf8");
    } catch (err: any) {
      return res.status(500).json({ error: `attestor key not available at ${attestorKeyPath}` });
    }

    // Build a simple task payload that Cortensor nodes understand
    const payload = { type, claim, context, risk };

    const result = await runFullPipeline({ sessionId: Number(sessionId), prompt: JSON.stringify(payload), attestorKeyPem: privateKeyPem });

    // runFullPipeline returns envelope, bundle, hash, attestation, auditOk
    return res.json(result);
  } catch (err: any) {
    console.error(err);
    return res.status(500).json({ error: err.message || String(err) });
  }
});

router.post("/audit/verify", async (req, res) => {
  try {
    const { bundle, attestation, publicKeyPem } = req.body;
    if (!bundle || !attestation || !publicKeyPem) return res.status(400).json({ error: "bundle, attestation, publicKeyPem required" });

    const ok = audit(bundle, attestation, { id: "frontend-verifier", publicKeyPem, privateKeyPem: "", type: "rsa-2048" });

    return res.json({ ok });
  } catch (err: any) {
    console.error(err);
    return res.status(500).json({ error: err.message || String(err) });
  }
});

// LLM-powered claims endpoint (uses an external LLM to generate multiple independent claims)
router.post("/llm", async (req, res) => {
  try {
    const parse = LLMSchema.safeParse({ ...req.body, sessionId: req.body.sessionId || process.env.SESSION_ID });
    if (!parse.success) return res.status(400).json({ error: "invalid body", details: parse.error.format() });

    const { prompt, miners = 3, temperature = 0.7, apiUrl, authenticated = false, sessionId } = parse.data;

    const outputs = await generateLLMOutputs({ apiUrl, prompt, n: Number(miners), temperature: Number(temperature) });

    const claims = outputs.map((out, i) => ({
      kind: "TrustedInferenceClaim",
      source: "llm",
      miner: `llm-${i + 1}`,
      output: out,
      authenticated: Boolean(authenticated),
      provenance: { sessionId: Number(sessionId), taskId: 0, network: "llm" },
      receivedAt: Date.now(),
    }));

    // require attestor key
    const attestorKeyPath = process.env.ATTESTOR_KEY || "attestor.key";
    let privateKeyPem = "";
    try {
      privateKeyPem = fs.readFileSync(attestorKeyPath, "utf8");
    } catch (err: any) {
      return res.status(500).json({ error: `attestor key not available at ${attestorKeyPath}` });
    }

    // run decision and evidence pipeline
    const envelope = (await import("../phases/phase3_3")).runPhase3_3(claims as any);
    const { bundle, hash, attestation } = (await import("../phases/phase3_4")).runPhase3_4(`llm-${Date.now()}`, envelope, { sessionId, taskIds: [] }, {
      id: "backend-attestor",
      privateKeyPem,
      publicKeyPem: (() => { try { return require("crypto").createPublicKey(privateKeyPem).export({ type: "pkcs1", format: "pem" }).toString(); } catch (e) { return ""; } })(),
      type: "rsa-2048",
    });

    let auditOk = false;
    try {
      auditOk = audit(bundle, attestation, { id: "backend-attestor", publicKeyPem: (attestation as any).publicKeyPem || "", privateKeyPem: "", type: "rsa-2048" });
    } catch (e: any) {
      auditOk = false;
      console.error("LLM audit failed:", e?.message || String(e));
    }

    return res.json({ envelope, bundle, hash, attestation, auditOk });
  } catch (err: any) {
    console.error(err);
    return res.status(500).json({ error: err.message || String(err) });
  }
});

// Process endpoint: run LLM + simulator on provided text and return bundles + attestations
router.post("/process", async (req, res) => {
  const steps: string[] = [];

  function pushStep(msg: string) {
    steps.push(`${new Date().toISOString()} - ${msg}`);
  }

  try {
    const parse = ProcessSchema.safeParse({ ...req.body, sessionId: req.body.sessionId || process.env.SESSION_ID });
    if (!parse.success) return res.status(400).json({ error: "invalid body", details: parse.error.format(), steps });

    const { text, miners = 3, temperature = 0.7, sessionId } = parse.data;

    const attestorKeyPath = process.env.ATTESTOR_KEY || "attestor.key";
    let privateKeyPem = "";
    try {
      privateKeyPem = fs.readFileSync(attestorKeyPath, "utf8");
    } catch (err: any) {
      return res.status(500).json({ error: `attestor key not available at ${attestorKeyPath}`, steps });
    }

    // LLM step
    pushStep("LLM: start");
    let llmOutputs: string[] = [];
    let llmError: string | null = null;
    try {
      llmOutputs = await generateLLMOutputs({ prompt: text, n: Number(miners), temperature: Number(temperature) });
      pushStep(`LLM: success (${llmOutputs.length} outputs)`);
    } catch (e: any) {
      llmError = e?.message || String(e);
      pushStep(`LLM: failed — ${llmError}`);

      // fallback — derive simple textual outputs from the user text
      const fallback = (i: number) => `${text} (fallback ${i + 1})`;
      llmOutputs = Array.from({ length: Number(miners) }).map((_, i) => fallback(i));
      pushStep("LLM: fallback outputs generated");
    }

    // construct LLM claims
    const llmClaims = llmOutputs.map((out, i) => ({
      kind: "TrustedInferenceClaim",
      source: "llm",
      miner: `llm-${i + 1}`,
      output: out,
      authenticated: true,
      provenance: { sessionId: Number(sessionId), taskId: 0, network: "llm" },
      receivedAt: Date.now(),
    }));

    // SIM step
    pushStep("Simulator: start");
    const simClaims = Array.from({ length: Number(miners) }).map((_, i) => ({
      kind: "TrustedInferenceClaim",
      source: "sim",
      miner: `sim-${i + 1}`,
      output: `Simulated check: ${text}${i > 0 ? ` (variant ${i + 1})` : ""}`,
      authenticated: true,
      provenance: { sessionId: Number(sessionId), taskId: 0, network: "sim" },
      receivedAt: Date.now(),
    }));
    pushStep(`Simulator: generated ${simClaims.length} claims`);

    // Decision + Evidence for LLM
    pushStep("LLM: decision and bundling");
    const envLLM = (await import("../phases/phase3_3")).runPhase3_3(llmClaims as any);

    let bundleLLM: any = null;
    let hashLLM: any = null;
    let attLLM: any = null;
    let auditLLM = false;

    try {
      const res = (await import("../phases/phase3_4")).runPhase3_4(`llm-run-${Date.now()}`, envLLM, { sessionId, taskIds: [] }, {
        id: "backend-attestor",
        privateKeyPem,
        publicKeyPem: (() => { try { return require("crypto").createPublicKey(privateKeyPem).export({ type: "pkcs1", format: "pem" }).toString(); } catch (e) { return ""; } })(),
        type: "rsa-2048",
      });
      bundleLLM = res.bundle;
      hashLLM = res.hash;
      attLLM = res.attestation;

      try {
        auditLLM = audit(bundleLLM, attLLM, { id: "backend-attestor", publicKeyPem: (attLLM as any).publicKeyPem || "", privateKeyPem: "", type: "rsa-2048" });
      } catch (e: any) {
        auditLLM = false;
        pushStep?.(`LLM: audit failed — ${e?.message || String(e)}`);
      }

      pushStep(`LLM: bundle created (hash ${hashLLM}), auditOk=${auditLLM}`);
    } catch (e: any) {
      pushStep?.(`LLM: bundling failed — ${e?.message || String(e)}`);

      // fallback bundle for blending
      const { buildEvidenceBundle } = await import("../phases/phase3_4/schema");
      bundleLLM = buildEvidenceBundle(`llm-run-fallback-${Date.now()}`, {
        decision: "ESCALATE",
        rationale: `LLM bundling failed: ${e?.message || String(e)}`,
        agreementState: "ESCALATED",
        evidence: { totalClaims: llmClaims.length, groupCount: 0, distinctMiners: llmClaims.length, replayHash: "" },
      } as any, { sessionId: Number(sessionId), taskIds: [] });
      hashLLM = "fallback-llm";
      attLLM = null;
      auditLLM = false;
    }

    // Decision + Evidence for SIM
    pushStep("Simulator: decision and bundling");
    const envSIM = (await import("../phases/phase3_3")).runPhase3_3(simClaims as any);

    let bundleSIM: any = null;
    let hashSIM: any = null;
    let attSIM: any = null;
    let auditSIM = false;

    try {
      const res = (await import("../phases/phase3_4")).runPhase3_4(`sim-run-${Date.now()}`, envSIM, { sessionId, taskIds: [] }, {
        id: "backend-attestor",
        privateKeyPem,
        publicKeyPem: (() => { try { return require("crypto").createPublicKey(privateKeyPem).export({ type: "pkcs1", format: "pem" }).toString(); } catch (e) { return ""; } })(),
        type: "rsa-2048",
      });
      bundleSIM = res.bundle;
      hashSIM = res.hash;
      attSIM = res.attestation;

      try {
        auditSIM = audit(bundleSIM, attSIM, { id: "backend-attestor", publicKeyPem: (attSIM as any).publicKeyPem || "", privateKeyPem: "", type: "rsa-2048" });
      } catch (e: any) {
        auditSIM = false;
        pushStep?.(`Simulator: audit failed — ${e?.message || String(e)}`);
      }

      pushStep(`Simulator: bundle created (hash ${hashSIM}), auditOk=${auditSIM}`);
    } catch (e: any) {
      pushStep?.(`Simulator: bundling failed — ${e?.message || String(e)}`);

      // fallback bundle for blending
      const { buildEvidenceBundle } = await import("../phases/phase3_4/schema");
      bundleSIM = buildEvidenceBundle(`sim-run-fallback-${Date.now()}`, {
        decision: "ESCALATE",
        rationale: `Simulator bundling failed: ${e?.message || String(e)}`,
        agreementState: "ESCALATED",
        evidence: { totalClaims: simClaims.length, groupCount: 0, distinctMiners: simClaims.length, replayHash: "" },
      } as any, { sessionId: Number(sessionId), taskIds: [] });
      hashSIM = "fallback-sim";
      attSIM = null;
      auditSIM = false;
    }

    // Blend
    pushStep("Blending: start");
    const { blendBundles } = await import("../utils/blend");
    let blended: any = null;

    try {
      blended = blendBundles("llm", bundleLLM, "sim", bundleSIM);
      pushStep("Blending: merged results");
    } catch (e: any) {
      pushStep?.(`Blending failed — ${e?.message || String(e)}`);

      blended = {
        id: `blended-fallback-${Date.now()}`,
        sources: [],
        blended: {
          decision: "ESCALATE",
          agreementState: "ESCALATED",
          rationale: `Blending failed: ${e?.message || String(e)}`,
          evidence: { totalClaims: 0, groupCount: 0, distinctMiners: 0, replayHash: [] },
          diffs: [],
        },
        createdAt: Date.now(),
      };
    }

    // Canonical blended bundle and attestation
    pushStep("Blended: creating evidence bundle and attestation");
    const blendedEnvelope = {
      decision: blended.blended.decision,
      rationale: blended.blended.rationale,
      agreementState: blended.blended.agreementState,
      evidence: {
        totalClaims: blended.blended.evidence.totalClaims,
        groupCount: blended.blended.evidence.groupCount,
        distinctMiners: blended.blended.evidence.distinctMiners,
        replayHash: (blended.blended.evidence.replayHash || []).join(","),
      },
    } as any;

    let bundleBLEND: any = null;
    let hashBLEND: any = null;
    let attBLEND: any = null;
    let auditBLEND = false;

    try {
      const res = (await import("../phases/phase3_4")).runPhase3_4(`blended-${Date.now()}`, blendedEnvelope as any, { sessionId, taskIds: [] }, {
        id: "backend-attestor",
        privateKeyPem,
        publicKeyPem: (() => { try { return require("crypto").createPublicKey(privateKeyPem).export({ type: "pkcs1", format: "pem" }).toString(); } catch (e) { return ""; } })(),
        type: "rsa-2048",
      });
      bundleBLEND = res.bundle;
      hashBLEND = res.hash;
      attBLEND = res.attestation;

      try {
        auditBLEND = audit(bundleBLEND, attBLEND, { id: "backend-attestor", publicKeyPem: (attBLEND as any).publicKeyPem || "", privateKeyPem: "", type: "rsa-2048" });
      } catch (e: any) {
        auditBLEND = false;
        pushStep?.(`Blended: audit failed — ${e?.message || String(e)}`);
      }

      pushStep(`Blended: bundle created (hash ${hashBLEND}), auditOk=${auditBLEND}`);
    } catch (e: any) {
      pushStep?.(`Blended: bundling failed — ${e?.message || String(e)}`);

      const { buildEvidenceBundle } = await import("../phases/phase3_4/schema");
      bundleBLEND = buildEvidenceBundle(`blended-fallback-${Date.now()}`, {
        decision: "ESCALATE",
        rationale: `Blended bundling failed: ${e?.message || String(e)}`,
        agreementState: "ESCALATED",
        evidence: { totalClaims: 0, groupCount: 0, distinctMiners: 0, replayHash: "" },
      } as any, { sessionId: Number(sessionId), taskIds: [] });
      hashBLEND = "fallback-blend";
      attBLEND = null;
      auditBLEND = false;
    }

    // Return structured response including steps and any LLM error
    return res.json({
      steps,
      llmError,
      llm: { envelope: envLLM, bundle: bundleLLM, hash: hashLLM, attestation: attLLM, auditOk: auditLLM },
      sim: { envelope: envSIM, bundle: bundleSIM, hash: hashSIM, attestation: attSIM, auditOk: auditSIM },
      blended: { blended, bundle: bundleBLEND, hash: hashBLEND, attestation: attBLEND, auditOk: auditBLEND },
    });
  } catch (err: any) {
    console.error(err);
    // include steps for diagnosis and stack in non-production to help debugging
    const payload: any = { error: err.message || String(err), steps };
    if (process.env.NODE_ENV !== "production") payload.stack = err.stack;
    return res.status(500).json(payload);
  }
});

export default router;
