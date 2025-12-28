import { listenForTrustedClaims } from "../src/adapters/cortensor/events";
import { runPhase3_3 } from "../src/phases/phase3_3";

console.log("Listening and converting claims to decisions (press Ctrl+C to stop)...");

listenForTrustedClaims((claims) => {
  try {
    const decision = runPhase3_3(claims);
    console.log("DECISION ENVELOPE");
    console.dir(decision, { depth: null });
  } catch (err) {
    console.error("Decision error:", err);
  }
});
