import fetch from "node-fetch";

export type LLMOptions = {
  apiUrl?: string; // full URL to chat API
  model?: string;
  prompt: string;
  n?: number;
  temperature?: number;
  apiKey?: string;
};

export async function generateLLMOutputs(opts: LLMOptions): Promise<string[]> {
  const apiUrl = opts.apiUrl || process.env.LLM_API_URL || "https://ollama-qwen.zeabur.app/api/chat";
  const model = opts.model || process.env.LLM_MODEL || "qwen";
  const n = opts.n || 3;
  const temp = typeof opts.temperature === "number" ? opts.temperature : Number(process.env.LLM_TEMPERATURE || 0.7);
  const apiKey = opts.apiKey || process.env.LLM_API_KEY || undefined;
  const provider = (process.env.LLM_PROVIDER || (opts as any).provider || "auto").toLowerCase();

  const results: string[] = [];

  // Attempt to use adk-ts if configured or in auto mode
  if (provider === "adk" || provider === "auto") {
    try {
      // optional import – may not be installed in all environments
      // @ts-ignore
      const adk = await import("adk-ts");
      // try common entrypoints: Model, Client, or default export
      const ModelClass = adk?.Model || adk?.Client || adk?.default || null;

      if (ModelClass) {
        // instantiate client if constructor
        let client: any;
        try {
          client = typeof ModelClass === "function" ? new ModelClass({ apiKey, model }) : ModelClass;
        } catch (e: any) {
          client = ModelClass;
        }

        // try a few common APIs
        const outputs: string[] = [];
        for (let i = 0; i < n; i++) {
          const prompt = `${opts.prompt}\n\n#seed:${i}`;
          try {
            let reply: any = null;

            if (client.chat) {
              reply = await client.chat({ messages: [{ role: "user", content: prompt }], temperature: temp, model });
              outputs.push(reply?.content || reply?.message || reply?.text || JSON.stringify(reply));
            } else if (client.generate) {
              reply = await client.generate({ input: prompt, temperature: temp, model });
              outputs.push(reply?.text || reply?.output || JSON.stringify(reply));
            } else if (client.call) {
              reply = await client.call(prompt);
              outputs.push(reply?.text || reply?.output || JSON.stringify(reply));
            } else if (typeof client === "function") {
              // functional client
              reply = await client({ prompt, temperature: temp, model, apiKey });
              outputs.push(reply?.text || reply?.content || JSON.stringify(reply));
            } else {
              // unsupported client shape — break to fallback
              throw new Error("adk-ts client has unsupported API shape");
            }
          } catch (e: any) {
            // If any adk call fails, fallback to HTTP-based path below
            console.warn("adk-ts invocation failed, falling back to HTTP client:", e?.message || String(e));
            throw e;
          }
        }

        if (outputs.length === n) return outputs.map((s) => String(s || "").trim());
      }
    } catch (e: any) {
      // ignore — we'll fallback to the HTTP fetch implementation
      // but surface a console message for diagnostics
      console.warn("adk-ts provider not available or failed, falling back to fetch-based LLM client:", e?.message || String(e));
    }
  }

  // helper that performs one request and attempts to extract a usable string
  async function singleRequest(promptPayload: any) {
    const headers: any = { "Content-Type": "application/json" };
    if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

    const res = await fetch(apiUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(promptPayload),
    });

    if (!res.ok) {
      const t = await res.text();
      const msg = `LLM api error ${res.status}: ${t}`;
      const e: any = new Error(msg);
      e.status = res.status;
      throw e;
    }

    const text = await res.text();
    let json: any = null;
    try {
      json = JSON.parse(text);
    } catch (_e) {
      json = null;
    }

    if (json) {
      if (json?.message?.content) return String(json.message.content).trim();
      if (json?.choices && json.choices[0]) {
        const c = json.choices[0];
        return String(c.message?.content || c.text || c.delta?.content || "").trim();
      }
      if (json?.generated_text) return String(json.generated_text).trim();
      if (json?.text) return String(json.text).trim();
      return String(JSON.stringify(json)).trim();
    }

    return String(text).trim();
  }

  for (let i = 0; i < n; i++) {
    // minor prompt variation to induce diversity
    const prompt = `${opts.prompt}\n\n#seed:${i}`;

    // Provider-friendly payload
    const body = {
      model,
      messages: [{ role: "user", content: prompt }],
      temperature: temp,
    } as any;

    // Retry with exponential backoff for transient failures
    const maxRetries = 3;
    let attempt = 0;
    let lastErr: any = null;

    while (attempt <= maxRetries) {
      try {
        const extracted = await singleRequest(body);
        results.push(extracted);
        lastErr = null;
        break;
      } catch (err: any) {
        lastErr = err;
        attempt++;

        // If it's a 4xx that's not 429, don't retry
        if (err?.status && err.status >= 400 && err.status < 500 && err.status !== 429) {
          // Try a more compact payload before giving up
          if (attempt === 1) {
            try {
              const compact = { model, prompt };
              const extracted = await singleRequest(compact);
              results.push(extracted);
              lastErr = null;
              break;
            } catch (compactErr) {
              lastErr = compactErr;
            }
          }
          break;
        }

        if (attempt > maxRetries) break;

        // backoff with jitter
        const backoff = Math.pow(2, attempt) * 200 + Math.floor(Math.random() * 200);
        await new Promise((r) => setTimeout(r, backoff));
      }
    }

    // If after retries we still didn't produce output, throw so callers can fallback
    if (lastErr) throw lastErr;
  }

  return results;
}
