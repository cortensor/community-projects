import { test, expect } from "vitest";
import { decisionEngine } from "../decisionEngine";
import type { TrustedInferenceClaim } from "../../adapters/cortensor/types";

test("ingestTrustedClaims returns ESCALATE and accepts claims", () => {
  const claims: TrustedInferenceClaim[] = [
    {
      kind: "TrustedInferenceClaim",
      source: "cortensor",
      miner: "n1",
      output: "ok",
      authenticated: true,
      provenance: { sessionId: 1, taskId: 1, network: "cortensor" },
      receivedAt: Date.now(),
    },
  ];

  const res = decisionEngine.ingestTrustedClaims(claims);

  expect(res.decision).toBe("ESCALATE");
  expect(res.reason).toMatch(/Agreement engine not active/);
});

test("rejects unauthenticated claims and returns BLOCK", () => {
  const badClaims = [
    {
      kind: "TrustedInferenceClaim",
      source: "cortensor",
      miner: "n1",
      output: "ok",
      authenticated: false,
      provenance: { sessionId: 1, taskId: 1, network: "cortensor" },
      receivedAt: Date.now(),
    } as any,
  ];

  const res = decisionEngine.ingestTrustedClaims(badClaims as any);
  expect(res.decision).toBe("BLOCK");
  expect(res.reason).toBe("Unauthenticated claim rejected");
});
