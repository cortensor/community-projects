export interface PromptPayload {
  claim: string;
  contextUrl?: string | null;
  contextText?: string | null;
  numMiners?: number;
  tavilyEvidence?: string | null;
}

export const DEEPSEEK_SYSTEM_PROMPT = `You are GPT OSS 20B embedded inside the ClaimCheck Oracle.
Your entire response must be ONE compact JSON object (no Markdown, no prose, no code fences, no arrays of nested votes) that exactly matches:
{
  "verdict": "true" | "false" | "uncertain",
  "confidence": number,   // 0-1 float
  "dispersion": number,   // 0-1 float capturing certainty spread; set 0.5 if unknown
  "reasoning": string,    // 2-3 sentences referencing concrete facts and evidence gaps
  "citations": Array<{ "source": string; "url": string | null; }>
}

Guidelines:
- Return at most 3 citations. If you have fewer than 3 high-quality sources, return fewer.
- Cite reputable sources (newsrooms, international orgs, peer-reviewed works, .gov/.edu domains). Prefer links surfaced in Tavily evidence when they align with your reasoning; drop any link that is weak, off-topic, or unverified.
- Prefer verifiable facts; when evidence conflicts, explain why and raise dispersion.
- If context is missing, state what information would resolve the claim and return verdict "uncertain".
- Do NOT include any additional keys, text outside JSON, multiple JSON objects, Markdown, or code fences.
- If you start to think out loud, stop and only return the final JSON object.`;

export const VALIDATION_SYSTEM_PROMPT = `You are an expert evaluator responsible for assessing the quality of an answer.
Return exactly one JSON object with this shape:
{
  "verdict": "normal" | "abnormal" | "inconclusive", // classification
  "score": number, // integer 0-10
  "notes": string // 1-2 concise sentences citing correctness, completeness, relevance, and clarity
}

Scoring guidance (0-10):
- 9-10 Exceptional: highly accurate, comprehensive, clear.
- 7-8 Good: accurate with minor gaps.
- 6 Acceptable: meets minimum standards.
- 4-5 Flawed: incomplete or partially inaccurate.
- 2-3 Poor: major errors or missing key elements.
- 0-1 Unacceptable: incorrect, irrelevant, or nonsensical.

Classification:
- "normal" for acceptable answers (score 6-10).
- "abnormal" for answers with notable issues (score 0-5).

Critical rules:
- Off-topic, refusal, or "I don't know" => score 0-1 and verdict "abnormal".
- Vague/generic/unsupported answers => score 3-5 and verdict "abnormal".
- If context is insufficient to judge, return verdict "inconclusive" with what is missing.
- No Markdown, no code fences, no extra keys or objects.`;

export const buildDeepSeekPrompt = ({ claim, contextUrl, contextText, numMiners, tavilyEvidence }: PromptPayload) => {
  const parts = [
    `### Claim\n${claim.trim()}`,
    contextUrl ? `### Context URL\n${contextUrl}` : '',
    contextText ? `### Context Text\n${contextText}` : '',
    tavilyEvidence ? `### Tavily Search Evidence\n${tavilyEvidence}` : '',
    numMiners ? `### Miner Cohort Size\n${numMiners}` : '### Miner Cohort Size\n3',
    '### Instructions\nAssess the claim, cite supporting + opposing evidence, and output a single JSON object that matches the schema above. If a Tavily evidence block is present, prefer those URLs, but only keep them when the facts in the page align with your reasoning; drop any Tavily link that conflicts or cannot be supported. You may add other reputable sources if they are stronger. Do not include text outside the JSON. Do not use Markdown or code fences.',
  ].filter(Boolean);

  return [DEEPSEEK_SYSTEM_PROMPT, parts.join('\n\n')].join('\n\n');
};

export const buildValidationPrompt = ({ claim, contextUrl, contextText, agentOutput }: PromptPayload & { agentOutput: string }) => {
  const parts = [
    `### Claim\n${claim.trim()}`,
    contextUrl ? `### Context URL\n${contextUrl}` : '',
    contextText ? `### Context Text\n${contextText}` : '',
    `### Candidate Assessment\n${agentOutput.trim()}`,
    '### Task\nEvaluate the candidate assessment for correctness, completeness, relevance, and clarity. Apply the schema above and return only the JSON object.',
  ].filter(Boolean);

  return [VALIDATION_SYSTEM_PROMPT, parts.join('\n\n')].join('\n\n');
};
