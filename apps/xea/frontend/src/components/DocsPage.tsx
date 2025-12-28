/**
 * DocsPage - Project documentation, tech stack, and differentiation
 */

export function DocsPage() {
    return (
        <div className="space-y-8">
            {/* Hero Section */}
            <section
                className="rounded-2xl p-8 text-center"
                style={{
                    background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1))',
                    border: '1px solid var(--color-border)',
                }}
            >
                <h1
                    className="text-4xl font-bold mb-4"
                    style={{
                        background: 'linear-gradient(135deg, var(--color-accent), #8b5cf6)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                    }}
                >
                    Xea Governance Oracle
                </h1>
                <p className="text-lg max-w-2xl mx-auto" style={{ color: 'var(--color-text-secondary)' }}>
                    Verifiable governance intelligence powered by decentralized inference on the Cortensor network
                </p>
            </section>

            {/* What is Xea */}
            <section className="card">
                <h2 className="text-xl font-bold mb-4 flex items-center gap-2" style={{ color: 'var(--color-text)' }}>
                    <span>🎯</span> What is Xea?
                </h2>
                <p className="mb-4" style={{ color: 'var(--color-text-secondary)' }}>
                    Xea is a decentralized claim verification system that extracts factual claims from governance
                    proposals and validates them using the Cortensor network's distributed AI miners.
                </p>
                <ul className="space-y-2" style={{ color: 'var(--color-text-secondary)' }}>
                    <li className="flex items-start gap-2">
                        <span style={{ color: 'var(--color-success)' }}>✓</span>
                        <span><strong>Claim Extraction:</strong> AI-powered extraction of verifiable claims from text</span>
                    </li>
                    <li className="flex items-start gap-2">
                        <span style={{ color: 'var(--color-success)' }}>✓</span>
                        <span><strong>Decentralized Validation:</strong> Multiple independent miners verify each claim</span>
                    </li>
                    <li className="flex items-start gap-2">
                        <span style={{ color: 'var(--color-success)' }}>✓</span>
                        <span><strong>Evidence Bundles:</strong> Cryptographic proofs of validation with IPFS storage</span>
                    </li>
                </ul>
            </section>

            {/* Tech Stack */}
            <section className="card">
                <h2 className="text-xl font-bold mb-4 flex items-center gap-2" style={{ color: 'var(--color-text)' }}>
                    <span>⚡</span> Tech Stack
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                        { name: 'Python', desc: 'FastAPI Backend', color: '#3776ab' },
                        { name: 'React', desc: 'TypeScript Frontend', color: '#61dafb' },
                        { name: 'Cortensor', desc: 'Decentralized AI', color: '#8b5cf6' },
                        { name: 'Redis', desc: 'Job State Management', color: '#dc382d' },
                        { name: 'Groq', desc: 'Claim Extraction', color: '#f55036' },
                        { name: 'IPFS', desc: 'Evidence Storage', color: '#65c2cb' },
                        { name: 'WebSocket', desc: 'Real-time Updates', color: '#10b981' },
                        { name: 'Pydantic', desc: 'Data Validation', color: '#e92063' },
                    ].map((tech) => (
                        <div
                            key={tech.name}
                            className="p-4 rounded-xl text-center"
                            style={{
                                background: 'var(--color-bg)',
                                border: '1px solid var(--color-border-subtle)',
                            }}
                        >
                            <div
                                className="text-2xl font-bold mb-1"
                                style={{ color: tech.color }}
                            >
                                {tech.name}
                            </div>
                            <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                {tech.desc}
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* How it's Different */}
            <section className="card">
                <h2 className="text-xl font-bold mb-4 flex items-center gap-2" style={{ color: 'var(--color-text)' }}>
                    <span>🔮</span> Why Decentralized Validation?
                </h2>
                <div className="grid md:grid-cols-2 gap-6">
                    <div
                        className="p-5 rounded-xl"
                        style={{
                            background: 'var(--color-danger-soft)',
                            border: '1px solid rgba(239, 68, 68, 0.2)',
                        }}
                    >
                        <h3 className="font-bold mb-2" style={{ color: 'var(--color-danger)' }}>
                            ❌ Traditional Validation
                        </h3>
                        <ul className="space-y-1 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                            <li>• Single point of failure</li>
                            <li>• Centralized trust required</li>
                            <li>• No cryptographic proofs</li>
                            <li>• Opaque decision process</li>
                            <li>• Vulnerable to manipulation</li>
                        </ul>
                    </div>
                    <div
                        className="p-5 rounded-xl"
                        style={{
                            background: 'var(--color-success-soft)',
                            border: '1px solid rgba(16, 185, 129, 0.2)',
                        }}
                    >
                        <h3 className="font-bold mb-2" style={{ color: 'var(--color-success)' }}>
                            ✅ Xea + Cortensor
                        </h3>
                        <ul className="space-y-1 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                            <li>• Distributed miner network</li>
                            <li>• Trustless verification</li>
                            <li>• Proof of Inference (PoI)</li>
                            <li>• Transparent evidence bundles</li>
                            <li>• Consensus-based verdicts</li>
                        </ul>
                    </div>
                </div>
            </section>

            {/* Workflow */}
            <section className="card">
                <h2 className="text-xl font-bold mb-4 flex items-center gap-2" style={{ color: 'var(--color-text)' }}>
                    <span>📊</span> Validation Workflow
                </h2>
                <div className="flex items-center justify-between flex-wrap gap-4">
                    {[
                        { step: '1', label: 'Submit Proposal', icon: '📝' },
                        { step: '2', label: 'Extract Claims', icon: '🔍' },
                        { step: '3', label: 'Send to Miners', icon: '📡' },
                        { step: '4', label: 'Aggregate Results', icon: '🔬' },
                        { step: '5', label: 'Evidence Bundle', icon: '✅' },
                    ].map((item, idx) => (
                        <div key={item.step} className="flex items-center gap-3">
                            <div className="flex flex-col items-center">
                                <div
                                    className="w-12 h-12 rounded-full flex items-center justify-center text-xl"
                                    style={{
                                        background: 'var(--color-accent)',
                                        color: 'white',
                                        boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                                    }}
                                >
                                    {item.icon}
                                </div>
                                <span className="text-xs mt-2 text-center font-medium" style={{ color: 'var(--color-text)' }}>
                                    {item.label}
                                </span>
                            </div>
                            {idx < 4 && (
                                <div
                                    className="w-8 h-0.5"
                                    style={{ background: 'var(--color-border)' }}
                                />
                            )}
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
}

export default DocsPage;
