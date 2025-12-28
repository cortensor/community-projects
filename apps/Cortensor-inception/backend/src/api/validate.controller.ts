import express from "express";
import { ValidateRequestSchema } from "../contracts/validate.request";
import { createSession } from "../core/session/session.service";
import { runValidation } from "../core/validation/validation.engine";
import { decideTrust } from "../core/decision/decision.engine";
import { generateEvidence } from "../core/evidence/evidence.service";

const router = express.Router();

router.post("/", async (req, res) => {
  try {
    const parsed = ValidateRequestSchema.parse(req.body);

    const session = await createSession(parsed);

    const validationResult = runValidation(parsed.policy);

    const decision = decideTrust(validationResult, parsed.policy);

    const evidence = await generateEvidence(session, validationResult, decision);

    return res.json({
      decision: decision.decision,
      confidence: decision.confidence,
      reason: decision.explanation,
      evidence,
      stats: {
        validatorsUsed: 0,
        agreementScore: validationResult.agreementScore,
        policyScore: validationResult.policyScore,
        latencyMs: Date.now() - Number(session.createdAt),
      },
    });
  } catch (err: any) {
    if (err?.errors) {
      return res.status(400).json({ error: err.errors });
    }
    console.error("/validate handler error:", err?.message ?? err, err?.stack ?? "");
    return res.status(500).json({ error: "internal_error" });
  }
});

export default router;
