// /lib/models/GeminiBase.js
let GoogleGenAIClient = null;

export default class GeminiBase {
  constructor({ key = "gemini-base", modelName = null } = {}) {
    this.key = key;
    this.modelName = modelName || process.env.GENAI_MODEL || "gemini-2.5-flash";
    this.apiKey = process.env.GENAI_API_KEY || null;
    this.apiUrl = process.env.GENAI_API_URL || null;
    this.client = null;

    // flags para evitar tentar importar várias vezes desnecessariamente
    this._sdkTried = false;
    this._sdkAvailable = false;
  }

  // tenta importar o SDK e inicializar o client (lazy, assíncrono)
  async _tryInitSdk() {
    if (this._sdkTried) return;
    this._sdkTried = true;
    if (!this.apiKey) return;

    try {
      const mod = await import("@google/genai");
      // suporte a formas diferentes de export
      const Candidate = mod?.GoogleGenAI ?? mod?.default?.GoogleGenAI ?? mod?.default;
      if (Candidate) {
        this.client = new Candidate({ apiKey: this.apiKey });
        this._sdkAvailable = true;
      }
    } catch (e) {
      // SDK não disponível -> fallback para REST
      this.client = null;
      this._sdkAvailable = false;
    }
  }

  // helper para obter fetch (usa global se existir, senão importa node-fetch)
  async _getFetch() {
    if (typeof fetch !== "undefined") return fetch;
    const mod = await import("node-fetch");
    return mod.default ?? mod;
  }

  async generateText({ prompt, maxTokens = 512, temperature = 0.7 } = {}) {
    if (!prompt) throw new Error("prompt required");

    // tenta inicializar SDK se possível
    await this._tryInitSdk();

    // Se SDK estiver pronto, use-o
    if (this.client) {
      try {
        const response = await this.client.models.generateContent({
          model: this.modelName,
          contents: prompt,
        });

        if (response && typeof response.text === "string") return response.text;
        if (response && typeof response === "string") return response;
        return JSON.stringify(response);
      } catch (err) {
        throw new Error(`Gemini SDK error: ${err.message || String(err)}`);
      }
    }

    // fallback para REST
    if (this.apiUrl && this.apiKey) {
      try {
        const fetchFn = await this._getFetch();
        const res = await fetchFn(this.apiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${this.apiKey}`,
          },
          body: JSON.stringify({
            model: this.modelName,
            prompt,
            maxTokens,
            temperature,
          }),
          // node-fetch v3 não aceita timeout aqui — se quiser timeout, use AbortController
        });

        if (!res.ok) {
          const text = await res.text().catch(() => "<no body>");
          throw new Error(`HTTP ${res.status}: ${text}`);
        }

        const json = await res.json().catch(() => null);
        if (!json) throw new Error("Empty JSON response from GENAI API");

        if (typeof json.text === "string") return json.text;
        if (json.output?.[0]?.content?.[0]?.text) return json.output[0].content[0].text;
        return typeof json === "string" ? json : JSON.stringify(json);
      } catch (err) {
        throw new Error(`Gemini REST error: ${err.message || String(err)}`);
      }
    }

    throw new Error("No Gemini client configured (set GENAI_API_KEY and install @google/genai or set GENAI_API_URL)");
  }
}
