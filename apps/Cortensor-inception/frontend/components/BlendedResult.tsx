"use client";

import React, { useEffect, useState } from "react";

type Blended = {
  id: string;
  sources: { path: string }[];
  blended: {
    decision: string;
    agreementState: string;
    rationale: string;
    evidence: any;
    diffs: string[];
  };
  createdAt: number;
};

export default function BlendedResult() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [data, setData] = useState<{ path: string; bundle: Blended } | null>(null);

  async function fetchBlended() {
    setLoading(true);
    setErr(null);
    try {
      const r = await fetch("/api/blended");
      if (!r.ok) throw new Error(await r.text());
      const j = await r.json();
      setData(j);
    } catch (e: any) {
      setErr(e?.message || "unknown error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchBlended();
  }, []);

  if (loading) return <div className="p-6 border-4 border-black">Loading blended result…</div>;
  if (err) return <div className="p-6 border-4 border-black">Error: {err}</div>;
  if (!data) return <div className="p-6 border-4 border-black">No blended result found</div>;

  const b = data.bundle;

  return (
    <div className="p-6 border-4 border-black bg-white">
      <h3 className="font-black">Blended Result</h3>
      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="col-span-1">
          <div className="text-sm text-black/70">Decision</div>
          <div className="mt-2 font-bold text-xl">{b.blended.decision}</div>
        </div>

        <div className="col-span-1">
          <div className="text-sm text-black/70">Agreement</div>
          <div className="mt-2 font-bold">{b.blended.agreementState}</div>
        </div>

        <div className="col-span-1">
          <div className="text-sm text-black/70">Diffs</div>
          <div className="mt-2">{b.blended.diffs.length ? b.blended.diffs.join(", ") : "none"}</div>
        </div>
      </div>

      <div className="mt-4 text-sm text-black/70 whitespace-pre-wrap">{b.blended.rationale}</div>

      <div className="mt-6">
        <div className="text-sm text-black/70">Sources</div>
        <ul className="mt-2 list-disc pl-6 text-sm">
          {b.sources.map((s, i) => (
            <li key={i} className="truncate max-w-2xl">{s.path}</li>
          ))}
        </ul>
      </div>

      <div className="mt-6">
        <details className="bg-gray-50 p-4 border border-black/5">
          <summary className="font-semibold cursor-pointer">Show raw blended JSON</summary>
          <pre className="mt-4 max-h-64 overflow-auto text-xs">{JSON.stringify(b, null, 2)}</pre>
        </details>
      </div>

      <div className="mt-6 flex items-center gap-4">
        <button onClick={fetchBlended} className="px-4 py-2 border border-black font-bold">Refresh</button>
      </div>
    </div>
  );
}
