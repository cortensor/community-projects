import { PieChart as RechartsPieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface PieChartProps {
  data: Array<{ name: string; value: number }>;
  colors: string[];
  height?: number;
  innerRadius?: number;
}

export default function PieChart({ data, colors, height = 300, innerRadius = 0 }: PieChartProps) {
  // Custom label renderer to prevent overlap
  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    if (percent < 0.05) return null; // Don't show label if slice is too small
    
    const RADIAN = Math.PI / 180;
    // Position label in the middle of the slice
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text 
        x={x} 
        y={y} 
        fill="white" 
        textAnchor="middle" 
        dominantBaseline="central"
        style={{ 
          fontSize: '14px', 
          fontWeight: '600',
          textShadow: '0 1px 2px rgba(0,0,0,0.3)'
        }}
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsPieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={renderCustomLabel}
          outerRadius={height * 0.28}
          innerRadius={innerRadius}
          fill="#8884d8"
          dataKey="value"
          animationDuration={1000}
        >
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Pie>
        <Tooltip 
          contentStyle={{ 
            backgroundColor: '#fff', 
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            fontSize: '12px'
          }}
        />
        <Legend 
          wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
          iconSize={10}
          layout="horizontal"
          verticalAlign="bottom"
          align="center"
        />
      </RechartsPieChart>
    </ResponsiveContainer>
  );
}
