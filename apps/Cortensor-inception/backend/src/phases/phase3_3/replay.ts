import crypto from "crypto";
import type { TrustedInferenceClaim } from "../../adapters/cortensor";

export function replayHash(claims: TrustedInferenceClaim[]): string {
  const stable = claims
    .map((c) => ({
      miner: c.miner,
      output: c.output,
      taskId: c.provenance.taskId,
      sessionId: c.provenance.sessionId,
    }))
    .sort((a, b) => a.miner.localeCompare(b.miner));

  return crypto.createHash("sha256").update(JSON.stringify(stable)).digest("hex");
}
