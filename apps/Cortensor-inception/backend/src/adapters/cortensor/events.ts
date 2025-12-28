import { SessionQueueV2 } from "./client";
import { TrustedInferenceClaim } from "./types";

type ClaimHandler = (claims: TrustedInferenceClaim[]) => void;

export function listenForTrustedClaims(handler: ClaimHandler) {
  // Guard: when running locally without a configured CORTENSOR_QUEUE_V2 address
  // the `SessionQueueV2` export is a stub object and won't expose an `on` method.
  // In that case, skip wiring the listener to avoid startup exceptions.
  if (typeof (SessionQueueV2 as any).on !== "function") {
    console.warn("SessionQueueV2.on is not available — skipping Cortensor event listener (missing config)");
    return;
  }

  SessionQueueV2.on("TaskEnded", async (sessionId: any, taskId: any) => {
    const [miners, outputs] = await SessionQueueV2.getTaskResults(sessionId, taskId);

    const claims: TrustedInferenceClaim[] = miners.map((miner: string, i: number) => ({
      kind: "TrustedInferenceClaim",
      source: "cortensor",
      miner,
      output: outputs[i],
      authenticated: true,
      provenance: {
        sessionId: Number(sessionId),
        taskId: Number(taskId),
        network: "cortensor",
      },
      receivedAt: Date.now(),
    }));

    handler(claims);
  });
}
