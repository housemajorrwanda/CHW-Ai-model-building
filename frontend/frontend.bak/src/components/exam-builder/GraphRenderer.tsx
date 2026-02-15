import { useEffect, useRef } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

interface GraphRendererProps {
  graphId: string;
  graphType: string;
  data: any[];
  title: string;
  xLabel: string;
  yLabel: string;
}

export function GraphRenderer({ graphType, data, title, xLabel, yLabel }: GraphRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const renderChart = () => {
      if (data.length === 0) return;

      const chartContainer = containerRef.current?.querySelector('.chart-mount');
      if (!chartContainer) return;

      // This will be handled by React rendering
    };

    renderChart();
  }, [graphType, data, title, xLabel, yLabel]);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground">
        No data available
      </div>
    );
  }

  return (
    <div ref={containerRef} className="graph-renderer w-full">
      {title && <h4 className="text-sm font-semibold mb-2">{title}</h4>}
      <div className="chart-mount" style={{ height: '200px', width: '100%' }}>
        <ResponsiveContainer width="100%" height="100%">
          {graphType === 'line' && (
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" label={{ value: xLabel, position: 'insideBottom', offset: -5 }} />
              <YAxis label={{ value: yLabel, angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} />
            </LineChart>
          )}
          {graphType === 'bar' && (
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#3b82f6" />
            </BarChart>
          )}
          {graphType === 'pie' && (
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={60}
                label
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
      <div className="text-xs text-muted-foreground mt-2">
        X: {xLabel} | Y: {yLabel}
      </div>
    </div>
  );
}

