export type AgreementState =
  | "COLLECTING"
  | "INSUFFICIENT_CLAIMS"
  | "CONFLICT_DETECTED"
  | "AGREED"
  | "ESCALATED";

export type FinalAgreementState = "AGREED" | "ESCALATED" | "CONFLICT_DETECTED";

export function deriveState(
  decision: "BLOCK" | "ESCALATE" | "RELEASE"
): FinalAgreementState {
  switch (decision) {
    case "RELEASE":
      return "AGREED";
    case "ESCALATE":
      return "ESCALATED";
    case "BLOCK":
      return "CONFLICT_DETECTED";
  }
}
