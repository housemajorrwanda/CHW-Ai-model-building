import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';

interface GraphBuilderProps {
  onInsert: (graphData: any) => void;
}

export function GraphBuilder({ onInsert }: GraphBuilderProps) {
  const [graphType, setGraphType] = useState<'line' | 'bar' | 'pie'>('line');
  const [dataInput, setDataInput] = useState('0,0\n1,2\n2,4\n3,6\n4,8');
  const [xLabel, setXLabel] = useState('X Axis');
  const [yLabel, setYLabel] = useState('Y Axis');
  const [title, setTitle] = useState('Graph');

  const parseData = () => {
    try {
      const lines = dataInput.trim().split('\n');
      return lines.map((line, idx) => {
        const [x, y] = line.split(',').map((v) => parseFloat(v.trim()));
        return { name: x.toString(), value: y, x, y };
      });
    } catch {
      return [];
    }
  };

  const data = parseData();

  const handleInsert = () => {
    const graphData = {
      type: graphType,
      data: data,
      xLabel,
      yLabel,
      title,
      name: title || 'Graph',
    };
    
    onInsert(graphData);
    toast.success('Graph inserted');
  };

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

  return (
    <div className="space-y-4">
      {/* Graph Type Selection */}
      <div>
        <Label className="text-sm">Graph Type</Label>
        <Select value={graphType} onValueChange={(v: any) => setGraphType(v)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="line">Line Chart</SelectItem>
            <SelectItem value="bar">Bar Chart</SelectItem>
            <SelectItem value="pie">Pie Chart</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Labels */}
      <div className="grid grid-cols-3 gap-2">
        <div>
          <Label className="text-xs">Title</Label>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Graph Title"
          />
        </div>
        <div>
          <Label className="text-xs">X Label</Label>
          <Input
            value={xLabel}
            onChange={(e) => setXLabel(e.target.value)}
            placeholder="X Axis"
          />
        </div>
        <div>
          <Label className="text-xs">Y Label</Label>
          <Input
            value={yLabel}
            onChange={(e) => setYLabel(e.target.value)}
            placeholder="Y Axis"
          />
        </div>
      </div>

      {/* Data Input */}
      <div>
        <Label className="text-sm">Data (x,y per line)</Label>
        <textarea
          value={dataInput}
          onChange={(e) => setDataInput(e.target.value)}
          className="w-full h-24 p-2 border rounded-md text-sm font-mono"
          placeholder="0,0&#10;1,2&#10;2,4&#10;3,6"
        />
        <p className="text-xs text-muted-foreground mt-1">
          Format: x,y on each line
        </p>
      </div>

      {/* Preview */}
      <div className="border rounded-lg p-3 bg-white h-48">
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

      {/* Insert Button */}
      <Button onClick={handleInsert} className="w-full" disabled={data.length === 0}>
        Insert Graph
      </Button>
    </div>
  );
}

