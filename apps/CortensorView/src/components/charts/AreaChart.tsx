import { AreaChart as RechartsAreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface AreaChartProps {
  data: Array<Record<string, unknown>>;
  areas: Array<{
    dataKey: string;
    fill: string;
    stroke: string;
    name?: string;
  }>;
  xAxisKey: string;
  height?: number;
}

export default function AreaChart({ data, areas, xAxisKey, height = 300 }: AreaChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsAreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
        <defs>
          {areas.map((area, idx) => (
            <linearGradient key={idx} id={`gradient-${area.dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={area.fill} stopOpacity={0.8}/>
              <stop offset="95%" stopColor={area.fill} stopOpacity={0.1}/>
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis 
          dataKey={xAxisKey} 
          stroke="#6b7280"
          style={{ fontSize: '11px' }}
          tick={{ fill: '#6b7280' }}
          interval="preserveStartEnd"
        />
        <YAxis 
          stroke="#6b7280"
          style={{ fontSize: '11px' }}
          tick={{ fill: '#6b7280' }}
          width={50}
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: '#fff', 
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            fontSize: '12px'
          }}
        />
        {areas.map((area) => (
          <Area
            key={area.dataKey}
            type="monotone"
            dataKey={area.dataKey}
            stroke={area.stroke}
            strokeWidth={2}
            fill={`url(#gradient-${area.dataKey})`}
            name={area.name || area.dataKey}
            animationDuration={1000}
          />
        ))}
      </RechartsAreaChart>
    </ResponsiveContainer>
  );
}
