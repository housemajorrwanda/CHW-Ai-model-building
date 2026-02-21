import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { useState, useRef } from 'react';
import { Circle, Square, Triangle, Hexagon, Star, Plus, X } from 'lucide-react';
import { toast } from 'sonner';
import { Separator } from '@/components/ui/separator';

interface ShapeInserterProps {
  onInsert: (shapeData: any) => void;
}

interface DimensionLabel {
  id: string;
  position: 'top' | 'bottom' | 'left' | 'right' | 'center';
  label: string;
  offset?: number;
  length?: number; // Percentage of shape dimension (0-100+)
  inside?: boolean; // Whether line is inside or outside the shape
  startOffset?: number; // Offset from start (for partial lines)
  endOffset?: number; // Offset from end (for partial lines)
  textXOffset?: number; // Manual X offset for text position
  textYOffset?: number; // Manual Y offset for text position
}

interface AngleMarker {
  id: string;
  vertex: string; // 'top-left', 'top-right', 'bottom-left', 'bottom-right', etc.
  type: 'right-angle' | 'arc';
  label?: string;
  size?: number; // Size of the marker (default: 12 for right-angle, 15 for arc)
  rotation?: number; // Rotation angle in degrees (0-360)
  startAngle?: number; // Start angle for arc (0-360)
  endAngle?: number; // End angle for arc (0-360)
  offsetX?: number; // Manual X offset from vertex
  offsetY?: number; // Manual Y offset from vertex
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
  const [selectedShape, setSelectedShape] = useState('rectangle');
  const [width, setWidth] = useState('200');
  const [height, setHeight] = useState('150');
  const [color, setColor] = useState('#60a5fa');
  const [strokeWidth, setStrokeWidth] = useState('2');
  const [fillColor, setFillColor] = useState('#dbeafe');
  const [dimensions, setDimensions] = useState<DimensionLabel[]>([]);
  const [angleMarkers, setAngleMarkers] = useState<AngleMarker[]>([]);
  const [radiusLabel, setRadiusLabel] = useState('');
  const [draggingTextId, setDraggingTextId] = useState<string | null>(null);
  const [draggingMarkerId, setDraggingMarkerId] = useState<string | null>(null);
  const [rotatingMarkerId, setRotatingMarkerId] = useState<string | null>(null);
  const [draggingRadiusLabel, setDraggingRadiusLabel] = useState(false);
  const [radiusLabelOffsetX, setRadiusLabelOffsetX] = useState(0);
  const [radiusLabelOffsetY, setRadiusLabelOffsetY] = useState(0);
  const svgRef = useRef<SVGSVGElement>(null);

  const addDimension = () => {
    const newDim: DimensionLabel = {
      id: crypto.randomUUID(),
      position: 'top',
      label: '',
      offset: 0,
      length: 100, // Full length by default
      inside: false,
      startOffset: 0,
      endOffset: 0,
    };
    setDimensions([...dimensions, newDim]);
  };

  const removeDimension = (id: string) => {
    setDimensions(dimensions.filter(d => d.id !== id));
  };

  const updateDimension = (id: string, updates: Partial<DimensionLabel>) => {
    setDimensions(dimensions.map(d => d.id === id ? { ...d, ...updates } : d));
  };

  const addAngleMarker = () => {
    const newMarker: AngleMarker = {
      id: crypto.randomUUID(),
      vertex: 'bottom-left',
      type: 'right-angle',
      size: 12, // Default size
      rotation: 0,
      startAngle: 0,
      endAngle: 90,
      offsetX: 0,
      offsetY: 0,
    };
    setAngleMarkers([...angleMarkers, newMarker]);
  };

  const removeAngleMarker = (id: string) => {
    setAngleMarkers(angleMarkers.filter(a => a.id !== id));
  };

  const updateAngleMarker = (id: string, updates: Partial<AngleMarker>) => {
    setAngleMarkers(angleMarkers.map(a => a.id === id ? { ...a, ...updates } : a));
  };

  const handleInsert = () => {
    const shapeData = {
      type: selectedShape,
      width: parseInt(width) || 200,
      height: parseInt(height) || 150,
      color,
      fillColor,
      strokeWidth: parseInt(strokeWidth) || 2,
      dimensions,
      angleMarkers,
      radiusLabel: selectedShape === 'circle' ? radiusLabel : undefined,
      radiusLabelOffsetX: selectedShape === 'circle' ? radiusLabelOffsetX : undefined,
      radiusLabelOffsetY: selectedShape === 'circle' ? radiusLabelOffsetY : undefined,
      name: shapes.find(s => s.type === selectedShape)?.name || 'Shape',
    };
    
    onInsert(shapeData);
    toast.success(`${shapeData.name} inserted`);
  };

  return (
    <div className="flex flex-col h-full max-h-full">
      <div className="space-y-4 overflow-y-auto flex-1 min-h-0 pr-2">
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
            className="h-9"
          />
        </div>
        <div>
          <Label className="text-xs">Height</Label>
          <Input
            type="number"
            value={height}
            onChange={(e) => setHeight(e.target.value)}
            placeholder="100"
            className="h-9"
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
              className="flex-1 h-9"
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
            className="h-9"
          />
        </div>
        <div>
          <Label className="text-xs">Fill Color</Label>
          <div className="flex gap-2">
            <Input
              type="color"
              value={fillColor}
              onChange={(e) => setFillColor(e.target.value)}
              className="w-12 h-9 p-1"
            />
            <Input
              type="text"
              value={fillColor}
              onChange={(e) => setFillColor(e.target.value)}
              placeholder="#dbeafe"
              className="flex-1 h-9"
            />
          </div>
        </div>
      </div>

      {/* Radius Label (for circles) */}
      {selectedShape === 'circle' && (
        <div>
          <Label className="text-xs">Radius Label</Label>
          <Input
            type="text"
            value={radiusLabel}
            onChange={(e) => setRadiusLabel(e.target.value)}
            placeholder='e.g., "r" or "5 cm"'
            className="h-9"
          />
          <p className="text-xs text-muted-foreground mt-1">Label shown next to the radius line</p>
        </div>
      )}

      <Separator />

      {/* Dimension Labels */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <Label className="text-sm">Dimension Labels</Label>
          <Button type="button" variant="outline" size="sm" onClick={addDimension}>
            <Plus className="h-3 w-3 mr-1" />
            Add
          </Button>
        </div>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {dimensions.map((dim) => (
            <div key={dim.id} className="p-2 border rounded space-y-2">
              <div className="flex gap-2 items-center">
                <select
                  value={dim.position}
                  onChange={(e) => updateDimension(dim.id, { position: e.target.value as any })}
                  className="text-xs border rounded px-2 py-1 h-8 flex-1"
                >
                  <option value="top">Top</option>
                  <option value="bottom">Bottom</option>
                  <option value="left">Left</option>
                  <option value="right">Right</option>
                  <option value="center">Center</option>
                </select>
                <Input
                  type="text"
                  value={dim.label}
                  onChange={(e) => updateDimension(dim.id, { label: e.target.value })}
                  placeholder="12 cm"
                  className="flex-1 h-8 text-xs"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeDimension(dim.id)}
                  className="h-8 w-8 p-0"
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={dim.inside || false}
                    onChange={(e) => updateDimension(dim.id, { inside: e.target.checked })}
                    className="h-3 w-3"
                  />
                  <Label className="text-xs">Inside shape</Label>
                </div>
                <div>
                  <Label className="text-xs">Length: </Label>
                  <Input
                    type="number"
                    value={dim.length || 100}
                    onChange={(e) => updateDimension(dim.id, { length: parseInt(e.target.value) || 100 })}
                    min="10"
                    max="200"
                    className="h-7 text-xs inline-block w-16"
                  />
                  <span className="text-xs ml-1">%</span>
                </div>
                {(dim.position === 'top' || dim.position === 'bottom') && (
                  <>
                    <div>
                      <Label className="text-xs">Start offset: </Label>
                      <Input
                        type="number"
                        value={dim.startOffset || 0}
                        onChange={(e) => updateDimension(dim.id, { startOffset: parseInt(e.target.value) || 0 })}
                        className="h-7 text-xs inline-block w-16"
                      />
                    </div>
                    <div>
                      <Label className="text-xs">End offset: </Label>
                      <Input
                        type="number"
                        value={dim.endOffset || 0}
                        onChange={(e) => updateDimension(dim.id, { endOffset: parseInt(e.target.value) || 0 })}
                        className="h-7 text-xs inline-block w-16"
                      />
                    </div>
                  </>
                )}
                {(dim.position === 'left' || dim.position === 'right') && (
                  <>
                    <div>
                      <Label className="text-xs">Top offset: </Label>
                      <Input
                        type="number"
                        value={dim.startOffset || 0}
                        onChange={(e) => updateDimension(dim.id, { startOffset: parseInt(e.target.value) || 0 })}
                        className="h-7 text-xs inline-block w-16"
                      />
                    </div>
                    <div>
                      <Label className="text-xs">Bottom offset: </Label>
                      <Input
                        type="number"
                        value={dim.endOffset || 0}
                        onChange={(e) => updateDimension(dim.id, { endOffset: parseInt(e.target.value) || 0 })}
                        className="h-7 text-xs inline-block w-16"
                      />
                    </div>
                  </>
                )}
                <div>
                  <Label className="text-xs">Distance: </Label>
                  <Input
                    type="number"
                    value={dim.offset || 0}
                    onChange={(e) => updateDimension(dim.id, { offset: parseInt(e.target.value) || 0 })}
                    className="h-7 text-xs inline-block w-16"
                  />
                  <span className="text-xs ml-1">px</span>
                </div>
              </div>
            </div>
          ))}
          {dimensions.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-2">No dimensions added</p>
          )}
        </div>
      </div>

      {/* Angle Markers (for triangles and polygons) */}
      {(selectedShape === 'triangle' || selectedShape === 'rectangle' || selectedShape === 'square') && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label className="text-sm">Angle Markers</Label>
            <Button type="button" variant="outline" size="sm" onClick={addAngleMarker}>
              <Plus className="h-3 w-3 mr-1" />
              Add
            </Button>
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {angleMarkers.map((marker) => (
              <div key={marker.id} className="p-2 border rounded space-y-2">
                <div className="flex gap-2 items-center">
                  <select
                    value={marker.vertex}
                    onChange={(e) => updateAngleMarker(marker.id, { vertex: e.target.value })}
                    className="text-xs border rounded px-2 py-1 h-8 flex-1"
                  >
                    <option value="top-left">Top-Left</option>
                    <option value="top-right">Top-Right</option>
                    <option value="bottom-left">Bottom-Left</option>
                    <option value="bottom-right">Bottom-Right</option>
                  </select>
                  <select
                    value={marker.type}
                    onChange={(e) => {
                      const newType = e.target.value as 'right-angle' | 'arc';
                      updateAngleMarker(marker.id, { 
                        type: newType,
                        size: marker.size || (newType === 'right-angle' ? 12 : 15)
                      });
                    }}
                    className="text-xs border rounded px-2 py-1 h-8 flex-1"
                  >
                    <option value="right-angle">Right Angle (□)</option>
                    <option value="arc">Arc</option>
                  </select>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeAngleMarker(marker.id)}
                    className="h-8 w-8 p-0"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Size: </Label>
                    <Input
                      type="number"
                      value={marker.size || (marker.type === 'right-angle' ? 12 : 15)}
                      onChange={(e) => updateAngleMarker(marker.id, { size: parseInt(e.target.value) || 12 })}
                      min="5"
                      max="200"
                      className="h-7 text-xs inline-block w-16"
                    />
                    <span className="text-xs ml-1">px</span>
                  </div>
                  <div>
                    <Label className="text-xs">Label: </Label>
                    <Input
                      type="text"
                      value={marker.label || ''}
                      onChange={(e) => updateAngleMarker(marker.id, { label: e.target.value })}
                      placeholder="Optional"
                      className="flex-1 h-7 text-xs"
                    />
                  </div>
                </div>
                {marker.type === 'arc' && (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <Label className="text-xs">Start Angle: </Label>
                      <Input
                        type="number"
                        value={marker.startAngle || 0}
                        onChange={(e) => updateAngleMarker(marker.id, { startAngle: parseInt(e.target.value) || 0 })}
                        min="0"
                        max="360"
                        className="h-7 text-xs inline-block w-16"
                      />
                      <span className="text-xs ml-1">°</span>
                    </div>
                    <div>
                      <Label className="text-xs">End Angle: </Label>
                      <Input
                        type="number"
                        value={marker.endAngle || 90}
                        onChange={(e) => updateAngleMarker(marker.id, { endAngle: parseInt(e.target.value) || 90 })}
                        min="0"
                        max="360"
                        className="h-7 text-xs inline-block w-16"
                      />
                      <span className="text-xs ml-1">°</span>
                    </div>
                    <div className="col-span-2 text-xs text-muted-foreground">
                      💡 Drag the arc line to move it, drag the black dot to rotate
                    </div>
                  </div>
                )}
              </div>
            ))}
            {angleMarkers.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-2">No angle markers</p>
            )}
          </div>
        </div>
      )}

      {/* Preview */}
      <div className="border rounded-lg p-4 bg-white flex items-center justify-center min-h-[200px] overflow-auto flex-1">
        <div
          onMouseMove={(e) => {
            if (draggingTextId && svgRef.current) {
              const dim = dimensions.find(d => d.id === draggingTextId);
              if (dim) {
                const rect = svgRef.current.getBoundingClientRect();
                const svgX = e.clientX - rect.left;
                const svgY = e.clientY - rect.top;
                
                const w = parseInt(width) || 200;
                const h = parseInt(height) || 150;
                const padding = 40;
                const shapeX = padding;
                const shapeY = padding;
                
                let baseTextX = 0, baseTextY = 0;
                const isInside = dim.inside || false;
                const offset = isInside ? (dim.offset || 0) : ((dim.offset || 0) + 15);
                const lengthPercent = (dim.length || 100) / 100;
                const startOffset = dim.startOffset || 0;
                
                switch (dim.position) {
                  case 'top':
                    baseTextX = shapeX + startOffset + (w * lengthPercent) / 2;
                    baseTextY = isInside ? shapeY + offset - 5 : shapeY - offset - 5;
                    break;
                  case 'bottom':
                    baseTextX = shapeX + startOffset + (w * lengthPercent) / 2;
                    baseTextY = isInside ? shapeY + h - offset + 15 : shapeY + h + offset + 15;
                    break;
                  case 'left':
                    baseTextX = isInside ? shapeX + offset - 5 : shapeX - offset - 5;
                    baseTextY = shapeY + startOffset + (h * lengthPercent) / 2;
                    break;
                  case 'right':
                    baseTextX = isInside ? shapeX + w - offset + 15 : shapeX + w + offset + 15;
                    baseTextY = shapeY + startOffset + (h * lengthPercent) / 2;
                    break;
                  case 'center':
                    baseTextX = shapeX + w / 2;
                    baseTextY = shapeY + h / 2;
                    break;
                }
                
                const newXOffset = svgX - baseTextX;
                const newYOffset = svgY - baseTextY;
                
                updateDimension(draggingTextId, {
                  textXOffset: newXOffset,
                  textYOffset: newYOffset,
                });
              }
            }
            
            if (draggingMarkerId && svgRef.current) {
              const marker = angleMarkers.find(m => m.id === draggingMarkerId);
              if (marker) {
                const rect = svgRef.current.getBoundingClientRect();
                const svgX = e.clientX - rect.left;
                const svgY = e.clientY - rect.top;
                
                const w = parseInt(width) || 200;
                const h = parseInt(height) || 150;
                const padding = 40;
                const shapeX = padding;
                const shapeY = padding;
                
                let vertexX = 0, vertexY = 0;
                switch (marker.vertex) {
                  case 'top-left':
                    vertexX = shapeX;
                    vertexY = shapeY;
                    break;
                  case 'top-right':
                    vertexX = shapeX + w;
                    vertexY = shapeY;
                    break;
                  case 'bottom-left':
                    vertexX = shapeX;
                    vertexY = shapeY + h;
                    break;
                  case 'bottom-right':
                    vertexX = shapeX + w;
                    vertexY = shapeY + h;
                    break;
                }
                
                const newOffsetX = svgX - vertexX;
                const newOffsetY = svgY - vertexY;
                
                updateAngleMarker(draggingMarkerId, {
                  offsetX: newOffsetX,
                  offsetY: newOffsetY,
                });
              }
            }
            
            if (rotatingMarkerId && svgRef.current) {
              const marker = angleMarkers.find(m => m.id === rotatingMarkerId);
              if (marker && marker.type === 'arc') {
                const rect = svgRef.current.getBoundingClientRect();
                const svgX = e.clientX - rect.left;
                const svgY = e.clientY - rect.top;
                
                const w = parseInt(width) || 200;
                const h = parseInt(height) || 150;
                const padding = 40;
                const shapeX = padding;
                const shapeY = padding;
                
                let vertexX = 0, vertexY = 0;
                switch (marker.vertex) {
                  case 'top-left':
                    vertexX = shapeX;
                    vertexY = shapeY;
                    break;
                  case 'top-right':
                    vertexX = shapeX + w;
                    vertexY = shapeY;
                    break;
                  case 'bottom-left':
                    vertexX = shapeX;
                    vertexY = shapeY + h;
                    break;
                  case 'bottom-right':
                    vertexX = shapeX + w;
                    vertexY = shapeY + h;
                    break;
                }
                
                const centerX = vertexX + (marker.offsetX || 0);
                const centerY = vertexY + (marker.offsetY || 0);
                
                const dx = svgX - centerX;
                const dy = svgY - centerY;
                const angle = Math.atan2(dy, dx) * 180 / Math.PI;
                
                const startAngle = marker.startAngle || 0;
                const newRotation = angle - startAngle;
                
                updateAngleMarker(rotatingMarkerId, {
                  rotation: newRotation,
                });
              }
            }
            
            if (draggingRadiusLabel && svgRef.current) {
              const rect = svgRef.current.getBoundingClientRect();
              const svgX = e.clientX - rect.left;
              const svgY = e.clientY - rect.top;
              
              const w = parseInt(width) || 200;
              const h = parseInt(height) || 150;
              const padding = 40;
              const shapeX = padding;
              const shapeY = padding;
              
              const baseX = shapeX + w / 2;
              const baseY = shapeY + h / 2 - Math.min(w, h) / 2 - 10;
              
              const newOffsetX = svgX - baseX;
              const newOffsetY = svgY - baseY;
              
              setRadiusLabelOffsetX(newOffsetX);
              setRadiusLabelOffsetY(newOffsetY);
            }
          }}
          onMouseUp={() => {
            setDraggingTextId(null);
            setDraggingMarkerId(null);
            setRotatingMarkerId(null);
            setDraggingRadiusLabel(false);
          }}
          onMouseLeave={() => {
            setDraggingTextId(null);
            setDraggingMarkerId(null);
            setRotatingMarkerId(null);
            setDraggingRadiusLabel(false);
          }}
        >
          {renderPreviewSVG()}
        </div>
      </div>

      </div>
      
      {/* Insert Button - Fixed at bottom */}
      <div className="flex-shrink-0 pt-4 border-t mt-4">
        <Button onClick={handleInsert} className="w-full">
          Insert Shape
        </Button>
      </div>
    </div>
  );

  function renderPreviewSVG() {
    const w = parseInt(width) || 200;
    const h = parseInt(height) || 150;
    const padding = 40;
    const svgWidth = w + padding * 2;
    const svgHeight = h + padding * 2;
    const shapeX = padding;
    const shapeY = padding;

    const renderDimensionLine = (dim: DimensionLabel) => {
      const isInside = dim.inside || false;
      const offset = isInside ? (dim.offset || 0) : ((dim.offset || 0) + 15);
      const lengthPercent = (dim.length || 100) / 100;
      const startOffset = dim.startOffset || 0;
      const endOffset = dim.endOffset || 0;
      
      let x1 = 0, y1 = 0, x2 = 0, y2 = 0, textX = 0, textY = 0;
      let lineLength = 0;

      switch (dim.position) {
        case 'top':
          lineLength = w * lengthPercent;
          x1 = shapeX + startOffset;
          y1 = isInside ? shapeY + offset : shapeY - offset;
          x2 = shapeX + startOffset + lineLength - endOffset;
          y2 = isInside ? shapeY + offset : shapeY - offset;
          textX = shapeX + startOffset + lineLength / 2;
          textY = isInside ? shapeY + offset - 5 : shapeY - offset - 5;
          break;
        case 'bottom':
          lineLength = w * lengthPercent;
          x1 = shapeX + startOffset;
          y1 = isInside ? shapeY + h - offset : shapeY + h + offset;
          x2 = shapeX + startOffset + lineLength - endOffset;
          y2 = isInside ? shapeY + h - offset : shapeY + h + offset;
          textX = shapeX + startOffset + lineLength / 2;
          textY = isInside ? shapeY + h - offset + 15 : shapeY + h + offset + 15;
          break;
        case 'left':
          lineLength = h * lengthPercent;
          x1 = isInside ? shapeX + offset : shapeX - offset;
          y1 = shapeY + startOffset;
          x2 = isInside ? shapeX + offset : shapeX - offset;
          y2 = shapeY + startOffset + lineLength - endOffset;
          textX = isInside ? shapeX + offset - 5 : shapeX - offset - 5;
          textY = shapeY + startOffset + lineLength / 2;
          break;
        case 'right':
          lineLength = h * lengthPercent;
          x1 = isInside ? shapeX + w - offset : shapeX + w + offset;
          y1 = shapeY + startOffset;
          x2 = isInside ? shapeX + w - offset : shapeX + w + offset;
          y2 = shapeY + startOffset + lineLength - endOffset;
          textX = isInside ? shapeX + w - offset + 15 : shapeX + w + offset + 15;
          textY = shapeY + startOffset + lineLength / 2;
          break;
        case 'center':
          textX = shapeX + w / 2;
          textY = shapeY + h / 2;
          break;
      }

      if (dim.position === 'center') {
        return (
          <text
            key={dim.id}
            x={textX}
            y={textY}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="12"
            fill="#000"
          >
            {dim.label}
          </text>
        );
      }

      const arrowDir = isInside ? -1 : 1;
      
      // Apply manual text offsets if provided
      const finalTextX = textX + (dim.textXOffset || 0);
      const finalTextY = textY + (dim.textYOffset || 0);

      const handleTextMouseDown = (e: React.MouseEvent) => {
        e.stopPropagation();
        e.preventDefault();
        setDraggingTextId(dim.id);
      };

      return (
        <g key={dim.id}>
          <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#000" strokeWidth="1" />
          {dim.position === 'top' || dim.position === 'bottom' ? (
            <>
              <line x1={x1} y1={y1} x2={x1} y2={y1 + (dim.position === 'top' ? (5 * arrowDir) : (-5 * arrowDir))} stroke="#000" strokeWidth="1" />
              <line x1={x2} y1={y2} x2={x2} y2={y2 + (dim.position === 'bottom' ? (-5 * arrowDir) : (5 * arrowDir))} stroke="#000" strokeWidth="1" />
            </>
          ) : (
            <>
              <line x1={x1} y1={y1} x2={x1 + (dim.position === 'left' ? (-5 * arrowDir) : (5 * arrowDir))} y2={y1} stroke="#000" strokeWidth="1" />
              <line x1={x2} y1={y2} x2={x2 + (dim.position === 'right' ? (5 * arrowDir) : (-5 * arrowDir))} y2={y2} stroke="#000" strokeWidth="1" />
            </>
          )}
          <text
            x={finalTextX}
            y={finalTextY}
            textAnchor={dim.position === 'left' ? 'end' : dim.position === 'right' ? 'start' : 'middle'}
            dominantBaseline={dim.position === 'top' ? 'baseline' : dim.position === 'bottom' ? 'hanging' : 'middle'}
            fontSize="12"
            fill="#000"
            style={{ cursor: 'move', userSelect: 'none', pointerEvents: 'all' }}
            onMouseDown={handleTextMouseDown}
          >
            {dim.label}
          </text>
        </g>
      );
    };

    const renderAngleMarker = (marker: AngleMarker) => {
      let x = 0, y = 0;
      switch (marker.vertex) {
        case 'top-left':
          x = shapeX;
          y = shapeY;
          break;
        case 'top-right':
          x = shapeX + w;
          y = shapeY;
          break;
        case 'bottom-left':
          x = shapeX;
          y = shapeY + h;
          break;
        case 'bottom-right':
          x = shapeX + w;
          y = shapeY + h;
          break;
      }

      const size = marker.size || (marker.type === 'right-angle' ? 12 : 15);

      if (marker.type === 'right-angle') {
        const offsetX = marker.offsetX || 0;
        const offsetY = marker.offsetY || 0;
        const finalX = x + offsetX;
        const finalY = y + offsetY;
        
        const handleRightAngleMouseDown = (e: React.MouseEvent) => {
          e.stopPropagation();
          e.preventDefault();
          setDraggingMarkerId(marker.id);
        };
        
        return (
          <g key={marker.id}>
            <rect 
              x={finalX - size} 
              y={finalY - size} 
              width={size} 
              height={size} 
              fill="none" 
              stroke="#000" 
              strokeWidth="1.5"
              style={{ cursor: 'move', pointerEvents: 'all' }}
              onMouseDown={handleRightAngleMouseDown}
            />
            {marker.label && (
              <text 
                x={finalX - size - 5} 
                y={finalY - size - 5} 
                fontSize="10" 
                fill="#000"
                style={{ cursor: 'move', pointerEvents: 'all' }}
                onMouseDown={handleRightAngleMouseDown}
              >
                {marker.label}
              </text>
            )}
          </g>
        );
      } else {
        const radius = size;
        const offsetX = marker.offsetX || 0;
        const offsetY = marker.offsetY || 0;
        const startAngle = (marker.startAngle || 0) * Math.PI / 180;
        const endAngle = (marker.endAngle || 90) * Math.PI / 180;
        const rotation = (marker.rotation || 0) * Math.PI / 180;
        
        const centerX = x + offsetX;
        const centerY = y + offsetY;
        
        // Calculate arc endpoints with rotation
        const startX = centerX + radius * Math.cos(startAngle + rotation);
        const startY = centerY + radius * Math.sin(startAngle + rotation);
        const endX = centerX + radius * Math.cos(endAngle + rotation);
        const endY = centerY + radius * Math.sin(endAngle + rotation);
        
        // Determine if arc is large (sweep > 180 degrees)
        const sweepFlag = Math.abs(endAngle - startAngle) > Math.PI ? 1 : 0;
        
        const handleArcMouseDown = (e: React.MouseEvent) => {
          e.stopPropagation();
          e.preventDefault();
          setDraggingMarkerId(marker.id);
        };
        
        // Calculate rotation handle position (at the end of the arc)
        const handleX = endX;
        const handleY = endY;
        
        const handleRotationMouseDown = (e: React.MouseEvent) => {
          e.stopPropagation();
          e.preventDefault();
          setRotatingMarkerId(marker.id);
        };
        
        return (
          <g key={marker.id}>
            <path
              d={`M ${startX} ${startY} A ${radius} ${radius} 0 ${sweepFlag} 1 ${endX} ${endY}`}
              fill="none"
              stroke="#000"
              strokeWidth="2"
              style={{ cursor: 'move', pointerEvents: 'all' }}
              onMouseDown={handleArcMouseDown}
            />
            {/* Rotation handle at the end of the arc */}
            <circle
              cx={handleX}
              cy={handleY}
              r="5"
              fill="#000"
              stroke="#fff"
              strokeWidth="1.5"
              style={{ cursor: 'grab', pointerEvents: 'all' }}
              onMouseDown={handleRotationMouseDown}
            />
            {marker.label && (
              <text x={centerX + radius / 2} y={centerY - radius - 5} fontSize="10" fill="#000">{marker.label}</text>
            )}
          </g>
        );
      }
    };

    return (
      <svg ref={svgRef} width={svgWidth} height={svgHeight} className="max-w-full max-h-full">
        {/* Shape */}
        {selectedShape === 'circle' && (
          <>
            <circle
              cx={shapeX + w / 2}
              cy={shapeY + h / 2}
              r={Math.min(w, h) / 2 - 5}
              fill={fillColor}
              stroke={color}
              strokeWidth={strokeWidth}
            />
            {radiusLabel && (
              <text
                x={shapeX + w / 2 + radiusLabelOffsetX}
                y={shapeY + h / 2 - Math.min(w, h) / 2 - 10 + radiusLabelOffsetY}
                textAnchor="middle"
                fontSize="12"
                fill="#000"
                style={{ cursor: 'move', pointerEvents: 'all', userSelect: 'none' }}
                onMouseDown={(e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  setDraggingRadiusLabel(true);
                }}
              >
                {radiusLabel}
              </text>
            )}
          </>
        )}
        {selectedShape === 'square' && (
          <rect
            x={shapeX}
            y={shapeY}
            width={w}
            height={w}
            fill={fillColor}
            stroke={color}
            strokeWidth={strokeWidth}
          />
        )}
        {selectedShape === 'rectangle' && (
          <rect
            x={shapeX}
            y={shapeY}
            width={w}
            height={h}
            fill={fillColor}
            stroke={color}
            strokeWidth={strokeWidth}
          />
        )}
        {selectedShape === 'triangle' && (
          <polygon
            points={`${shapeX + w / 2},${shapeY} ${shapeX + w},${shapeY + h} ${shapeX},${shapeY + h}`}
            fill={fillColor}
            stroke={color}
            strokeWidth={strokeWidth}
          />
        )}
        
        {/* Dimension lines */}
        {dimensions.map(renderDimensionLine)}
        
        {/* Angle markers */}
        {angleMarkers.map(renderAngleMarker)}
      </svg>
    );
  }
}

