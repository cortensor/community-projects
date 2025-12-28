import { RiskResult, TreasurySnapshot } from "../types";
import { generateLLMOutputs } from "../../llm/client";

export async function callQwenLLM(prompt: string) {
  // Convenience wrapper that delegates to existing LLM client
  // Use default of 3 outputs and return the first one
  const outs = await generateLLMOutputs({ prompt, n: 1, temperature: 0.3 });
  return outs[0] || "";
}

export function extractJSON<T = any>(text: string): T {
  // Attempt to extract the first JSON object/array in the text
  const match = text.match(/\{[\s\S]*\}|\[[\s\S]*\]/);
  if (!match) throw new Error("no JSON found in text");
  try {
    return JSON.parse(match[0]) as T;
  } catch (e) {
    throw new Error("invalid JSON extracted");
  }
}

export const treasuryTools = {
  generateBaseRisk(snapshot: TreasurySnapshot): RiskResult {
    const posCount = snapshot.positions.length;
    let points = 0;

    // Concentration
    if (posCount === 1) points += 40;
    else if (posCount <= 3) points += 20;

    // Diversification
    const tokens = new Set(snapshot.positions.map((p) => p.token));
    if (tokens.size === 1) points += 25;

    // Size impact
    const total = snapshot.totalUsdValue;
    if (total > 10_000_000) points += 30;
    else if (total >= 1_000_000) points += 25;
    else points += 5;

    const score = Math.max(0, 100 - points);
    const level = score > 70 ? "LOW" : score >= 40 ? "MEDIUM" : "HIGH";

    const issues: string[] = [];
    if (posCount === 1) issues.push("Single position concentration");
    if (tokens.size === 1) issues.push("All funds in single token");
    if (total > 10_000_000) issues.push("Large treasury — review size impact");

    return { level, score, issues };
  },
};
