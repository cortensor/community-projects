export function decideTrust(validation: any, policy: any) {
  if (validation.policyScore < 1) {
    return {
      decision: "BLOCK",
      confidence: 0,
      explanation: "Policy validation failed",
    };
  }

  if (validation.agreementScore === 0) {
    return {
      decision: "ESCALATE",
      confidence: 0.2,
      explanation: "No inference results yet",
    };
  }

  return {
    decision: "RELEASE",
    confidence: 0.9,
    explanation: "All trust conditions satisfied",
  };
}
