// prompts/runWorkgroupPrompt.js
/**
 * Helpers to build extremely direct prompts with a clear separation of concerns.
 * - AgentExecution: Generates ONLY plain text for context.
 * - Integrator: Consumes all text and generates ONLY a JSON object.
 * Optimized for models like LLaVA that need unambiguous instructions.
 */

/**
 * Builds a prompt for a regular agent.
 * Its ONLY goal is to produce a plain text response.
 * It is explicitly forbidden from using JSON.
 */
export function buildAgentExecutionPrompt({ agent, input, previousOutputs }) {
  // === INPUT DATA SECTION ===
  let prompt = `== INPUT DATA ==\n`;
  prompt += `User's Request: ${input}\n`;

  if (!previousOutputs || previousOutputs.length === 0) {
    prompt += `Results from Previous Steps: None. You are the first.\n`;
  } else {
    const previousOutputsText = previousOutputs
      .map((output, i) => {
        const filteredOutput = (output || "").replace("<end_of_turn>", '').trim();
        return `Result from Step ${i}:\n${filteredOutput}`;
      })
      .join("\n\n");
    prompt += `Results from Previous Steps:\n${previousOutputsText}\n`;
  }

  // === YOUR INSTRUCTIONS SECTION ===
  prompt += `\n== YOUR INSTRUCTIONS ==\n`;
  prompt += `You are the "${agent.name}". Your instructions are below. Follow them exactly.\n\n${agent.prompt}\n`;

  // === ACTION SECTION ===
  // This section is now extremely clear about the output format.
  prompt += `\n== ACTION ==\n`;
  prompt += `Generate your response now based on your instructions. Follow these critical rules:\n`;
  prompt += `1. Your response MUST be plain text. Do NOT use JSON format.\n`;
  prompt += `2. Your entire output must be ONLY the direct answer. Do not include "Understood", explanations, or any extra text.\n`;
  prompt += `3. GENERATE THE TEXT RESPONSE IMMEDIATELY.`;

  prompt += `\n\nresponse:`;
  return prompt;
}


/**
 * Builds a prompt for the final Integrator agent.
 * Its ONLY goal is to take all the previous text and create a single JSON object.
 */
export function buildIntegratorPrompt({ responseformat, outputs, workgroup }) {
  // responseformat is an object with keys->descriptions
  const rfStr = JSON.stringify(responseformat || {}, null, 2);

  const header = `You are the Integrator agent.
System note: Your job is to merge the outputs of the previous agents (they are provided below, in order)
into a single JSON object that strictly follows the response format specification provided.\n\n`;

  const outputsBlock = `Agent outputs (in order):\n${(outputs || []).map((o, idx) => `Agent ${idx} (${(workgroup?.[idx]?.name)||('Agent'+idx)}):\n${o}\n`).join("\n")}\n\n`;

  const task = `Response format specification (JSON keys and descriptions):\n${rfStr}\n\nTask:
- Produce a single JSON object that exactly matches the keys in the response format.
- Also include a top-level key "final_message" containing a human-readable concise answer for the user.
- Values should be strings or arrays as appropriate; keep them concise and ready-to-use.
- RETURN ONLY THE JSON OBJECT (no explanation, no surrounding text, no code fences). \n assistant:`;

  return header + outputsBlock + task;
}
