import React, { useState } from "react";

export default function ClaimForm({ onSubmit }: { onSubmit: (payload: any) => void }) {
  const [type, setType] = useState("intent");
  const [claim, setClaim] = useState("");
  const [context, setContext] = useState("");
  const [risk, setRisk] = useState(0);
  const [sessionId, setSessionId] = useState(process.env.NEXT_PUBLIC_SESSION_ID || "");
  const [useLLM, setUseLLM] = useState(false);
  const [miners, setMiners] = useState(3);
  const [temperature, setTemperature] = useState(0.7);
  const [llmApiUrl, setLlmApiUrl] = useState(process.env.NEXT_PUBLIC_LLM_API_URL || "");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (useLLM) {
          onSubmit({ useLLM, prompt: claim || "", miners, temperature, llmApiUrl, sessionId });
        } else {
          onSubmit({ type, claim, context, risk, sessionId });
        }
      }}
      className="space-y-4"
    >
      <div>
        <label className="block text-sm font-medium">Type</label>
        <select value={type} onChange={(e) => setType(e.target.value)} className="mt-1">
          <option value="intent">intent</option>
          <option value="claim">claim</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium">Claim JSON (arbitrary)</label>
        <textarea
          rows={6}
          value={claim}
          onChange={(e) => setClaim(e.target.value)}
          className="mt-1 w-full border rounded p-2"
          placeholder='{"text":"Some claim text"}'
        />
      </div>

      <div>
        <label className="block text-sm font-medium">Context (optional)</label>
        <input value={context} onChange={(e) => setContext(e.target.value)} className="mt-1 w-full border rounded p-2" />
      </div>

      <div>
        <label className="block text-sm font-medium">Risk Score (0-100)</label>
        <input type="number" value={risk} onChange={(e) => setRisk(Number(e.target.value))} className="mt-1 w-32 border rounded p-2" />
      </div>

      <div>
        <label className="inline-flex items-center gap-2">
          <input type="checkbox" checked={useLLM} onChange={(e) => setUseLLM(e.target.checked)} />
          <span className="text-sm font-medium">Use my LLM to generate claims</span>
        </label>
      </div>

      {useLLM && (
        <div className="space-y-3 border p-3 rounded bg-white">
          <div>
            <label className="block text-sm font-medium">Miners (simulated)</label>
            <input type="number" value={miners} onChange={(e) => setMiners(Number(e.target.value))} className="mt-1 w-32 border rounded p-2" />
          </div>

          <div>
            <label className="block text-sm font-medium">Temperature</label>
            <input type="number" step="0.1" value={temperature} onChange={(e) => setTemperature(Number(e.target.value))} className="mt-1 w-32 border rounded p-2" />
          </div>

          <div>
            <label className="block text-sm font-medium">LLM API URL (optional)</label>
            <input value={llmApiUrl} onChange={(e) => setLlmApiUrl(e.target.value)} className="mt-1 w-full border rounded p-2" placeholder="https://ollama-qwen.zeabur.app/api/chat" />
            <div className="text-sm text-gray-500 mt-1">If blank, server uses configured LLM_API_URL</div>
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium">Session ID</label>
        <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} className="mt-1 w-48 border rounded p-2" />
        <div className="text-sm text-gray-500 mt-1">If empty, server uses configured SESSION_ID</div>
      </div>

      <div>
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">Submit Claim</button>
      </div>
    </form>
  );
}
