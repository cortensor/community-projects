// ensure env vars for router config during tests
process.env.CORTENSOR_ROUTER_URL = process.env.CORTENSOR_ROUTER_URL || "http://localhost:9999";
process.env.CORTENSOR_API_KEY = process.env.CORTENSOR_API_KEY || "testkey";

import { describe, it, expect, beforeEach, vi } from "vitest";
import { CortensorRouterAdapter } from "../src/adapters/cortensor/router.adapter";
import { CortensorRouterConfig } from "../src/adapters/cortensor/router.config";
import crypto from "crypto";

describe("CortensorRouterAdapter", () => {
  const adapter = new CortensorRouterAdapter();

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("maps router response to InferenceResult[] and computes proofHash", async () => {
    const poi = { a: 1 };
    const fakeRes = {
      ok: true,
      json: async () => ({ results: [{ nodeId: "n1", output: "o", poi, latencyMs: 10 }] }),
    } as any;

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(fakeRes));

    const res = await adapter.runInference({ prompt: "p", timeoutMs: 1000, minValidators: 1 });
    expect(res.length).toBe(1);
    expect(res[0].nodeId).toBe("n1");
    expect(res[0].output).toBe("o");
    expect(res[0].poi.proofHash).toBe(crypto.createHash("sha256").update(JSON.stringify(poi)).digest("hex"));
  });

  it("throws on non-ok HTTP response", async () => {
    const fakeRes = { ok: false, status: 500 } as any;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(fakeRes));

    await expect(adapter.runInference({ prompt: "p", timeoutMs: 1000, minValidators: 1 })).rejects.toThrow("Router error 500");
  });

  it("returns empty array if router returns no results", async () => {
    const fakeRes = { ok: true, json: async () => ({}) } as any;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(fakeRes));

    const res = await adapter.runInference({ prompt: "p", timeoutMs: 1000, minValidators: 1 });
    expect(res).toEqual([]);
  });

  it("aborts on timeout and throws", async () => {
    // simulate a fetch that never resolves but responds to abort signal
    vi.stubGlobal("fetch", vi.fn().mockImplementation((_url: string, opts: any) => {
      return new Promise((resolve, reject) => {
        const signal = opts.signal as AbortSignal;
        signal.addEventListener("abort", () => reject(new Error("The user aborted a request.")));
      });
    }));

    await expect(adapter.runInference({ prompt: "p", timeoutMs: 1, minValidators: 1 })).rejects.toThrow();
  });
});
