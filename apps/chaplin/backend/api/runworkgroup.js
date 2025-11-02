// api/runworkgroup.js
import { withCors } from "../lib/withCors.js";
import { withMiddleware } from "../lib/withMiddleware.js";
import { runWorkgroupAndIntegrate } from "../lib/workgroupEngine.js";
import { validateWorkgroup, validateResponseFormat } from "../lib/validators.js";
import { MAX_RESPONSE_ENTRIES } from "../lib/constants.js";


async function runworkgroupHandler(req, res) {
  try {
    const { input, workgroup, workgroupresponse = {}, responseformat } = req.body || {};


    if (typeof input === "undefined") {
      throw new ValidationError("Missing required field: input");
    }
    if (!workgroup || workgroup.length === 0) {
      throw new ValidationError("workgroup must be a non-empty array");
    }
    if (typeof workgroupresponse !== "object" || workgroupresponse === null) {
      throw new ValidationError("workgroupresponse must be an object");
    }
    if (Object.keys(workgroupresponse).length > MAX_RESPONSE_ENTRIES) {
      throw new ValidationError(`workgroupresponse too large (max ${MAX_RESPONSE_ENTRIES} entries)`);
    }

    validateWorkgroup(workgroup);
    validateResponseFormat(responseformat);
    
    const result = await runWorkgroupAndIntegrate({
      input,
      workgroup,
      workgroupResponseMap: workgroupresponse,
      responseformat,
      options: {
        maxTokens: 800,
        temperature: 0.7,
        integratorMaxAttempts: 3,
        integratorMaxTokens: 900,
        integratorTemperature: 0.5
      }
    });

    // Envia a resposta de sucesso
    return res.status(200).json({
      perAgent: result.perAgent,
      generated: result.generated,
      updatedWorkgroupResponse: result.updatedWorkgroupResponse,
      final: result.final,
      validation: result.validation,
      attempts: result.attempts,
      lastRaw: result.lastRaw
    });

  } catch (err) {

    if (err.name === "ValidationError") {
      return res.status(400).json({ error: err.message });
    }
    console.error("runworkgroup handler error:", err);
    if (!res.headersSent) {
      return res.status(500).json({ error: "Internal server error", detail: err.message });
    }
  }
}

export default withCors(withMiddleware(runworkgroupHandler, {
  allowedMethods: ["POST"],
  requireJson: true,
  parseJson: true,
  maxBodyBytes: 300 * 1024,
  rateLimit: { windowMs: 60_000, max: 30 },
  requireAuth: false
}));