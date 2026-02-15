import crypto from "crypto";
import { RouterAdapter, RouterInferenceRequest } from "./router.types";
import { CortensorRouterConfig } from "./router.config";
import type { InferenceResult } from "../../core/inference/inference.types";

export class CortensorRouterAdapter implements RouterAdapter {
  async runInference(request: RouterInferenceRequest): Promise<InferenceResult[]> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), request.timeoutMs || CortensorRouterConfig.defaultTimeoutMs);

    try {
      const res = await (globalThis as any).fetch(`${CortensorRouterConfig.baseUrl}/infer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${CortensorRouterConfig.apiKey}`,
        },
        body: JSON.stringify({ prompt: request.prompt, n: request.minValidators }),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`Router error ${res.status}`);
      }

      const data = await res.json();

      if (!data || !Array.isArray(data.results)) return [];

      return data.results.map((r: any): InferenceResult => ({
        nodeId: r.nodeId,
        output: r.output,
        poi: {
          proofType: "CORTENSOR_POI",
          proofPayload: r.poi,
          proofHash: crypto.createHash("sha256").update(JSON.stringify(r.poi)).digest("hex"),
        },
        latencyMs: r.latencyMs,
        receivedAt: Date.now(),
      }));
    } finally {
      clearTimeout(timeout);
    }
  }
}
