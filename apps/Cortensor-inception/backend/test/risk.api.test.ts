import { describe, it, expect, beforeAll } from "vitest";
import request from "supertest";
import app from "../src/server";

const snapshot = {
  totalUsdValue: 2_500_000,
  positions: [
    { token: "USDC", usdValue: 2_000_000 },
    { token: "ETH", usdValue: 500_000 },
  ],
};

describe("POST /api/risk", () => {
  it("returns 400 on invalid body", async () => {
    const res = await request(app).post("/api/risk").send({});
    expect(res.status).toBe(400);
  });

  it("returns a valid RiskResult shape", async () => {
    const res = await request(app).post("/api/risk").send(snapshot);
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty("result");
    expect(["LOW", "MEDIUM", "HIGH"]).toContain(res.body.result.level);
    expect(typeof res.body.result.score).toBe("number");
    expect(Array.isArray(res.body.result.issues)).toBe(true);
  });
});
