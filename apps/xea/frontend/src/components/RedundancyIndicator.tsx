/**
 * RedundancyIndicator - Clean miner health status
 */

interface RedundancyIndicatorProps {
    level: 'full' | 'reduced' | 'minimal';
    minersRequested?: number;
    minersResponded?: number;
    confidenceAdjustment?: number;
}

const levelConfig = {
    full: { color: 'var(--color-success)', bg: 'var(--color-success-soft)', icon: '✓', label: 'Full' },
    reduced: { color: 'var(--color-warning)', bg: 'var(--color-warning-soft)', icon: '⚡', label: 'Reduced' },
    minimal: { color: 'var(--color-danger)', bg: 'var(--color-danger-soft)', icon: '!', label: 'Minimal' },
};

export const RedundancyIndicator = ({
    level,
    minersRequested = 5,
    minersResponded = 5,
    confidenceAdjustment = 1.0,
}: RedundancyIndicatorProps) => {
    const config = levelConfig[level];
    const confidencePercent = Math.round(confidenceAdjustment * 100);

    return (
        <div
            className="flex items-center gap-3 px-4 py-2.5 rounded-lg animate-fade-in"
            style={{
                background: config.bg,
                border: `1px solid ${config.color}20`,
            }}
        >
            <span style={{ color: config.color }} className="text-lg font-bold">
                {config.icon}
            </span>

            <div className="flex-1">
                <span style={{ color: config.color }} className="text-sm font-semibold">
                    {config.label} Redundancy
                </span>
                <span className="text-secondary text-sm ml-2">
                    • {minersResponded}/{minersRequested} miners • {confidencePercent}%
                </span>
            </div>

            {/* Simple progress dots */}
            <div className="flex gap-1">
                {[...Array(minersRequested)].map((_, i) => (
                    <div
                        key={i}
                        className="w-2 h-2 rounded-full"
                        style={{
                            background: i < minersResponded ? config.color : 'var(--color-border)',
                        }}
                    />
                ))}
            </div>
        </div>
    );
};

export default RedundancyIndicator;
