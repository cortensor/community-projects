/**
 * Navigation - Header with Home, Docs, History tabs
 */

interface NavigationProps {
    activeTab: 'home' | 'docs' | 'history';
    onTabChange: (tab: 'home' | 'docs' | 'history') => void;
}

export function Navigation({ activeTab, onTabChange }: NavigationProps) {
    const tabs = [
        { id: 'home' as const, label: 'Home', icon: '🏠' },
        { id: 'docs' as const, label: 'Docs', icon: '📚' },
        { id: 'history' as const, label: 'History', icon: '📋' },
    ];

    return (
        <nav
            className="sticky top-0 z-50 backdrop-blur-md"
            style={{
                background: 'var(--color-bg)',
                borderBottom: '1px solid var(--color-border)',
                opacity: 0.98
            }}
        >
            <div className="max-w-7xl mx-auto px-6 py-4">
                <div className="flex items-center justify-between">
                    {/* Logo & Brand */}
                    <div className="flex items-center gap-4">
                        <img
                            src="/logo.png"
                            alt="Xea Logo"
                            className="h-11 w-11 rounded-full"
                            style={{ objectFit: 'cover' }}
                        />
                        <div>
                            <h1 className="text-xl font-bold tracking-tight" style={{ color: 'var(--color-text)' }}>
                                Xea
                            </h1>
                            <p className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                                Verifiable Governance Intelligence
                            </p>
                        </div>
                    </div>

                    {/* Tabs */}
                    <div
                        className="flex items-center gap-1 p-1 rounded-xl border"
                        style={{
                            background: 'var(--color-bg-secondary)',
                            borderColor: 'var(--color-border)'
                        }}
                    >
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => onTabChange(tab.id)}
                                className={`
                                    px-4 py-2 rounded-lg text-sm font-medium
                                    transition-all duration-200
                                    flex items-center gap-2
                                `}
                                style={{
                                    background: activeTab === tab.id
                                        ? 'var(--color-accent)'
                                        : 'transparent',
                                    color: activeTab === tab.id
                                        ? 'white'
                                        : 'var(--color-text-secondary)',
                                    boxShadow: activeTab === tab.id
                                        ? '0 2px 8px rgba(99, 102, 241, 0.3)'
                                        : 'none',
                                }}
                            >
                                <span>{tab.icon}</span>
                                <span>{tab.label}</span>
                            </button>
                        ))}
                    </div>

                    {/* Right side actions */}
                    <div className="flex items-center gap-3">
                        {/* Network Status */}
                        <div
                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium"
                            style={{
                                background: 'var(--color-success-soft)',
                                color: 'var(--color-success)',
                            }}
                        >
                            <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
                            <span>Cortensor Testnet0</span>
                        </div>
                    </div>
                </div>
            </div>
        </nav>
    );
}

export default Navigation;
