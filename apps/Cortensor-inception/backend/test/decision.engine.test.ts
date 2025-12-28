import { describe, it, expect } from "vitest";
import { decideTrust } from "../src/core/decision/decision.engine";

describe("decision engine", () => {
  it("blocks when policyScore < 1", () => {
    const decision = decideTrust({ policyScore: 0.5, agreementScore: 0 }, {} as any);
    expect(decision.decision).toBe("BLOCK");
  });

  it("escalates when policyScore === 1 and no agreement score", () => {
    const decision = decideTrust({ policyScore: 1, agreementScore: 0 }, {} as any);
    expect(decision.decision).toBe("ESCALATE");
  });

  it("releases when agreementScore > 0 and policyScore === 1", () => {
    const decision = decideTrust({ policyScore: 1, agreementScore: 0.9 }, {} as any);
    expect(decision.decision).toBe("RELEASE");
  });
});
