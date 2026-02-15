import React from "react";

export default function DecisionPanel({ result }: { result: any }) {
  const { envelope, bundle, hash, attestation, auditOk } = result;

  return (
    <div className="mt-6 border rounded p-4 bg-gray-50">
      <h2 className="text-xl font-semibold mb-2">Decision Envelope</h2>
      <pre className="bg-white p-3 rounded overflow-auto max-h-64">{JSON.stringify(envelope, null, 2)}</pre>

      <h3 className="mt-4 font-semibold">Canonical Bundle</h3>
      <pre className="bg-white p-3 rounded overflow-auto max-h-64">{JSON.stringify(bundle, null, 2)}</pre>

      <div className="mt-4">
        <strong>Canonical hash:</strong> <code>{hash}</code>
      </div>

      <div className="mt-2">
        <strong>Attestation signer:</strong> {attestation?.signer}
      </div>

      <div className="mt-2">
        <strong>Audit OK:</strong> {String(auditOk)}
      </div>

      <div className="mt-4">
        <button
          className="bg-green-600 text-white px-3 py-1 rounded"
          onClick={async () => {
            const publicKeyPem = attestation?.publicKeyPem;
            if (!publicKeyPem) return alert("No public key available");
            try {
              const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:4000"}/api/claims/audit/verify`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ bundle, attestation, publicKeyPem }),
              });
              const json = await res.json();
              alert(json.ok ? "Verification OK" : `Verification failed: ${json.error || json.ok}`);
            } catch (err: any) {
              alert(err.message || String(err));
            }
          }}
        >
          Verify Bundle
        </button>
      </div>
    </div>
  );
}
