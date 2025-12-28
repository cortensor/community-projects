import express from "express";
import fs from "fs";
import { runFullPipeline } from "../utils/fullPipeline";

const router = express.Router();

router.post("/full-pipeline", async (req, res) => {
  try {
    const sessionId = Number(req.body.sessionId || process.env.SESSION_ID);
    const prompt = req.body.prompt || "Summarize why trust in AI should be earned.";
    const attestorKeyPath = req.body.attestorKeyPath || process.env.ATTESTOR_KEY || "attestor.key";

    if (!sessionId) return res.status(400).json({ error: "sessionId required" });

    const keyPem = fs.readFileSync(attestorKeyPath, "utf8");

    const result = await runFullPipeline({ sessionId, prompt, attestorKeyPem: keyPem });

    res.json({ ok: true, result });
  } catch (err: any) {
    res.status(500).json({ ok: false, error: err.message || String(err) });
  }
});

export default router;
