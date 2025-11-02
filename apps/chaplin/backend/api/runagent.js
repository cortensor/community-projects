import { withCors } from "../lib/withCors.js";
import { withMiddleware } from "../lib/withMiddleware.js";
import { runAgentsSequentially } from "../lib/workgroupEngine.js";
import { validateWorkgroup } from "../lib/validators.js"; // <<< NOVO
import { MAX_RESPONSE_ENTRIES } from "../lib/constants.js";

async function runAgentHandler(req, res) {
  try {
    const { input, workgroup, workgroupresponse = {}, targetAgentName = null } = req.body || {};

    validateWorkgroup(workgroup);

    // Validações específicas deste endpoint
    if (typeof input === "undefined") {
      return res.status(400).json({ error: "Missing input" });
    }
    if (typeof workgroupresponse !== "object" || workgroupresponse === null) {
      return res.status(400).json({ error: "workgroupresponse must be an object" });
    }
    if (Object.keys(workgroupresponse).length > MAX_RESPONSE_ENTRIES) {
      return res.status(400).json({ error: `workgroupresponse too large (max ${MAX_RESPONSE_ENTRIES} entries)` });
    }

    // Normalize agent names for matching (case-insensitive)
    const workgroupNames = workgroup.map((w) => String(w.name || "").trim());
    const wgNameSetLower = new Set(workgroupNames.map((n) => n.toLowerCase()));

    // If targetAgentName provided, ensure it exists in workgroup (case-insensitive)
    let stopAt = targetAgentName;
    if (targetAgentName) {
      if (!wgNameSetLower.has(String(targetAgentName).trim().toLowerCase())) {
        res.statusCode = 400;
        res.setHeader("Content-Type", "application/json");
        res.end(
          JSON.stringify({
            error: "targetAgentName not found in provided workgroup",
          })
        );
        return;
      }
    } else {
      // find first missing agent by checking workgroupresponse map keys (case-insensitive)
      const filled = new Set(
        Object.keys(workgroupresponse || {}).map((k) =>
          String(k).trim().toLowerCase()
        )
      );
      const firstMissing = workgroup.find(
        (w) => !filled.has(String(w.name).trim().toLowerCase())
      );
      stopAt = firstMissing ? firstMissing.name : null;
    }

    if (!stopAt) {
      // nothing to do: compose perAgent list showing prefilled outputs where available
      const perAgent = workgroup.map((w) => {
        const keyExact = Object.keys(workgroupresponse).find(
          (k) =>
            String(k).trim().toLowerCase() ===
            String(w.name).trim().toLowerCase()
        );
        const output =
          typeof keyExact !== "undefined" ? workgroupresponse[keyExact] : null;
        return { name: w.name, output, source: "prefilled" };
      });

      res.statusCode = 200;
      res.setHeader("Content-Type", "application/json");
      res.end(
        JSON.stringify({
          message: "All agents already filled",
          updatedWorkgroupResponse: workgroupresponse,
          generated: [],
          perAgent,
        })
      );
      return;
    }

    // Run agents sequentially until stopAt (inclusive), skipping already filled agents
    const result = await runAgentsSequentially({
      input,
      workgroup,
      workgroupResponseMap: workgroupresponse,
      options: {
        stopAtAgentName: targetAgentName,
        maxTokens: 800,
        temperature: 0.7,
      },
    });

    // Return the merged mapping and generated outputs
    res.statusCode = 200;
    res.setHeader("Content-Type", "application/json");
    res.end(
      JSON.stringify({
        updatedWorkgroupResponse: result.updatedWorkgroupResponse,
        generated: result.generated,
        perAgent: result.perAgent,
      })
    );
    return;
  } catch (err) {
    // <<< TRATAMENTO DE ERRO MELHORADO >>>
    if (err.name === "ValidationError") {
      return res.status(400).json({ error: err.message });
    }
    console.error("runagent handler error:", err);
    if (!res.headersSent) {
      res.status(500).json({ error: "Internal server error", detail: err.message });
    }
  }
}

export default withCors(withMiddleware(runAgentHandler, {
  allowedMethods: ["POST"],
  requireJson: true,
  parseJson: true,
  maxBodyBytes: 200 * 1024,
  rateLimit: { windowMs: 60_000, max: 30 }
}));