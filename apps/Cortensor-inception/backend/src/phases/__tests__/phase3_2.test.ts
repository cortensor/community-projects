import { test, expect } from "vitest";
import { guardPhase3_2 } from "../phase3_2.guard";

import type { TrustedInferenceClaim } from "../../adapters/cortensor/types";

test("accepts authenticated claims", () => {
  const claim: TrustedInferenceClaim = {
    kind: "TrustedInferenceClaim",
    source: "cortensor",
    miner: "node1",
    output: "ok",
    authenticated: true,
    provenance: { sessionId: 1, taskId: 2, network: "cortensor" },
    receivedAt: Date.now(),
  };

  expect(guardPhase3_2([claim])).toBe(true);
});

test("rejects unauthenticated claims", () => {
  const badClaim = {
    kind: "TrustedInferenceClaim",
    source: "cortensor",
    miner: "node1",
    output: "ok",
    authenticated: false,
    provenance: { sessionId: 1, taskId: 2, network: "cortensor" },
    receivedAt: Date.now(),
  };

  expect(() => guardPhase3_2([badClaim as any])).toThrow("Unauthenticated claim rejected");
});
