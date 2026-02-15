import { test, expect } from "vitest";
import { runPhase3_3 } from "../phase3_3";
import type { TrustedInferenceClaim } from "../../adapters/cortensor";

function makeClaim(miner: string, output: string, session = 1, task = 1): TrustedInferenceClaim {
  return {
    kind: "TrustedInferenceClaim",
    source: "cortensor",
    miner,
    output,
    authenticated: true,
    provenance: { sessionId: session, taskId: task, network: "cortensor" },
    receivedAt: Date.now(),
  };
}

test("agreed when majority meets threshold", () => {
  const claims = [
    makeClaim("n1", "yes"),
    makeClaim("n2", "yes"),
    makeClaim("n3", "yes"),
    makeClaim("n4", "no"),
  ];

  const env = runPhase3_3(claims as TrustedInferenceClaim[]);
  expect(env.decision).toBe("RELEASE");
  expect(env.evidence.totalClaims).toBe(4);
  expect(env.evidence.distinctMiners).toBe(4);
  expect(env.agreementState).toBe("AGREED");
});

test("escalated when partial agreement", () => {
  const claims = [
    makeClaim("n1", "yes"),
    makeClaim("n2", "yes"),
    makeClaim("n3", "no"),
    makeClaim("n4", "no"),
  ];

  const env = runPhase3_3(claims);
  expect(env.decision).toBe("ESCALATE");
  expect(env.agreementState).toBe("ESCALATED");
});

test("blocked on conflict", () => {
  const claims = [makeClaim("a", "x"), makeClaim("b", "y"), makeClaim("c", "z")];
  const env = runPhase3_3(claims);
  expect(env.decision).toBe("BLOCK");
  expect(env.agreementState).toBe("CONFLICT_DETECTED");
});
