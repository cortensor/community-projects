/**
 * VerificationPanel - Clean verification display
 */

import { useState } from 'react';

interface VerificationPanelProps {
    computationHash?: string;
    replayVersion?: string;
    cliCommand?: string;
}

export const VerificationPanel = ({
    computationHash,
    replayVersion = '1.0',
    cliCommand = 'python -m backend.cli verify evidence.json',
}: VerificationPanelProps) => {
    const [copied, setCopied] = useState<'hash' | 'cli' | null>(null);

    const copyToClipboard = async (text: string, type: 'hash' | 'cli') => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(type);
            setTimeout(() => setCopied(null), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    if (!computationHash) return null;

    const shortHash = computationHash.length > 24
        ? `${computationHash.slice(0, 16)}...${computationHash.slice(-8)}`
        : computationHash;

    return (
        <div
            className="rounded-lg overflow-hidden"
            style={{
                background: 'var(--color-bg-secondary)',
                border: '1px solid var(--color-border)',
            }}
        >
            {/* Header */}
            <div
                className="flex items-center gap-3 px-4 py-3"
                style={{ borderBottom: '1px solid var(--color-border-subtle)' }}
            >
                <span className="text-lg">🔐</span>
                <div className="flex-1">
                    <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                        Verification
                    </span>
                    <span className="text-xs ml-2" style={{ color: 'var(--color-text-muted)' }}>
                        v{replayVersion}
                    </span>
                </div>
                <span
                    className="px-2 py-0.5 rounded text-xs font-medium"
                    style={{
                        background: 'var(--color-success-soft)',
                        color: 'var(--color-success)',
                    }}
                >
                    ✓ Verified
                </span>
            </div>

            {/* Hash */}
            <div className="px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                    <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        Computation Hash
                    </span>
                    <button
                        onClick={() => copyToClipboard(computationHash, 'hash')}
                        className="text-xs px-2 py-1 rounded transition-colors"
                        style={{
                            background: copied === 'hash' ? 'var(--color-success-soft)' : 'var(--color-bg)',
                            color: copied === 'hash' ? 'var(--color-success)' : 'var(--color-text-secondary)',
                        }}
                    >
                        {copied === 'hash' ? '✓ Copied' : 'Copy'}
                    </button>
                </div>
                <code
                    className="text-sm font-mono"
                    style={{ color: 'var(--color-accent)' }}
                >
                    {shortHash}
                </code>
            </div>

            {/* CLI */}
            <div
                className="px-4 py-3"
                style={{
                    background: 'var(--color-bg)',
                    borderTop: '1px solid var(--color-border-subtle)',
                }}
            >
                <div className="flex items-center justify-between mb-1">
                    <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        Verify Offline
                    </span>
                    <button
                        onClick={() => copyToClipboard(cliCommand, 'cli')}
                        className="text-xs px-2 py-1 rounded transition-colors"
                        style={{
                            background: copied === 'cli' ? 'var(--color-success-soft)' : 'transparent',
                            color: copied === 'cli' ? 'var(--color-success)' : 'var(--color-text-secondary)',
                        }}
                    >
                        {copied === 'cli' ? '✓' : '📋'}
                    </button>
                </div>
                <code
                    className="text-sm font-mono"
                    style={{ color: 'var(--color-success)' }}
                >
                    $ {cliCommand}
                </code>
            </div>
        </div>
    );
};

export default VerificationPanel;
