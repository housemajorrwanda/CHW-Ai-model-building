import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { useState } from 'react';
import { Circle, Square, Triangle, Hexagon, Star } from 'lucide-react';
import { toast } from 'sonner';

interface ShapeInserterProps {
  onInsert: (shapeData: any) => void;
}

const shapes = [
  { name: 'Circle', icon: Circle, type: 'circle' },
  { name: 'Square', icon: Square, type: 'square' },
  { name: 'Rectangle', icon: Square, type: 'rectangle' },
  { name: 'Triangle', icon: Triangle, type: 'triangle' },
  { name: 'Pentagon', icon: Hexagon, type: 'pentagon' },
  { name: 'Hexagon', icon: Hexagon, type: 'hexagon' },
  { name: 'Star', icon: Star, type: 'star' },
];

export function ShapeInserter({ onInsert }: ShapeInserterProps) {
  const [selectedShape, setSelectedShape] = useState('circle');
  const [width, setWidth] = useState('100');
  const [height, setHeight] = useState('100');
  const [color, setColor] = useState('#3b82f6');
  const [strokeWidth, setStrokeWidth] = useState('2');

  const handleInsert = () => {
    const shapeData = {
      type: selectedShape,
      width: parseInt(width) || 100,
      height: parseInt(height) || 100,
      color,
      strokeWidth: parseInt(strokeWidth) || 2,
      name: shapes.find(s => s.type === selectedShape)?.name || 'Shape',
    };
    
    onInsert(shapeData);
    toast.success(`${shapeData.name} inserted`);
  };

  return (
    <div className="space-y-4">
      {/* Shape Selection */}
      <div>
        <Label className="text-sm mb-2 block">Select Shape</Label>
        <div className="grid grid-cols-4 gap-2">
          {shapes.map((shape) => {
            const Icon = shape.icon;
            return (
              <Button
                key={shape.type}
                variant={selectedShape === shape.type ? 'default' : 'outline'}
                size="sm"
                className="flex flex-col h-auto py-3"
                onClick={() => setSelectedShape(shape.type)}
              >
                <Icon className="h-6 w-6 mb-1" />
                <span className="text-xs">{shape.name}</span>
              </Button>
            );
          })}
        </div>
      </div>

      {/* Properties */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-xs">Width</Label>
          <Input
            type="number"
            value={width}
            onChange={(e) => setWidth(e.target.value)}
            placeholder="100"
          />
        </div>
        <div>
          <Label className="text-xs">Height</Label>
          <Input
            type="number"
            value={height}
            onChange={(e) => setHeight(e.target.value)}
            placeholder="100"
          />
        </div>
        <div>
          <Label className="text-xs">Color</Label>
          <div className="flex gap-2">
            <Input
              type="color"
              value={color}
              onChange={(e) => setColor(e.target.value)}
              className="w-12 h-9 p-1"
            />
            <Input
              type="text"
              value={color}
              onChange={(e) => setColor(e.target.value)}
              placeholder="#3b82f6"
              className="flex-1"
            />
          </div>
        </div>
        <div>
          <Label className="text-xs">Stroke Width</Label>
          <Input
            type="number"
            value={strokeWidth}
            onChange={(e) => setStrokeWidth(e.target.value)}
            placeholder="2"
          />
        </div>
      </div>

      {/* Preview */}
      <div className="border rounded-lg p-4 bg-white flex items-center justify-center h-32">
        <svg width={parseInt(width) || 100} height={parseInt(height) || 100} className="max-w-full max-h-full">
          {selectedShape === 'circle' && (
            <circle
              cx={(parseInt(width) || 100) / 2}
              cy={(parseInt(height) || 100) / 2}
              r={Math.min((parseInt(width) || 100), (parseInt(height) || 100)) / 2 - 5}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
            />
          )}
          {selectedShape === 'square' && (
            <rect
              x="5"
              y="5"
              width={(parseInt(width) || 100) - 10}
              height={(parseInt(width) || 100) - 10}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
            />
          )}
          {selectedShape === 'rectangle' && (
            <rect
              x="5"
              y="5"
              width={(parseInt(width) || 100) - 10}
              height={(parseInt(height) || 100) - 10}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
            />
          )}
          {selectedShape === 'triangle' && (
            <polygon
              points={`${(parseInt(width) || 100) / 2},5 ${(parseInt(width) || 100) - 5},${(parseInt(height) || 100) - 5} 5,${(parseInt(height) || 100) - 5}`}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
            />
          )}
        </svg>
      </div>

      {/* Insert Button */}
      <Button onClick={handleInsert} className="w-full">
        Insert Shape
      </Button>
    </div>
  );
}

