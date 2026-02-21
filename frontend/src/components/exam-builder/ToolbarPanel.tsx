import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Image as ImageIcon,
  Table as TableIcon,
  Calculator,
  Shapes,
  BarChart3,
  Scan,
  Upload,
  Atom,
  Ruler,
  FlaskConical,
  Pi,
} from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MediaUploader } from './tools/MediaUploader';
import { ShapeInserter } from './tools/ShapeInserter';
import { GraphBuilder } from './tools/GraphBuilder';
import { PeriodicTableSelector } from './tools/PeriodicTableSelector';
import { CalculatorWidget } from './tools/CalculatorWidget';
import { UnitConverter } from './tools/UnitConverter';
import { ConstantsLibrary } from './tools/ConstantsLibrary';
import { FormulaInserter } from './tools/FormulaInserter';
import { TableControls } from './TableControls';
import { ImageControls } from './ImageControls';
import ScientificKeyboard from '../exam-taker/ScientificKeyboard';
import type { Question } from './QuestionBuilder';
import type { Editor } from '@tiptap/react';
import { useEffect, useState } from 'react';

interface ToolbarPanelProps {
  editor: Editor | null;
  question: Question;
  onUpdate: (question: Question) => void;
}

export function ToolbarPanel({ editor, question, onUpdate }: ToolbarPanelProps) {
  if (!editor) return null;

  const [selectedNode, setSelectedNode] = useState<any>(null);

  useEffect(() => {
    const updateSelection = () => {
      const { selection } = editor.state;
      let node = null;
      
      if (selection.empty) {
        const pos = selection.$anchor.pos;
        const resolvedPos = editor.state.doc.resolve(pos);
        node = resolvedPos.nodeAfter;
        
        if (!node || node.type.name !== 'image') {
          node = resolvedPos.nodeBefore;
        }
      } else {
        const { $from } = selection;
        node = $from.node($from.depth);
      }
      
      if (node?.type.name === 'image') {
        setSelectedNode(node);
      } else {
        setSelectedNode(null);
      }
    };

    editor.on('selectionUpdate', updateSelection);
    editor.on('update', updateSelection);
    updateSelection();

    return () => {
      editor.off('selectionUpdate', updateSelection);
      editor.off('update', updateSelection);
    };
  }, [editor]);

  const insertImage = (url: string) => {
    editor.chain().focus().setImage({ src: url }).run();
  };

  const insertTable = () => {
    editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
  };

  const insertShapeSVG = (shapeData: any) => {
    const { type, width, height, color, fillColor, strokeWidth, dimensions = [], angleMarkers = [], radiusLabel, radiusLabelOffsetX = 0, radiusLabelOffsetY = 0 } = shapeData;
    const w = parseInt(width) || 200;
    const h = parseInt(height) || 150;
    const c = color || '#60a5fa';
    const fill = fillColor || '#dbeafe';
    const sw = parseInt(strokeWidth) || 2;
    const padding = 40;
    const svgWidth = w + padding * 2;
    const svgHeight = h + padding * 2;
    const shapeX = padding;
    const shapeY = padding;

    let svgParts = [];

    // Render dimension lines
    const renderDimension = (dim: any) => {
      const isInside = dim.inside || false;
      const offset = isInside ? (dim.offset || 0) : ((dim.offset || 0) + 15);
      const lengthPercent = (dim.length || 100) / 100;
      const startOffset = dim.startOffset || 0;
      const endOffset = dim.endOffset || 0;
      
      let x1 = 0, y1 = 0, x2 = 0, y2 = 0, textX = 0, textY = 0, textAnchor = 'middle';
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
          textAnchor = 'end';
          break;
        case 'right':
          lineLength = h * lengthPercent;
          x1 = isInside ? shapeX + w - offset : shapeX + w + offset;
          y1 = shapeY + startOffset;
          x2 = isInside ? shapeX + w - offset : shapeX + w + offset;
          y2 = shapeY + startOffset + lineLength - endOffset;
          textX = isInside ? shapeX + w - offset + 15 : shapeX + w + offset + 15;
          textY = shapeY + startOffset + lineLength / 2;
          textAnchor = 'start';
          break;
        case 'center':
          textX = shapeX + w / 2;
          textY = shapeY + h / 2;
          break;
      }

      if (dim.position === 'center') {
        return `<text x="${textX}" y="${textY}" text-anchor="middle" dominant-baseline="middle" font-size="12" fill="#000">${dim.label || ''}</text>`;
      }

      const arrowDir = isInside ? -1 : 1;
      
      // Apply manual text offsets if provided
      const finalTextX = textX + (dim.textXOffset || 0);
      const finalTextY = textY + (dim.textYOffset || 0);
      
      return `
        <line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#000" stroke-width="1"/>
        ${dim.position === 'top' || dim.position === 'bottom' ? `
          <line x1="${x1}" y1="${y1}" x2="${x1}" y2="${y1 + (dim.position === 'top' ? (5 * arrowDir) : (-5 * arrowDir))}" stroke="#000" stroke-width="1"/>
          <line x1="${x2}" y1="${y2}" x2="${x2}" y2="${y2 + (dim.position === 'bottom' ? (-5 * arrowDir) : (5 * arrowDir))}" stroke="#000" stroke-width="1"/>
        ` : `
          <line x1="${x1}" y1="${y1}" x2="${x1 + (dim.position === 'left' ? (-5 * arrowDir) : (5 * arrowDir))}" y2="${y1}" stroke="#000" stroke-width="1"/>
          <line x1="${x2}" y1="${y2}" x2="${x2 + (dim.position === 'right' ? (5 * arrowDir) : (-5 * arrowDir))}" y2="${y2}" stroke="#000" stroke-width="1"/>
        `}
        <text x="${finalTextX}" y="${finalTextY}" text-anchor="${textAnchor}" dominant-baseline="${dim.position === 'top' ? 'baseline' : dim.position === 'bottom' ? 'hanging' : 'middle'}" font-size="12" fill="#000">${dim.label || ''}</text>
      `;
    };

    // Render angle markers
    const renderAngleMarker = (marker: any) => {
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
        return `
          <rect x="${finalX - size}" y="${finalY - size}" width="${size}" height="${size}" fill="none" stroke="#000" stroke-width="1.5"/>
          ${marker.label ? `<text x="${finalX - size - 5}" y="${finalY - size - 5}" font-size="10" fill="#000">${marker.label}</text>` : ''}
        `;
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
        
        return `
          <path d="M ${startX} ${startY} A ${radius} ${radius} 0 ${sweepFlag} 1 ${endX} ${endY}" fill="none" stroke="#000" stroke-width="2"/>
          ${marker.label ? `<text x="${centerX + radius / 2}" y="${centerY - radius - 5}" font-size="10" fill="#000">${marker.label}</text>` : ''}
        `;
      }
    };

    // Render shape
    switch (type) {
      case 'circle':
        svgParts.push(`<circle cx="${shapeX + w / 2}" cy="${shapeY + h / 2}" r="${Math.min(w, h) / 2 - 5}" fill="${fill}" stroke="${c}" stroke-width="${sw}"/>`);
        if (radiusLabel) {
          const baseX = shapeX + w / 2;
          const baseY = shapeY + h / 2 - Math.min(w, h) / 2 - 10;
          svgParts.push(`<text x="${baseX + radiusLabelOffsetX}" y="${baseY + radiusLabelOffsetY}" text-anchor="middle" font-size="12" fill="#000">${radiusLabel}</text>`);
        }
        break;
      case 'square':
        svgParts.push(`<rect x="${shapeX}" y="${shapeY}" width="${w}" height="${w}" fill="${fill}" stroke="${c}" stroke-width="${sw}"/>`);
        break;
      case 'rectangle':
        svgParts.push(`<rect x="${shapeX}" y="${shapeY}" width="${w}" height="${h}" fill="${fill}" stroke="${c}" stroke-width="${sw}"/>`);
        break;
      case 'triangle':
        svgParts.push(`<polygon points="${shapeX + w / 2},${shapeY} ${shapeX + w},${shapeY + h} ${shapeX},${shapeY + h}" fill="${fill}" stroke="${c}" stroke-width="${sw}"/>`);
        break;
    }

    // Add dimensions
    dimensions.forEach((dim: any) => {
      svgParts.push(renderDimension(dim));
    });

    // Add angle markers
    angleMarkers.forEach((marker: any) => {
      svgParts.push(renderAngleMarker(marker));
    });

    const svgContent = `data:image/svg+xml,${encodeURIComponent(`<svg width="${svgWidth}" height="${svgHeight}" xmlns="http://www.w3.org/2000/svg">${svgParts.join('')}</svg>`)}`;

    if (svgContent) {
      editor.chain().focus().setImage({ src: svgContent }).run();
    }
  };

  const insertGraphHTML = (graphData: any) => {
    // Insert as plain text description
    const graphText = `[Graph: ${graphData.title || 'Chart'} - Type: ${graphData.type}, X: ${graphData.xLabel || 'X'}, Y: ${graphData.yLabel || 'Y'}, ${graphData.data ? graphData.data.length : 0} points]`;
    editor.chain().focus().insertContent(graphText).run();
  };

  const insertFormula = (latex: string, displayMode: boolean) => {
    // Insert formula as LaTeX notation (students/readers will understand it)
    const formulaText = displayMode ? `$$${latex}$$` : `$${latex}$`;
    editor.chain().focus().insertContent(` ${formulaText} `).run();
  };

  const isTableSelected = editor.isActive('table');
  const isImageSelected = selectedNode?.type.name === 'image';

  return (
    <div className="space-y-2">
      {/* Main Toolbar */}
      <div className="flex flex-wrap items-center gap-1 p-2 border rounded-lg bg-muted/30">
        {/* Text Formatting */}
        <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={cn('h-8 w-8 p-0', editor.isActive('bold') && 'bg-accent')}
          title="Bold"
        >
          <Bold className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={cn('h-8 w-8 p-0', editor.isActive('italic') && 'bg-accent')}
          title="Italic"
        >
          <Italic className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={cn('h-8 w-8 p-0', editor.isActive('bulletList') && 'bg-accent')}
          title="Bullet List"
        >
          <List className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={cn('h-8 w-8 p-0', editor.isActive('orderedList') && 'bg-accent')}
          title="Numbered List"
        >
          <ListOrdered className="h-4 w-4" />
        </Button>
      </div>

      <Separator orientation="vertical" className="h-6" />

      {/* Media Tools */}
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="ghost" size="sm" className="h-8 px-2" title="Upload Media">
            <Upload className="h-4 w-4 mr-1" />
            Media
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80">
          <MediaUploader
            onImageUpload={insertImage}
            onAttachmentAdd={(attachment) => {
              onUpdate({
                ...question,
                attachments: [...question.attachments, attachment],
              });
            }}
          />
        </PopoverContent>
      </Popover>

      {/* Table */}
      <Button
        variant="ghost"
        size="sm"
        onClick={insertTable}
        className="h-8 px-2"
        title="Insert Table"
      >
        <TableIcon className="h-4 w-4 mr-1" />
        Table
      </Button>

      {/* Formula */}
      <FormulaInserter onInsert={insertFormula} />

      <Separator orientation="vertical" className="h-6" />

      {/* Scientific Tools */}
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="ghost" size="sm" className="h-8 px-2" title="Scientific Tools">
            <FlaskConical className="h-4 w-4 mr-1" />
            Tools
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[600px] p-0 max-h-[80vh] flex flex-col">
          <Tabs defaultValue="keyboard" className="w-full flex flex-col flex-1 min-h-0">
            <TabsList className="w-full grid grid-cols-6 flex-shrink-0">
              <TabsTrigger value="keyboard" className="text-xs">
                Keyboard
              </TabsTrigger>
              <TabsTrigger value="calculator">
                <Calculator className="h-4 w-4" />
              </TabsTrigger>
              <TabsTrigger value="periodic">
                <Atom className="h-4 w-4" />
              </TabsTrigger>
              <TabsTrigger value="units">
                <Ruler className="h-4 w-4" />
              </TabsTrigger>
              <TabsTrigger value="constants">
                <Pi className="h-4 w-4" />
              </TabsTrigger>
              <TabsTrigger value="shapes">
                <Shapes className="h-4 w-4" />
              </TabsTrigger>
            </TabsList>

            <div className="flex-1 overflow-y-auto min-h-0">
              <TabsContent value="keyboard" className="p-4">
                <ScientificKeyboard
                  onInsert={(symbol) => {
                    editor.chain().focus().insertContent(symbol).run();
                  }}
                />
              </TabsContent>

              <TabsContent value="calculator" className="p-4">
                <CalculatorWidget
                  onInsert={(value) => {
                    editor.chain().focus().insertContent(value).run();
                  }}
                />
              </TabsContent>

              <TabsContent value="periodic" className="p-4">
                <PeriodicTableSelector
                  onSelect={(element) => {
                    editor.chain().focus().insertContent(element.symbol).run();
                  }}
                />
              </TabsContent>

              <TabsContent value="units" className="p-4">
                <UnitConverter
                  onInsert={(value) => {
                    editor.chain().focus().insertContent(value).run();
                  }}
                />
              </TabsContent>

              <TabsContent value="constants" className="p-4">
                <ConstantsLibrary
                  onSelect={(constant) => {
                    editor.chain().focus().insertContent(`${constant.symbol} = ${constant.value}`).run();
                  }}
                />
              </TabsContent>

              <TabsContent value="shapes" className="p-4">
                <ShapeInserter
                  onInsert={insertShapeSVG}
                />
              </TabsContent>
            </div>
          </Tabs>
        </PopoverContent>
      </Popover>

      {/* Graph Builder */}
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="ghost" size="sm" className="h-8 px-2" title="Insert Graph">
            <BarChart3 className="h-4 w-4 mr-1" />
            Graph
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-96">
          <GraphBuilder
            onInsert={insertGraphHTML}
          />
        </PopoverContent>
      </Popover>
      </div>

      {/* Contextual Controls */}
      {isTableSelected && (
        <TableControls editor={editor} />
      )}
      {isImageSelected && (
        <ImageControls editor={editor} imageNode={selectedNode} />
      )}
    </div>
  );
}

