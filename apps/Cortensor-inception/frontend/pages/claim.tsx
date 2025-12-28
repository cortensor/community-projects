import React, { useState } from "react";
import ClaimForm from "../components/ClaimForm";
import DecisionPanel from "../components/DecisionPanel";

export default function ClaimPage() {
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Submit Claim (Judge UI)</h1>
      <ClaimForm
        onSubmit={async (payload) => {
          setLoading(true);
          setError(null);
          try {
            const path = payload.useLLM ? "/api/claims/llm" : "/api/claims/submit";
            const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:4000"}${path}`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });
            const json = await res.json();
            if (!res.ok) throw new Error(json.error || "server error");
            setResult(json);
          } catch (err: any) {
            setError(err.message || String(err));
          } finally {
            setLoading(false);
          }
        }}
      />

      {loading && <div className="mt-4">Running pipeline…</div>}
      {error && <div className="mt-4 text-red-600">{error}</div>}

      {result && <DecisionPanel result={result} />}
    </div>
  );
}
