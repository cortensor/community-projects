import { Router } from "express";

const router = Router();

router.post("/infer-escrow", async (req, res) => {
  const { prompt } = req.body || {};

  // Dummy logic: if prompt contains "danger" -> HOLD, else RELEASE.
  const lower = (prompt || "").toString().toLowerCase();
  if (lower.includes("danger") || lower.includes("unsafe")) {
    return res.json({ decision: "HOLD", confidence: 0.97 });
  }

  // Default dummy response to unblock frontend
  return res.json({ decision: "RELEASE", confidence: 0.9 });
});

export default router;
