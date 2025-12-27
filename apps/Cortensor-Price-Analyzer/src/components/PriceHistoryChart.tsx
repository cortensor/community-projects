'use client';

import { useId, useMemo } from 'react';
import type { HistoricalCandle } from '@/lib/marketTypes';

export type CandleWithClose = HistoricalCandle & { close: number };

interface PriceHistoryChartProps {
  data: CandleWithClose[];
}

function formatPriceLabel(value: number): string {
  if (!Number.isFinite(value)) return '—';
  if (Math.abs(value) >= 1000) {
    return `$${value.toFixed(0)}`;
  }
  if (Math.abs(value) >= 100) {
    return `$${value.toFixed(1)}`;
  }
  if (Math.abs(value) >= 1) {
    return `$${value.toFixed(2)}`;
  }
  return `$${value.toPrecision(3)}`;
}

function formatDateLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
}

function PriceHistoryChart({ data }: PriceHistoryChartProps) {
  const gradientId = useId();

  const chart = useMemo(() => {
    if (data.length === 0) {
      return null;
    }

    const sorted = [...data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
    const closes = sorted.map((entry) => entry.close);
    const minClose = Math.min(...closes);
    const maxClose = Math.max(...closes);
    const range = maxClose - minClose || Math.max(Math.abs(maxClose), 1);

    const viewWidth = 960;
    const viewHeight = 320;
    const paddingX = 48;
    const paddingY = 36;
    const usableWidth = viewWidth - paddingX * 2;
    const usableHeight = viewHeight - paddingY * 2;

    const points = sorted.map((entry, index) => {
      const t = sorted.length === 1 ? 0 : index / (sorted.length - 1);
      const x = paddingX + usableWidth * t;
      const scaled = range === 0 ? 0.5 : (entry.close - minClose) / range;
      const y = paddingY + usableHeight * (1 - scaled);
      return { ...entry, x, y };
    });

    const linePath = points.reduce((path, point, index) => {
      const command = index === 0 ? 'M' : 'L';
      return `${path}${command}${point.x},${point.y}`;
    }, '');

    const baseY = paddingY + usableHeight;
    const areaPath = `${linePath}L${points[points.length - 1].x},${baseY}L${points[0].x},${baseY}Z`;

    const gridLines = Array.from({ length: 4 }, (_, idx) => (
      paddingY + (usableHeight / 3) * idx
    ));

    return {
      viewWidth,
      viewHeight,
      paddingX,
      paddingY,
      baseY,
      points,
      linePath,
      areaPath,
      gridLines,
      minClose,
      maxClose,
    };
  }, [data]);

  if (!chart) {
    return <div className="flex h-full items-center justify-center text-sm text-slate-500">Insufficient history</div>;
  }

  const { viewWidth, viewHeight, paddingX, paddingY, baseY, points, linePath, areaPath, gridLines, minClose, maxClose } = chart;
  const firstPoint = points[0];
  const lastPoint = points[points.length - 1];

  return (
    <svg viewBox={`0 0 ${viewWidth} ${viewHeight}`} className="h-full w-full" preserveAspectRatio="none">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2563eb" stopOpacity={0.3} />
          <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
        </linearGradient>
      </defs>

      <rect x={0} y={0} width={viewWidth} height={viewHeight} fill="#ffffff" />

      {gridLines.map((y, idx) => (
        <line key={idx} x1={paddingX} x2={viewWidth - paddingX} y1={y} y2={y} stroke="#e2e8f0" strokeDasharray="4 6" strokeWidth={1} />
      ))}

      <path d={areaPath} fill={`url(#${gradientId})`} opacity={1} />
      <path d={linePath} fill="none" stroke="#2563eb" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

      <circle cx={lastPoint.x} cy={lastPoint.y} r={4} fill="#2563eb" stroke="#1d4ed8" strokeWidth={2} />
      <circle cx={firstPoint.x} cy={firstPoint.y} r={3} fill="#2563eb" opacity={0.6} />

      <text x={paddingX} y={paddingY - 10} fill="#334155" fontSize={12} fontWeight={500}>
        {formatPriceLabel(maxClose)}
      </text>
      <text x={paddingX} y={baseY + 18} fill="#64748b" fontSize={12}>
        {formatPriceLabel(minClose)}
      </text>

      <text x={firstPoint.x} y={baseY + 18} fill="#94a3b8" fontSize={12} textAnchor="start">
        {formatDateLabel(firstPoint.date)}
      </text>
      <text x={lastPoint.x} y={baseY + 18} fill="#334155" fontSize={12} textAnchor="end" fontWeight={600}>
        {formatDateLabel(lastPoint.date)}
      </text>
    </svg>
  );
}

export default PriceHistoryChart;
