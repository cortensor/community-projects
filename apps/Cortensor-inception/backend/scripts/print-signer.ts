import "dotenv/config";
import { signer, SessionV2 } from "../src/adapters/cortensor/client";

async function run() {
  console.log("Checking Cortensor client configuration...");

  if (!process.env.CORTENSOR_RPC || !process.env.CORTENSOR_PRIVATE_KEY) {
    console.warn("ENV not configured: CORTENSOR_RPC or CORTENSOR_PRIVATE_KEY missing.");
  }

  if (!signer || typeof signer.getAddress !== "function") {
    console.warn("Signer not available. Ensure CORTENSOR_PRIVATE_KEY is set and provider reachable.");
  } else {
    try {
      const addr = await signer.getAddress();
      console.log("Signer address:", addr);

      // If SessionV2 has a helper to list sessions, try it
      if (SessionV2 && typeof (SessionV2 as any).getSessionsByAddress === "function") {
        try {
          const sessions = await (SessionV2 as any).getSessionsByAddress(addr);
          console.log("Sessions owned (raw):", sessions);
        } catch (err) {
          const msg = (err as any)?.message || String(err);
          console.warn("Could not fetch sessions via getSessionsByAddress:", msg);
        }
      } else if (SessionV2 && typeof (SessionV2 as any).sessions === "function") {
        console.log("SessionV2 exposes 'sessions' function; consider using it to query owned sessions.");
      } else {
        console.log("SessionV2 ABI does not expose getSessionsByAddress or sessions helper (ABI mismatch possible). See verify-abi script.");
      }
    } catch (err: any) {
      console.error("Error fetching signer address:", err.message || err);
    }
  }
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
