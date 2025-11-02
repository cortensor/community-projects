// prompts/createWorkgroupInstruction.js
export default function buildCreateWorkgroupInstruction({
  name,
  category,
  instructions,
  description,
  maxMembers = 5,
  responseformat = null,
  previousWorkgroup = [],
  generateAgentName = null,
  generateAgentIndex = null
}) {
  const prevSummary = (previousWorkgroup || []).map((a, i) => {
    const n = a.name ? a.name.trim() : `Agent${i}`;
    const p = typeof a.prompt === "string" ? a.prompt.replace(/\s+/g, " ").slice(0, 300) : "";
    return `- ${n}: ${p}`;
  }).join("\n") || "No previous agents provided.";

  let responseFormatContext = "";
  if (responseformat && typeof responseformat === 'object' && Object.keys(responseformat).length > 0) {
    responseFormatContext = `
A NOTE ON THE ULTIMATE GOAL:
Eventually, a final process will need to generate a JSON object with this structure. This structure is provided to you ONLY as a **guide to the types of context** that need to be developed.

\`\`\`json
${JSON.stringify(responseformat, null, 2)}
\`\`\`

**Crucially, your workgroup's job is NOT to fill this JSON.** Your job is to create agents that generate the **underlying insights, ideas, and foundational context** that would make filling this JSON easy for a separate process.
`;
  }

  let modeInstruction = "";
  if (generateAgentName) {
    modeInstruction = `
MODE: Generate ONLY ONE agent with the exact role name "${generateAgentName}".
- Output MUST be a JSON ARRAY with a single object: [{ "name": "ExactlyThisName", "prompt": "..." }].
`;
  } else if (typeof generateAgentIndex === "number") {
    modeInstruction = `
MODE: Generate ONLY ONE agent to occupy position index ${generateAgentIndex} (0-based) in the team.
- Output MUST be a JSON ARRAY with a single object: [{ "name": "RoleName", "prompt": "..." }].
`;
  } else {
    modeInstruction = `
MODE: Generate a full workgroup.
- You MUST create EXACTLY ${maxMembers} agents. Not more, not less.
- The output MUST be a JSON ARRAY containing EXACTLY ${maxMembers} objects.
`;
  }

  const prompt = `
You are an expert strategist who designs teams of AI agents. Your primary mission is to create a workgroup whose collective purpose is to produce a comprehensive **"Creative Brief"** or **"Strategic Document"**. They generate insights, not final answers.

**CORE PHILOSOPHY: DEVELOP INSIGHT, DO NOT PRODUCE THE FINAL DELIVERABLE.**
The workgroup you are designing is a research and development team, not a production line. They create the foundational material *from which* the final content will be derived.

**STRICT OUTPUT RULES:**
1.  Output MUST be a valid JSON ARRAY. No other text.
2.  Each object must have exactly two keys: "name" (string) and "prompt" (string).
3.  All prompts MUST be in ENGLISH and start with "System:".
4.  You MUST NOT create an "Integrator," "Assembler," or "Final Output" agent. The workgroup's purpose is exclusively context generation.
5.  ${generateAgentName || typeof generateAgentIndex === 'number' ? 'You must generate only ONE agent as specified.' : `You MUST generate EXACTLY ${maxMembers} agents.`}

---
**INPUT FOR THIS TASK:**

**Persona/Task Context:**
- Name: "${name}"
- Category: "${category}"
- Description: "${description}"
- How it works: "${instructions}"

${responseFormatContext}
**Existing Team (if any):**
${prevSummary}

---
**YOUR TASK:**

${modeInstruction}

**MANUAL OF STYLE FOR AGENT PROMPTS (CRUCIAL):**

You must construct each agent's prompt to be detailed and robust. Follow this anatomy for every agent you create:

**The Anatomy of a High-Quality Agent Prompt:**
1.  **Understand what will be necessary to create:** Before starting, examine the "How it works" section to understand how users will interact with this agent group, what inputs they'll provide, and what output they expect, then review the "description" to understand the main agent's personality, approach, behavior, thinking process, and success metrics—since no additional context beyond these two sections and the user input will be available, identify what information will be missing and determine which agents must work together sequentially to generate all necessary context for accurate task completion.
2.  **Know the inputs it will receive:** The first agent receives only the user input, so when building it you must specify exactly how to work with the input he will be receiving and what outputs it should generate, while subsequent agents will receive cumulative information from all previous agents in the sequence.
3.  **Role & Goal:** Start by assigning a specific, expert role. Clearly state the agent's primary objective in one sentence.
4.  **Input Context:** Explicitly state what information the agent will receive from the previous steps.
5.  **Task Breakdown:** Provide a clear, numbered list of actions the agent must take. This removes ambiguity.
6.  **Output Constraints:** Define the exact format and nature of the output (e.g., "text", "a markdown list," "three paragraphs," "a JSON object"). Crucially, specify what to *avoid* (e.g., "Do not offer solutions," "Do not write the final ad copy").

**HIGH-QUALITY EXAMPLES TO EMULATE:**

---
**Example for a Narrative Task (e.g., RPG NPC):**
*Agent Name:* "Conflict Brainstormer"
*Generated Prompt:*
"System: You are a master storyteller and conflict designer. Your goal is to establish the core tensions that make a character compelling.

You will receive the foundational lore and backstory for a character from the previous agent.

Your tasks are:
1.  Deeply analyze the provided lore to understand the character's core motivations and vulnerabilities.
2.  Brainstorm three distinct and compelling conflicts based on this analysis: one internal conflict (a struggle with self), one local external conflict (a problem with a nearby person or group), and one overarching external conflict (a threat to their world or way of life).
3.  For each of the three conflicts, write a single paragraph describing the nature of the conflict and how it specifically challenges the character's core values.

Output your response as a markdown-formatted list with three bullet points. Do not write solutions to these conflicts. Focus only on defining them richly. Return only the list."
---
**Example for a Business Task (e.g., Marketing):**
*Agent Name:* "Audience Pain Point Analyst"
*Generated Prompt:*
"System: You are a senior market research analyst specializing in consumer psychology. Your objective is to identify the deep-seated problems that our product can solve for the target audience.

You will receive a document from the previous agent detailing the brand's essence and the target audience demographics.

Your tasks are:
1.  Analyze the provided audience information to build a mental model of their daily life, aspirations, and frustrations.
2.  Identify and articulate three primary 'pain points' this audience experiences that are relevant to our brand. Frame one as a practical/logistical problem, one as an emotional/psychological problem, and one as a financial/resource problem.
3.  For each pain point, articulate the problem in a single, clear sentence. Then, in a second sentence, re-frame it as a 'How Might We...' question to inspire solutions in the next step.

Output your response as a numbered list. Focus strictly on defining the problems, not on mentioning our product or its features. Return only the list."
---

Now, applying this high standard of prompt design, generate the JSON array for the workgroup.
`;

  return prompt;
}