import { describe, it, expect } from "vitest";
import { analyzeRisk } from "../src/adapters/adk/riskAgent";

const snapshot = {
  totalUsdValue: 2_500_000,
  positions: [
    { token: "USDC", usdValue: 2_000_000 },
    { token: "ETH", usdValue: 500_000 },
  ],
};

describe("ADK Risk Agent (fallback behaviour)", () => {
  it("returns a valid RiskResult shape using deterministic fallback when ADK/LLM unavailable", async () => {
    const res = await analyzeRisk(snapshot as any);
    expect(res).toHaveProperty("level");
    expect(res).toHaveProperty("score");
    expect(Array.isArray(res.issues)).toBe(true);
    expect(["LOW", "MEDIUM", "HIGH"]).toContain(res.level);
    expect(typeof res.score).toBe("number");
  });
});