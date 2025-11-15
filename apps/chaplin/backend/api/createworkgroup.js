import { withMiddleware } from "../lib/withMiddleware.js";
import buildCreateWorkgroupInstruction from "../prompts/createWorkgroupInstruction.js";
import buildEnhanceAgentPrompt from "../prompts/enhanceAgentPrompt.js";
import buildSummarizePrevPrompt from "../prompts/summarizePreviousWorkgroup.js";
import { generateText, generateTextAndParseJson } from "../lib/aiProvider.js";
import { withCors } from "../lib/withCors.js";
import { validatePersona, validateResponseFormat, validateWorkgroup } from "../lib/validators.js"; // <<< NOVO
import { AGENT_NAME_MAX, AGENT_PROMPT_MAX, MAX_WORKGROUP_MEMBERS, MAX_PREV } from "../lib/constants.js";

async function createWorkgroupHandler(req, res) {
  try {
    const {
      name, category, description, instructions, max_members, responseformat = null,
      previousWorkgroup = [], generateAgentName = null, generateAgentIndex = null,
      style = null, existingPrompt = null
    } = req.body || {};


    // <<< VALIDAÇÃO CENTRALIZADA >>>
    validatePersona({ name, category, description, instructions });
    validateResponseFormat(responseformat);
    validateWorkgroup(previousWorkgroup, { name: 'previousWorkgroup', max: MAX_PREV });
    
    const personaName = name.trim();
    const personaCategory = category.trim();
    const personaDescription = description.trim();
    const personaInstruction = instructions.trim();

    let maxMembers = Number.isInteger(max_members) ? max_members : parseInt(max_members || `${MAX_WORKGROUP_MEMBERS}`, 3);
    if (Number.isNaN(maxMembers) || maxMembers < 1) maxMembers = 1;
    if (maxMembers > MAX_WORKGROUP_MEMBERS) maxMembers = MAX_WORKGROUP_MEMBERS;

    const prev = previousWorkgroup.slice(0, MAX_PREV).map((a, idx) => {
      if (!a || typeof a !== "object") return null;
      return {
        name: String(a.name || `Agent${idx}`).trim().slice(0, AGENT_NAME_MAX),
        prompt: String(a.prompt || "").trim().slice(0, AGENT_PROMPT_MAX)
      };
    }).filter(Boolean);

    let genName = generateAgentName ? String(generateAgentName).trim().slice(0, AGENT_NAME_MAX) : null;
    let genIndex = (generateAgentIndex != null && Number.isInteger(Number(generateAgentIndex)) && Number(generateAgentIndex) >= 0) ? Number(generateAgentIndex) : null;
    if (genName && genIndex !== null) genName = null;

    const isEnhance = String(style || "").toLowerCase() === "enhance";

    // --- LÓGICA DO 'ENHANCE' RESTAURADA ---
    if (isEnhance) {
      let targetAgentName = genName;
      if (!targetAgentName && genIndex !== null && prev[genIndex]) {
        targetAgentName = prev[genIndex].name;
      }
      if (!targetAgentName) {
        return res.status(400).json({ error: "To enhance, provide generateAgentName or a valid generateAgentIndex for an agent in previousWorkgroup." });
      }

      const existingAgent = prev.find(p => p.name.toLowerCase() === targetAgentName.toLowerCase());
      const existingText = existingAgent ? existingAgent.prompt : (typeof existingPrompt === "string" ? existingPrompt.trim() : null);

      if (!existingText) {
        return res.status(400).json({ error: "No existing prompt found to enhance." });
      }

      let prevSummary = "No previous agents provided.";
      if (prev.length > 0) {
        try {
          const summarizeInstruction = buildSummarizePrevPrompt({ previousWorkgroup: prev, personaName, personaCategory });
          prevSummary = await generateText({ prompt: summarizeInstruction, maxTokens: 250, temperature: 0.1, sessionSize: 'big' });
        } catch (err) {
          console.error("Summarization error:", err);
          prevSummary = prev.map(p => `- ${p.name}: ${p.prompt.slice(0, 120)}`).join("\n");
        }
      }

      const enhanceInstruction = buildEnhanceAgentPrompt({
        personaName, personaCategory, personaDescription,
        agentName: targetAgentName, existingPrompt: existingText, previousWorkgroupSummary: prevSummary
      });

      const improved = await generateText({ prompt: enhanceInstruction, maxTokens: 400, temperature: 0.2, sessionSize: 'big' });
      const finalPrompt = (improved || "").trim().slice(0, AGENT_PROMPT_MAX);

      if (!finalPrompt) {
        return res.status(500).json({ error: "LLM returned empty enhancement" });
      }

      return res.status(200).json({
        workgroup: [{ name: targetAgentName, prompt: finalPrompt }],
        raw: improved
      });
    }

    // --- FLUXO DE GERAÇÃO NORMAL COM RETRY ---
    const prompt = buildCreateWorkgroupInstruction({
      name: personaName, category: personaCategory, description: personaDescription, instructions: personaInstruction,
      maxMembers, responseformat, previousWorkgroup: prev,
      generateAgentName: genName, generateAgentIndex: genIndex
    });

    const { parsedJson: parsedWorkgroup, rawText: lastLlmText } = await generateTextAndParseJson(
      { prompt: prompt, maxTokens: 1500, temperature: 0.18 },
      { expectedShape: 'array' },
      { sessionSize: 'big' } // Passa a dica para o aiProvider
    );

    const normalized = parsedWorkgroup
      .filter(i => i && typeof i === "object" && i.name && i.prompt)
      .map(it => ({
        name: String(it.name).trim().slice(0, AGENT_NAME_MAX),
        prompt: String(it.prompt).trim().slice(0, AGENT_PROMPT_MAX),
      }))
      .filter(item => !/integrator/i.test(item.name))
      .slice(0, maxMembers);

    if ((genName || genIndex !== null) && normalized.length > 1) {
      let result = [];
      let warning = undefined;
      if (genName) {
        const found = normalized.find(n => n.name.toLowerCase() === genName.toLowerCase());
        result = found ? [found] : [normalized[0]];
        if (!found) warning = "Requested single agent not found exactly; returning first generated.";
      } else { // genIndex
        if (genIndex < normalized.length) {
          result = [normalized[genIndex]];
        } else {
          result = [normalized[0]];
          warning = "Requested index out of range; returning first generated agent.";
        }
      }
      return res.status(200).json({ workgroup: result, raw: lastLlmText, warning });
    }

    return res.status(200).json({ workgroup: normalized, raw: lastLlmText });

  } catch (err) {
    if (err.name === "ValidationError") {
      return res.status(400).json({ error: err.message });
    }
    console.error("createworkgroup general error:", err);
    if (!res.headersSent) {
      res.status(500).json({ error: "Internal server error", detail: err.message });
    }
  }
}

export default withCors(withMiddleware(createWorkgroupHandler, {
  allowedMethods: ["POST"],
  requireJson: true,
  parseJson: true,
  maxBodyBytes: 200 * 1024,
  rateLimit: { windowMs: 60_000, max: 30 }
}));