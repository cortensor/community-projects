import { SessionV2 } from "./client";
import { submitTaskWeb2 } from "./web2";

export async function submitInference(sessionId: number, payload: unknown) {
  // Prefer on-chain submission when SessionV2.submit is available
  if (SessionV2 && typeof (SessionV2 as any).submit === "function") {
    const tx = await SessionV2.submit(
      sessionId,
      0,
      JSON.stringify(payload),
      0,
      "",
      [1024, 1, 1, 1, 0, 0],
      `inception-${Date.now()}`
    );

    await tx.wait();
    return { type: "onchain", txHash: tx.hash };
  }

  // Fallback to Web2 API submission if configured
  if (process.env.CORTENSOR_WEB2_URL) {
    const res = await submitTaskWeb2(sessionId, payload);
    return { type: "web2", res };
  }

  throw new Error(
    "No submission method available: configure on-chain client (CORTENSOR_RPC, CORTENSOR_PRIVATE_KEY, SESSION_V2_ADDRESS) or CORTENSOR_WEB2_URL for API submission"
  );
}
