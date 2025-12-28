import type { RiskResult, TreasurySnapshot } from "./types";
import { callQwenLLM, extractJSON, treasuryTools } from "./tools/treasuryTools";

let riskAgent: any = null;
let riskRunner: any = null;

export async function initRiskAgent() {
  if (riskAgent && riskRunner) return;

  // Try ADK providers (prefer '@iqai/adk', fall back to 'adk-ts')
  try {
    let AgentBuilder: any = null;

    try {
      // @ts-ignore - optional peer dependency may not be installed in dev/test env
      const mod = await import("@iqai/adk");
      AgentBuilder = mod?.AgentBuilder || mod?.default?.AgentBuilder || mod?.default || null;
    } catch (_) {
      // ignore and try adk-ts
    }

    if (!AgentBuilder) {
      try {
        // @ts-ignore - optional peer dependency may not be installed in dev/test env
        const mod = await import("adk-ts");
        AgentBuilder = mod?.AgentBuilder || mod?.Client || mod?.default || null;
      } catch (_) {
        // ignore
      }
    }

    if (!AgentBuilder) {
      console.warn("ADK AgentBuilder not available — will use LLM wrapper fallback.");
      return;
    }

    const modelName = process.env.LLM_MODEL || "qwen2.5";

    const built = await AgentBuilder.create("risk_analysis_agent")
      .withModel(modelName)
      .withInstruction(
        `You are a professional DeFi risk analyst agent.\nAnalyze the treasury snapshot and provide a risk assessment.\nConsider concentration risk, asset diversification, and treasury size.\nReturn STRICT JSON ONLY:\n{\n  \"level\": \"LOW\" | \"MEDIUM\" | \"HIGH\",\n  \"score\": number (0-100),\n  \"issues\": string[]\n}`
      )
      .build();

    riskAgent = built;
    // ADK implementations expose different runner shapes
    riskRunner = (built as any).runner || (built as any).run || (built as any).runAgent || null;
    console.log(`✅ Risk Agent initialized (ADK AgentBuilder) — model=${modelName}`);
  } catch (e: any) {
    console.warn("ADK init failed — using fallback behavior:", e?.message || String(e));
  }
}

export async function analyzeRisk(snapshot: TreasurySnapshot): Promise<RiskResult> {
  try {
    if (!riskRunner) await initRiskAgent();

    if (riskRunner) {
      // Use agent runner (best-effort; ADK implementations vary)
      try {
        const prompt = `Analyze treasury: total=${snapshot.totalUsdValue}, positions=${snapshot.positions
          .map((p) => p.token)
          .join(",")} `;
        const res = await riskRunner.call ? await riskRunner.call(prompt) : await riskRunner(prompt);
        const parsed = extractJSON<RiskResult>(String(res));

        if (
          parsed?.level && ["LOW", "MEDIUM", "HIGH"].includes(parsed.level) &&
          typeof parsed.score === "number" && Array.isArray(parsed.issues)
        ) {
          console.log("✅ Risk assessment from ADK agent");
          return parsed as RiskResult;
        }
      } catch (e: any) {
        console.warn("ADK agent failed to produce valid result, falling back:", e?.message || String(e));
      }
    }

    // Use LLM wrapper fallback (callQwenLLM + parse)
    try {
      const prompt = `You are a professional DeFi risk analyst. Provide STRICT JSON ONLY. TREASURY: total=${snapshot.totalUsdValue}; tokens=${snapshot.positions
        .map((p) => p.token)
        .join(",")}`;
      const response = await callQwenLLM(prompt);
      const parsed = extractJSON<RiskResult>(String(response));
      if (
        parsed?.level && ["LOW", "MEDIUM", "HIGH"].includes(parsed.level) &&
        typeof parsed.score === "number" && Array.isArray(parsed.issues)
      ) {
        console.log("✅ Risk assessment from LLM fallback");
        return parsed as RiskResult;
      }
    } catch (e: any) {
      console.warn("LLM fallback failed:", e?.message || String(e));
    }
  } catch (err) {
    console.warn("Unexpected risk analysis error:", err);
  }

  // Deterministic fallback
  console.log("✅ Risk assessment from deterministic tool");
  return treasuryTools.generateBaseRisk(snapshot);
}

export default {
  initRiskAgent,
  analyzeRisk,
};
