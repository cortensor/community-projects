import { describe, it, expect } from "vitest";
import { ValidateRequestSchema } from "../src/contracts/validate.request";

describe("ValidateRequestSchema", () => {
  const base = {
    task: { prompt: "do not run" },
    policy: { minValidators: 1, minAgreement: 0.6, timeoutMs: 1000, checks: [] },
    meta: { caller: "tester", purpose: "unit-test" },
  };

  it("accepts a valid request", () => {
    expect(() => ValidateRequestSchema.parse(base)).not.toThrow();
  });

  it("rejects minValidators === 0", () => {
    const bad = JSON.parse(JSON.stringify(base));
    bad.policy.minValidators = 0;
    expect(() => ValidateRequestSchema.parse(bad)).toThrow();
  });

  it("rejects missing timeoutMs", () => {
    const bad = JSON.parse(JSON.stringify(base));
    delete bad.policy.timeoutMs;
    expect(() => ValidateRequestSchema.parse(bad)).toThrow();
  });

  it("rejects missing checks", () => {
    const bad = JSON.parse(JSON.stringify(base));
    delete bad.policy.checks;
    expect(() => ValidateRequestSchema.parse(bad)).toThrow();
  });

  it("rejects missing meta.caller or meta.purpose", () => {
    const bad1 = JSON.parse(JSON.stringify(base));
    delete bad1.meta.caller;
    expect(() => ValidateRequestSchema.parse(bad1)).toThrow();

    const bad2 = JSON.parse(JSON.stringify(base));
    delete bad2.meta.purpose;
    expect(() => ValidateRequestSchema.parse(bad2)).toThrow();
  });
});
