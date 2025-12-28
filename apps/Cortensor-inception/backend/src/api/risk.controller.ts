import express from "express";
import { initRiskAgent, analyzeRisk } from "../adapters/adk/riskAgent";

const router = express.Router();

// POST /api/risk — run risk analysis on a TreasurySnapshot payload
router.post("/risk", async (req, res) => {
  try {
    const snapshot = req.body;
    if (!snapshot || typeof snapshot.totalUsdValue !== "number" || !Array.isArray(snapshot.positions)) {
      return res.status(400).json({ error: "invalid body: expected { totalUsdValue: number, positions: [{ token, usdValue }] }" });
    }

    // Ensure agent initialized (best-effort)
    try {
      await initRiskAgent();
    } catch (e: any) {
      // continue — analyzeRisk will fallback if needed
      console.warn("initRiskAgent failed:", e?.message || String(e));
    }

    const result = await analyzeRisk(snapshot as any);
    return res.json({ ok: true, result });
  } catch (err: any) {
    console.error(err);
    return res.status(500).json({ error: err?.message || String(err) });
  }
});

export default router;
