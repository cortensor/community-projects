import crypto from "crypto";
import type { EvidenceBundle } from "./schema";
import { canonicalize } from "./canonical";

export function hashEvidence(bundle: EvidenceBundle): string {
  const canonical = canonicalize(bundle);

  return crypto.createHash("sha256").update(canonical).digest("hex");
}
