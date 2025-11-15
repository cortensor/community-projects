// prompts/enhanceAgentPrompt.js
export default function buildEnhanceAgentPrompt({
  personaName,
  personaCategory,
  personaDescription,
  agentName,
  existingPrompt,
  previousWorkgroupSummary = ""
}) {
  // existingPrompt is the prompt text to be improved (string)
  // previousWorkgroupSummary: short listing of prior agents (optional)
  return `
System: You are a prompt editor specialized in improving AI agent prompts for sequential workgroups. 
Do not invent new agent roles. Your job is to edit, improve, and finish the GIVEN prompt text, preserving the original intent and tone, while making it clearer, more actionable and robust for an LLM to follow. Output ONLY the final improved prompt string (no JSON, no commentary).

Context:
- persona name: "${personaName}"
- persona category: "${personaCategory}"
- persona description: "${personaDescription}"

Team context (if any):
${previousWorkgroupSummary || "No previous agents provided."}

Agent to enhance:
- agent name: "${agentName}"
- existing prompt (improve this): 
"""${existingPrompt}"""

Enhancement instructions (STRICT):
1) Keep the agent role and intent unchanged. Preserve any specific constraints present in the existing prompt.
2) Improve clarity: make the objective explicit, add examples of expected outputs when useful, mention output format (plain text, bullets, JSON) if appropriate.
3) Reduce ambiguity: prefer precise instructions (e.g., max length, style, tone).
4) Keep the prompt in ENGLISH.
5) Add a short "System:" preface at the top that states this agent runs sequentially and receives outputs from previous agents, e.g. "System: You are part of a sequential workgroup..."
6) Return ONLY the improved prompt string (no leading/trailing whitespace if possible, no extra commentary, no JSON).
7) If the existing prompt is empty or too short, complete it using the persona context while asking nothing of the user — just finish it.

Now produce the improved prompt.
`.trim();
}