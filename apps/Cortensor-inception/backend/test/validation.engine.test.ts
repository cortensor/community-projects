import { describe, it, expect } from "vitest";
import { runValidation } from "../src/core/validation/validation.engine";

describe("validation engine", () => {
  it("fails if minValidators is missing or zero", () => {
    const policy = { minValidators: 0, minAgreement: 0.6 };
    const r = runValidation(policy as any);
    expect(r.policyScore).toBeLessThan(1);
  });

  it("passes when minValidators>0 and minAgreement in range", () => {
    const policy = { minValidators: 1, minAgreement: 0.6 };
    const r = runValidation(policy as any);
    expect(r.policyScore).toBe(1);
    expect(r.agreementScore).toBe(0);
  });
});
