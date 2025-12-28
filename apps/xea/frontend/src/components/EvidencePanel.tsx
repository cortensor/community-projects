import React, { useState } from 'react';
import { api, EvidenceBundle, AttestResponse } from '../api';

interface EvidencePanelProps {
    jobId: string;
    bundle: EvidenceBundle;
    ipfsCid?: string;
}

export function EvidencePanel({ jobId, bundle, ipfsCid: initialCid }: EvidencePanelProps) {
    const [showJson, setShowJson] = useState(false);
    const [attestation, setAttestation] = useState<AttestResponse | null>(null);
    const [attesting, setAttesting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [ipfsCid, setIpfsCid] = useState(initialCid);

    const handleAttest = async () => {
        setAttesting(true);
        setError(null);
        try {
            const response = await api.attest({ job_id: jobId, publish: true });
            setAttestation(response);
            setIpfsCid(response.ipfs_cid);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Attestation failed');
        } finally {
            setAttesting(false);
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
    };

    return (
        <div className="space-y-4">
            {/* Action Buttons - Compact */}
            <div className="flex gap-2">
                <button
                    onClick={() => setShowJson(!showJson)}
                    className="flex-1 px-3 py-2 text-xs font-medium rounded-lg transition-colors"
                    style={{
                        background: 'var(--color-bg)',
                        color: 'var(--color-text-secondary)',
                        border: '1px solid var(--color-border)',
                    }}
                >
                    {showJson ? 'Hide JSON' : 'View JSON'}
                </button>
                <button
                    onClick={handleAttest}
                    disabled={attesting || !!attestation}
                    className="flex-1 px-3 py-2 text-xs font-medium rounded-lg transition-colors"
                    style={{
                        background: attestation ? 'var(--color-success)' : 'var(--color-accent)',
                        color: 'white',
                        opacity: attesting ? 0.7 : 1,
                    }}
                >
                    {attesting ? '...' : attestation ? '✓ Attested' : 'Attest'}
                </button>
            </div>

            {error && (
                <div
                    className="p-2 rounded text-xs"
                    style={{
                        background: 'var(--color-danger-soft)',
                        color: 'var(--color-danger)',
                    }}
                >
                    {error}
                </div>
            )}

            {/* IPFS CID */}
            {ipfsCid && (
                <div
                    className="p-3 rounded-lg"
                    style={{
                        background: 'var(--color-bg)',
                        border: '1px solid var(--color-border)',
                    }}
                >
                    <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                            IPFS CID
                        </span>
                        <button
                            onClick={() => copyToClipboard(ipfsCid)}
                            className="text-xs"
                            style={{ color: 'var(--color-accent)' }}
                        >
                            Copy
                        </button>
                    </div>
                    <code
                        className="text-xs font-mono block break-all"
                        style={{ color: 'var(--color-accent)' }}
                    >
                        {ipfsCid}
                    </code>
                </div>
            )}

            {/* JSON Viewer (Collapsible) */}
            {showJson && (
                <div
                    className="rounded-lg overflow-hidden"
                    style={{ border: '1px solid var(--color-border)' }}
                >
                    <div
                        className="flex items-center justify-between px-3 py-2"
                        style={{ background: 'var(--color-bg)' }}
                    >
                        <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                            Evidence Bundle
                        </span>
                        <button
                            onClick={() => copyToClipboard(JSON.stringify(bundle, null, 2))}
                            className="text-xs"
                            style={{ color: 'var(--color-accent)' }}
                        >
                            Copy All
                        </button>
                    </div>
                    <pre
                        className="p-3 text-xs font-mono overflow-auto max-h-48"
                        style={{
                            background: 'var(--color-bg-secondary)',
                            color: 'var(--color-text-muted)',
                        }}
                    >
                        {JSON.stringify(bundle, null, 2)}
                    </pre>
                </div>
            )}

            {/* Attestation Details */}
            {attestation && (
                <div
                    className="p-3 rounded-lg space-y-2"
                    style={{
                        background: 'var(--color-success-soft)',
                        border: '1px solid rgba(16, 185, 129, 0.2)',
                    }}
                >
                    <div className="flex items-center gap-2">
                        <span className="text-sm">✓</span>
                        <span className="text-xs font-medium" style={{ color: 'var(--color-success)' }}>
                            Attestation Complete
                        </span>
                    </div>
                    <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        <div>Signer: <code className="font-mono">{attestation.signer}</code></div>
                        <div className="mt-1">
                            Signature: <code className="font-mono">{attestation.signature.slice(0, 12)}...</code>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default EvidencePanel;
