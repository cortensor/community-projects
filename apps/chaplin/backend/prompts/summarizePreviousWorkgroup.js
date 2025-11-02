// prompts/summarizePreviousWorkgroup.js
export default function buildSummarizePrevPrompt({ previousWorkgroup = [], personaName = "", personaCategory = "" }) {
  /*
    Build an instruction to summarize a list of agent objects.
    The LLM should return a short, human-readable summary where each line has:
      AgentName: one-sentence objective (what that agent does / expected output)
    Keep each summary concise (max 20 words). Return ONLY the lines (no JSON, no extra commentary).
  */
  const itemsPreview = previousWorkgroup
    .map((a, i) => {
      const name = a.name ? String(a.name).trim() : `Agent${i}`;
      const p = a.prompt ? String(a.prompt).replace(/\s+/g, " ").slice(0, 300) : "";
      return `- ${name}: ${p}`;
    })
    .slice(0, 20) // safety: preview only up to 20 items
    .join("\n");

  return `
You are an assistant that summarizes agent roles and their objectives for a developer/user.
Context: persona name="${personaName}", category="${personaCategory}".

Input: a list of agents and their full prompt text (below). For each agent, produce ONE concise summary line in English:
  AgentName: <one-sentence objective / expected output>
Guidelines:
  - Each line must be at most ~20 words.
  - Use active, clear verbs (e.g., "write a 3-line dialog", "enrich lore with 3 facts", "format output as JSON").
  - If the prompt text is short or empty, infer the likely objective from the role name.
  - Return ONLY the summary lines, one per agent, in the same order as the input. Do NOT output any extra text, headings or JSON.
  - Example output lines:
      Storyteller: produce a vivid 4-6 sentence backstory for the persona.
      DialogWriter: create 3 short lines of in-character dialogue with tone instructions.

Agents to summarize (input preview):
${itemsPreview}

Now produce the concise summary lines as described, one per agent.
`.trim();
}