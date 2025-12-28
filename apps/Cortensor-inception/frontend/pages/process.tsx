"use client";

import React, { useState } from "react";
import Link from "next/link";

type Source = {
  source: string;
  text: string;
  decision: string;
  confidence: number;
};

type Blended = {
  decision: string;
  agreementState: string;
  rationale: string;
  diffs: string[];
  sources: Source[];
};

function blendSources(a: Source, b: Source): Blended {
  const diffs: string[] = [];
  if (a.decision !== b.decision) diffs.push("decision");
  if (Math.abs(a.confidence - b.confidence) > 0.25) diffs.push("confidence");

  const decision = a.decision === b.decision ? a.decision : "ESCALATE";
  const agreementState = a.decision === b.decision ? "AGREED" : "ESCALATED";
  const rationale = `AI: ${a.text}\nSim: ${b.text}`;

  return { decision, agreementState, rationale, diffs, sources: [a, b] };
}

export default function ProcessPage() {
  // expose raw response for debugging
  const [rawResponse, setRawResponse] = useState<any>(null);
  const [text, setText] = useState("");
  const [result, setResult] = useState<Blended | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<string[]>([]);

  // Always use backend processing for robust handling of arbitrary inputs
  async function onProcess(e?: React.FormEvent) {
    e?.preventDefault();
    setLoading(true);
    setResult(null);
    setProgress(["Starting backend processing..."]);

    try {
      const r = await fetch("/api/claims/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, miners: 3, temperature: 0.7, sessionId: Number(process.env.NEXT_PUBLIC_SESSION_ID || 1) }),
      });
      const j = await r.json();

      // show steps if provided
      if (Array.isArray(j?.steps)) setProgress(j.steps);

      if (!r.ok) {
        // show server error and display a safe ESCALATE result
        setRawResponse(j);
        setResult({ decision: "ESCALATE", agreementState: "ESCALATED", rationale: `Backend error: ${j?.error || "unknown"}`, diffs: [], sources: [{ source: "AI", text, decision: "ESCALATE", confidence: 0.5 }, { source: "Simulator", text: `Simulated check: ${text}`, decision: "ESCALATE", confidence: 0.5 }] });
        return;
      }

      // convert blended.blended to our local display shape safely
      const b = j?.blended?.blended || { decision: "ESCALATE", agreementState: "ESCALATED", rationale: "no blended data", diffs: [] };

      const sources = [
        { source: "AI", text: j?.llm?.envelope?.decision ? text : text, decision: j?.llm?.envelope?.decision || (b.decision === "RELEASE" ? "RELEASE" : "ESCALATE"), confidence: 0.55 },
        { source: "Simulator", text: `Simulated check: ${text}`, decision: j?.sim?.envelope?.decision || (b.decision === "RELEASE" ? "RELEASE" : "ESCALATE"), confidence: 0.5 },
      ];

      const blendedLocal: Blended = {
        decision: b.decision,
        agreementState: b.agreementState,
        rationale: b.rationale,
        diffs: b.diffs || [],
        sources,
      };

      setResult(blendedLocal);
      setRawResponse(j);
    } catch (err: any) {
      console.error(err);
      setRawResponse({ error: err?.message || String(err) });
      setResult({ decision: "ESCALATE", agreementState: "ESCALATED", rationale: `Client error: ${err?.message || String(err)}`, diffs: [], sources: [{ source: "AI", text, decision: "ESCALATE", confidence: 0.5 }, { source: "Simulator", text: `Simulated check: ${text}`, decision: "ESCALATE", confidence: 0.5 }] });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-white text-black px-8 py-12">
      <nav className="mb-8 flex items-center gap-6">
        <Link href="/" className="font-semibold underline">Home</Link>
      </nav>

      <h1 className="text-4xl font-black mb-6">Process Text — Blended Analysis</h1>

      <form onSubmit={onProcess} className="max-w-3xl">
        <label className="block font-semibold mb-2">Enter the text to analyze</label>
        <textarea
          className="w-full border-4 border-black p-4 min-h-[160px] mb-4"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste AI output, claim text, or a short description..."
        />

        <div className="flex items-center gap-4">
          <button type="submit" className="px-6 py-3 border-4 border-black font-black bg-black text-white" disabled={loading}>
            {loading ? "Processing…" : "Process"}
          </button>

          <button type="button" className="px-6 py-3 border border-black font-semibold" onClick={() => { setText(""); setResult(null); (setRawResponse as any)?.({ raw: null }); }}>
            Clear
          </button>
        </div>

        {/* loading bar */}
        {loading && (
          <div className="mt-4">
            <div className="relative w-full h-2 bg-black/10 overflow-hidden mb-2">
              <div className="absolute left-0 top-0 h-full bg-black animate-[progress_2s_linear_infinite]" style={{ width: "40%" }} />
            </div>

            {/* Progress steps */}
            <div className="text-sm text-black/70">
              <ul className="list-disc pl-6">
                {progress.length === 0 && <li>Processing…</li>}
                {progress.map((p, i) => (
                  <li key={i} className="truncate max-w-2xl">{p}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </form>

      <section className="mt-10 max-w-3xl">
        {!result && !loading && <div className="text-black/60">No analysis yet — enter text and press Process.</div>}

        {result && (
          <div className="border-4 border-black p-6 bg-white">
            <h2 className="font-black">Blended Result</h2>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <div className="text-sm text-black/70">Decision</div>
                <div className="mt-2 font-bold text-xl">{result.decision}</div>
              </div>

              <div>
                <div className="text-sm text-black/70">Agreement</div>
                <div className="mt-2 font-bold">{result.agreementState}</div>
              </div>

              <div>
                <div className="text-sm text-black/70">Diffs</div>
                <div className="mt-2">{result.diffs.length ? result.diffs.join(", ") : "none"}</div>
              </div>
            </div>

            <div className="mt-4 text-sm text-black/70 whitespace-pre-wrap">{result.rationale}</div>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              {result.sources.map((s, i) => (
                <div key={i} className="p-4 border border-black/10">
                  <div className="text-xs text-black/70">{s.source}</div>
                  <div className="mt-2 text-sm whitespace-pre-wrap">{s.text}</div>
                  <div className="mt-3 text-sm">Decision: <strong>{s.decision}</strong> — Confidence: {(s.confidence * 100).toFixed(0)}%</div>
                </div>
              ))}
            </div>

            {/* Raw JSON + Attestations */}
            {rawResponse && (
              <div className="mt-6">
                <h3 className="font-semibold">Raw backend response</h3>
                <pre className="mt-2 p-4 bg-gray-50 border border-black/5 max-h-96 overflow-auto text-xs">{JSON.stringify(rawResponse || null, null, 2)}</pre>

                {/* Attestation quick view */}
                {rawResponse?.llm?.attestation && (
                  <div className="mt-4 text-sm">
                    <div className="font-semibold">LLM attestation</div>
                    <div>signer: {rawResponse.llm.attestation.signer}</div>
                    <div>signature: <code className="break-all">{rawResponse.llm.attestation.signature}</code></div>
                    <div>auditOk: {String(rawResponse.llm.auditOk)}</div>
                  </div>
                )}

                {rawResponse?.sim?.attestation && (
                  <div className="mt-4 text-sm">
                    <div className="font-semibold">Simulator attestation</div>
                    <div>signer: {rawResponse.sim.attestation.signer}</div>
                    <div>signature: <code className="break-all">{rawResponse.sim.attestation.signature}</code></div>
                    <div>auditOk: {String(rawResponse.sim.auditOk)}</div>
                  </div>
                )}

                {rawResponse?.blended?.attestation && (
                  <div className="mt-4 text-sm">
                    <div className="font-semibold">Blended attestation</div>
                    <div>signer: {rawResponse.blended.attestation.signer}</div>
                    <div>signature: <code className="break-all">{rawResponse.blended.attestation.signature}</code></div>
                    <div>auditOk: {String(rawResponse.blended.auditOk)}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {loading && (
          <div className="mt-6 p-6 border-4 border-black bg-white">Processing — this may take a few seconds (calling LLM + simulator)...</div>
        )}
      </section>
    </main>
  );
}
