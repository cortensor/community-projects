/**
 * LandingPage - Clean, calm introduction to Xea
 * Explains what Xea is, why use it, and how it differs from traditional validation
 */

import { useState, useEffect } from 'react';

interface LandingPageProps {
    onStart: () => void;
}

export function LandingPage({ onStart }: LandingPageProps) {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        // Trigger fade-in animation on mount
        const timer = setTimeout(() => setIsVisible(true), 100);
        return () => clearTimeout(timer);
    }, []);

    const differentiators = [
        {
            icon: '📈',
            title: 'Lifecycle-Aware',
            description: 'Tracks how proposals change over time (v1 → v2 → v3), not just single claims',
        },
        {
            icon: '🔗',
            title: 'Claim Graph',
            description: 'Analyzes consistency across multiple claims instead of validating in isolation',
        },
        {
            icon: '🔄',
            title: 'Selective Revalidation',
            description: 'Re-verifies only what changed, preserving prior evidence and trust',
        },
        {
            icon: '📋',
            title: 'Governance-Grade Evidence',
            description: 'Produces replayable, auditable evidence bundles for voters, delegates, and auditors',
        },
    ];

    return (
        <div
            className="min-h-screen flex items-center justify-center px-6 py-12"
            style={{
                background: 'var(--color-bg)',
                transition: 'opacity 0.5s ease-out',
                opacity: isVisible ? 1 : 0,
            }}
        >
            {/* Main Container */}
            <div
                className="w-full max-w-4xl rounded-3xl overflow-hidden"
                style={{
                    background: 'var(--color-bg-elevated)',
                    boxShadow: '0 25px 80px rgba(0, 0, 0, 0.15), 0 8px 32px rgba(0, 0, 0, 0.1)',
                    border: '1px solid var(--color-border)',
                    transform: isVisible ? 'translateY(0)' : 'translateY(20px)',
                    transition: 'transform 0.6s ease-out',
                }}
            >
                {/* Hero Section */}
                <div
                    className="px-10 py-12 text-center"
                    style={{
                        background: 'linear-gradient(135deg, var(--color-accent-soft), transparent)',
                    }}
                >
                    {/* Logo */}
                    <div className="flex justify-center mb-6">
                        <img
                            src="/logo.png"
                            alt="Xea Logo"
                            className="h-20 w-20 rounded-full"
                            style={{
                                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
                                animation: 'float 3s ease-in-out infinite',
                            }}
                        />
                    </div>

                    <h1
                        className="text-4xl font-bold mb-4"
                        style={{ color: 'var(--color-text)' }}
                    >
                        Xea
                    </h1>

                    <p
                        className="text-xl mb-2"
                        style={{ color: 'var(--color-accent)' }}
                    >
                        Verifiable Governance Intelligence
                    </p>

                    <p
                        className="text-base max-w-xl mx-auto leading-relaxed"
                        style={{ color: 'var(--color-text-secondary)' }}
                    >
                        Transform how you evaluate governance proposals.
                        Xea uses decentralized AI inference to verify claims
                        with cryptographic proof — not just opinions.
                    </p>
                </div>

                {/* Differentiators Section */}
                <div className="px-10 py-10">
                    <h2
                        className="text-lg font-semibold mb-6 text-center"
                        style={{ color: 'var(--color-text)' }}
                    >
                        What Makes Xea Different
                    </h2>

                    <div className="grid md:grid-cols-2 gap-5">
                        {differentiators.map((item, idx) => (
                            <div
                                key={idx}
                                className="p-5 rounded-xl flex items-start gap-4"
                                style={{
                                    background: 'var(--color-bg)',
                                    border: '1px solid var(--color-border)',
                                    transition: 'transform 0.2s ease',
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                                onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                            >
                                <span className="text-2xl">{item.icon}</span>
                                <div>
                                    <h3
                                        className="font-semibold mb-1"
                                        style={{ color: 'var(--color-text)' }}
                                    >
                                        {item.title}
                                    </h3>
                                    <p
                                        className="text-sm"
                                        style={{ color: 'var(--color-text-muted)' }}
                                    >
                                        {item.description}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>


                {/* CTA Section */}
                <div
                    className="px-10 py-10 text-center"
                    style={{ borderTop: '1px solid var(--color-border)' }}
                >
                    <button
                        onClick={onStart}
                        className="px-10 py-4 rounded-xl text-lg font-semibold transition-all"
                        style={{
                            background: 'linear-gradient(135deg, var(--color-accent), #8b5cf6)',
                            color: 'white',
                            boxShadow: '0 8px 32px rgba(99, 102, 241, 0.3)',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.transform = 'scale(1.02)';
                            e.currentTarget.style.boxShadow = '0 12px 40px rgba(99, 102, 241, 0.4)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'scale(1)';
                            e.currentTarget.style.boxShadow = '0 8px 32px rgba(99, 102, 241, 0.3)';
                        }}
                    >
                        Start Verifying →
                    </button>

                    <p
                        className="mt-4 text-xs"
                        style={{ color: 'var(--color-text-muted)' }}
                    >
                        Powered by Cortensor Decentralized Network
                    </p>
                </div>
            </div>

            {/* CSS Animation */}
            <style>{`
                @keyframes float {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-8px); }
                }
            `}</style>
        </div>
    );
}

export default LandingPage;
