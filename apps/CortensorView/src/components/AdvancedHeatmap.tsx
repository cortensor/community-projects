import { useState } from 'react';
import type { HeatmapRank } from '../types/cortensor';

interface AdvancedHeatmapProps {
  data: HeatmapRank[];
  rows?: number;
  cols?: number;
}

export default function AdvancedHeatmap({ data, rows = 10, cols = 10 }: AdvancedHeatmapProps) {
  const [hoveredCell, setHoveredCell] = useState<number | null>(null);

  const maxValue = Math.max(...data.map(d => Number(d.value || 0)));
  const minValue = Math.min(...data.map(d => Number(d.value || 0)));

  const getColor = (value: number) => {
    const normalized = (value - minValue) / (maxValue - minValue || 1);
    
    if (normalized > 0.8) return '#10b981'; // Green
    if (normalized > 0.6) return '#34d399';
    if (normalized > 0.4) return '#fbbf24'; // Yellow
    if (normalized > 0.2) return '#fb923c'; // Orange
    return '#ef4444'; // Red
  };

  const gridData = Array.from({ length: rows * cols }, (_, idx) => {
    const item = data[idx] || { value: Math.random() * 100, rank: idx + 1 };
    return {
      index: idx,
      value: Number(item.value || 0),
      rank: item.rank || idx + 1,
      node_id: item.node_id || `node-${idx}`,
    };
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#ef4444' }}></div>
            <span className="text-gray-600">Low</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#fbbf24' }}></div>
            <span className="text-gray-600">Medium</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#10b981' }}></div>
            <span className="text-gray-600">High</span>
          </div>
        </div>
        <div className="text-xs text-gray-500">
          Range: {minValue.toFixed(1)} - {maxValue.toFixed(1)}
        </div>
      </div>

      <div 
        className="grid gap-2"
        style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
      >
        {gridData.map((cell) => (
          <div
            key={cell.index}
            className="aspect-square rounded-lg transition-all duration-200 cursor-pointer relative group"
            style={{ 
              backgroundColor: getColor(cell.value),
              transform: hoveredCell === cell.index ? 'scale(1.1)' : 'scale(1)',
              boxShadow: hoveredCell === cell.index ? '0 4px 12px rgba(0,0,0,0.15)' : 'none',
            }}
            onMouseEnter={() => setHoveredCell(cell.index)}
            onMouseLeave={() => setHoveredCell(null)}
          >
            {hoveredCell === cell.index && (
              <div className="absolute z-10 bottom-full left-1/2 transform -translate-x-1/2 mb-2 bg-gray-900 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap shadow-lg">
                <div className="font-semibold">Rank #{cell.rank}</div>
                <div className="text-gray-300">Value: {cell.value.toFixed(2)}</div>
                <div className="text-gray-400 text-[10px] mt-1">{cell.node_id.slice(0, 12)}...</div>
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                  <div className="border-4 border-transparent border-t-gray-900"></div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
