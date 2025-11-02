import { RadarChart as RechartsRadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Legend } from 'recharts';

interface RadarChartProps {
  data: Array<Record<string, unknown>>;
  dataKey: string;
  nameKey: string;
  fill: string;
  stroke: string;
  height?: number;
}

export default function RadarChart({ data, dataKey, nameKey, fill, stroke, height = 300 }: RadarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsRadarChart data={data}>
        <PolarGrid stroke="#e5e7eb" />
        <PolarAngleAxis 
          dataKey={nameKey} 
          style={{ fontSize: '12px' }}
        />
        <PolarRadiusAxis 
          angle={90} 
          domain={[0, 100]}
          style={{ fontSize: '10px' }}
        />
        <Radar
          name="Performance"
          dataKey={dataKey}
          stroke={stroke}
          fill={fill}
          fillOpacity={0.6}
          animationDuration={1000}
        />
        <Legend wrapperStyle={{ fontSize: '12px' }} />
      </RechartsRadarChart>
    </ResponsiveContainer>
  );
}
