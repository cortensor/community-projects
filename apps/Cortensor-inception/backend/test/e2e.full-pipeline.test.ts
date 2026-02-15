import { test, expect } from "vitest";
import fs from "fs";
import { runFullPipeline } from "../src/utils/fullPipeline";

// This E2E test is gated to avoid running in CI unless explicitly enabled.
const RUN_E2E = process.env.E2E === "1";

if (!RUN_E2E) {
  test.skip("E2E full pipeline (skipped by default)", () => {});
} else {
  test("full pipeline end-to-end", async () => {
    const sessionId = Number(process.env.SESSION_ID || 141);
    const privateKey = fs.readFileSync(process.env.ATTESTOR_KEY || "attestor.key", "utf8");

    const result = await runFullPipeline({ sessionId, prompt: "E2E test prompt", attestorKeyPem: privateKey });

    expect(result.envelope).toBeDefined();
    expect(result.bundle).toBeDefined();
    expect(typeof result.hash).toBe("string");
    expect(result.auditOk).toBe(true);
  });
}
