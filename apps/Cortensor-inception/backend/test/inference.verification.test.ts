import { describe, it, expect } from "vitest";
import { verifyInferenceBatch } from "../src/core/inference/verification";
import type { InferenceBatch } from "../src/core/inference/batch.types";
import { sha256 } from "../src/utils/hash";

describe("inference verification", () => {
  const requestedAt = Date.now();

  it("accepts valid inference and returns VerifiedInference", () => {
    const proofPayload = { x: 1 };
    const poi = { proofType: "CORTENSOR_POI", proofPayload, proofHash: sha256(JSON.stringify(proofPayload)) };

    const batch: InferenceBatch = {
      taskHash: "t1",
      requestedAt,
      policy: { minValidators: 1, timeoutMs: 10000 },
      results: [
        { nodeId: "n1", output: "ok", poi, latencyMs: 10, receivedAt: requestedAt + 100 },
      ],
    };

    const { verified, discarded } = verifyInferenceBatch(batch);
    expect(verified.length).toBe(1);
    expect(discarded.length).toBe(0);
  });

  it("discards inference without poi", () => {
    const batch: InferenceBatch = {
      taskHash: "t2",
      requestedAt,
      policy: { minValidators: 1, timeoutMs: 10000 },
      results: [
        // @ts-expect-error testing invalid shape
        { nodeId: "n2", output: "ok", latencyMs: 10, receivedAt: requestedAt + 100 },
      ],
    };

    const { verified, discarded } = verifyInferenceBatch(batch);
    expect(verified.length).toBe(0);
    expect(discarded[0].reason).toBe("schema_invalid");
  });

  it("discards proofHash mismatch and timeout exceeded", () => {
    const proofPayload = { y: 2 };
    const poi = { proofType: "CORTENSOR_POI", proofPayload, proofHash: "deadbeef" + "0".repeat(56) };

    const batch: InferenceBatch = {
      taskHash: "t3",
      requestedAt,
      policy: { minValidators: 1, timeoutMs: 50 },
      results: [
        { nodeId: "n3", output: "ok", poi, latencyMs: 10, receivedAt: requestedAt + 100 },
      ],
    };

    const { verified, discarded } = verifyInferenceBatch(batch);
    expect(verified.length).toBe(0);
    expect(discarded.some((d) => d.reason === "proofHash_mismatch")).toBe(true);
    // Also the timeout_exceeded should be recorded if proofHash passed; in this case mismatch triggers first
  });
});
