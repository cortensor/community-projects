import { listenForTrustedClaims } from "../src/adapters/cortensor/events";

console.log("Listening for TrustedInferenceClaim events (press Ctrl+C to stop)...");

listenForTrustedClaims((claims) => {
  console.log("CLAIMS RECEIVED");
  console.dir(claims, { depth: null });
});
