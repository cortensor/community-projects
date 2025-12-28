import React from 'react';

interface TooltipProps {
    content: string;
    children: React.ReactNode;
}

/**
 * Reusable tooltip component for explaining metrics to judges
 */
export function Tooltip({ content, children }: TooltipProps) {
    return (
        <span className="tooltip">
            {children}
            <span className="tooltip-content">{content}</span>
        </span>
    );
}

// Predefined tooltips for metrics
export function PoITooltip({ children }: { children: React.ReactNode }) {
    return (
        <Tooltip content="PoI = Agreement across independent miners">
            {children}
        </Tooltip>
    );
}

export function PoUWTooltip({ children }: { children: React.ReactNode }) {
    return (
        <Tooltip content="PoUW = Usefulness & correctness score from validators">
            {children}
        </Tooltip>
    );
}

export default Tooltip;
