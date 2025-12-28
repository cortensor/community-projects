import { CheckResult } from "./checks";

export function runValidation(policy: any) {
  const checks: CheckResult[] = [];

  checks.push({
    name: "MIN_VALIDATORS_DEFINED",
    passed: typeof policy.minValidators === "number" && policy.minValidators > 0,
    weight: 1,
  });

  checks.push({
    name: "AGREEMENT_THRESHOLD_VALID",
    passed:
      typeof policy.minAgreement === "number" && policy.minAgreement >= 0.5 && policy.minAgreement <= 1,
    weight: 1,
  });

  const passed = checks.filter((c) => c.passed).length;
  const policyScore = passed / checks.length;

  return {
    agreementScore: 0, // Phase 2: no inference yet
    policyScore,
    checkResults: checks,
  };
}
