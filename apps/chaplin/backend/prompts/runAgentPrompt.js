// prompts/runAgentPrompt.js
/**
 * Build the prompt used to run a single agent in the workgroup.
 * - agent: { name, prompt }
 * - input: user input (string)
 * - previousOutputs: array of strings (outputs in order)
 */
export function buildRunAgentPrompt({ agent, input, previousOutputs }) {
  const header = `You are the "${agent.name}" agent in a sequential workgroup.
System note: Agents run in order; you will receive the user input and the outputs from previous agents in order.
Follow your role instructions and RETURN ONLY YOUR CONTENT (no meta, no commentary).\n\n`;

  let body = `User input:\n${input}\n\nPrevious outputs:\n`;
  if (!previousOutputs || previousOutputs.length === 0) {
    body += "(none)\n\n";
  } else {
    previousOutputs.forEach((o, i) => {
      body += `Agent ${i} output:\n${o}\n\n`;
    });
  }

  body += `Role instructions (below). Execute the task described and return only the result:\n\n${agent.prompt}\n\n`;

  // Clear explicit instruction to return ONLY content
  body += `IMPORTANT: Return only your output, no JSON wrapper unless specified by your role prompt.`;

  return header + body;
}