import { cn } from '@/lib/utils';
import {
  Bold, Italic, Underline as UnderlineIcon, Strikethrough, Code,
  AlignLeft, AlignCenter, AlignRight, AlignJustify,
  List, ListOrdered, Undo, Redo,
  Image as ImageIcon, Table as TableIcon,
  Calculator, Shapes, BarChart3, Upload,
  Atom, Ruler, FlaskConical, Pi,
  Highlighter, Link2, Heading1, Heading2, Heading3,
  Superscript as SuperscriptIcon, Subscript as SubscriptIcon,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Popover, PopoverContent, PopoverTrigger,
} from '@/components/ui/popover';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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

/** Compact toolbar button with active highlight */
function TB({
  onClick, active = false, disabled = false, title, children,
}: {
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        'inline-flex items-center justify-center h-8 w-8 rounded text-sm transition-colors',
        'hover:bg-accent hover:text-accent-foreground',
        'disabled:pointer-events-none disabled:opacity-40',
        active && 'bg-accent text-accent-foreground font-semibold',
      )}
    >
      {children}
    </button>
  );
}

function ToolSep() {
  return <Separator orientation="vertical" className="h-6 mx-0.5" />;
}

export function ToolbarPanel({ editor, question, onUpdate }: ToolbarPanelProps) {
  const [selectedNode, setSelectedNode] = useState<any>(null);

  useEffect(() => {
    if (!editor) return;
    const updateSelection = () => {
      const { selection } = editor.state;
      let node = null;
      if (selection.empty) {
        const pos = selection.$anchor.pos;
        const resolved = editor.state.doc.resolve(pos);
        node = resolved.nodeAfter;
        if (!node || node.type.name !== 'image') node = resolved.nodeBefore;
      } else {
        const { $from } = selection;
        node = $from.node($from.depth);
      }
      setSelectedNode(node?.type.name === 'image' ? node : null);
    };
    editor.on('selectionUpdate', updateSelection);
    editor.on('update', updateSelection);
    updateSelection();
    return () => {
      editor.off('selectionUpdate', updateSelection);
      editor.off('update', updateSelection);
    };
  }, [editor]);

  if (!editor) return null;

  /* ── helpers ── */
  const insertImage = (url: string) => editor.chain().focus().setImage({ src: url }).run();
  const insertTable = () => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
  const insertFormula = (latex: string, displayMode: boolean) => {
    const chain = editor.chain().focus() as any;
    if (displayMode) chain.insertBlockMath({ latex }).run();
    else chain.insertInlineMath({ latex }).run();
  };
  const insertGraphHTML = (graphData: any) => {
    (editor.chain().focus() as any).insertGraph({
      graphType: graphData.type,
      data: graphData.data,
      title: graphData.title || 'Graph',
      xLabel: graphData.xLabel || 'X',
      yLabel: graphData.yLabel || 'Y',
    }).run();
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
    let svgParts: string[] = [];

    const renderDimension = (dim: any) => {
      const isInside = dim.inside || false;
      const offset = isInside ? (dim.offset || 0) : ((dim.offset || 0) + 15);
      const lengthPercent = (dim.length || 100) / 100;
      const startOffset = dim.startOffset || 0;
      const endOffset = dim.endOffset || 0;
      let x1 = 0, y1 = 0, x2 = 0, y2 = 0, textX = 0, textY = 0, textAnchor = 'middle';
      let lineLength = 0;
      switch (dim.position) {
        case 'top': lineLength = w * lengthPercent; x1 = shapeX + startOffset; y1 = isInside ? shapeY + offset : shapeY - offset; x2 = shapeX + startOffset + lineLength - endOffset; y2 = y1; textX = shapeX + startOffset + lineLength / 2; textY = isInside ? y1 - 5 : y1 - 5; break;
        case 'bottom': lineLength = w * lengthPercent; x1 = shapeX + startOffset; y1 = isInside ? shapeY + h - offset : shapeY + h + offset; x2 = shapeX + startOffset + lineLength - endOffset; y2 = y1; textX = shapeX + startOffset + lineLength / 2; textY = isInside ? y1 + 15 : y1 + 15; break;
        case 'left': lineLength = h * lengthPercent; x1 = isInside ? shapeX + offset : shapeX - offset; y1 = shapeY + startOffset; x2 = x1; y2 = shapeY + startOffset + lineLength - endOffset; textX = isInside ? x1 - 5 : x1 - 5; textY = shapeY + startOffset + lineLength / 2; textAnchor = 'end'; break;
        case 'right': lineLength = h * lengthPercent; x1 = isInside ? shapeX + w - offset : shapeX + w + offset; y1 = shapeY + startOffset; x2 = x1; y2 = shapeY + startOffset + lineLength - endOffset; textX = isInside ? x1 + 15 : x1 + 15; textY = shapeY + startOffset + lineLength / 2; textAnchor = 'start'; break;
        case 'center': return `<text x="${shapeX + w / 2}" y="${shapeY + h / 2}" text-anchor="middle" dominant-baseline="middle" font-size="12" fill="#000">${dim.label || ''}</text>`;
      }
      const arrowDir = isInside ? -1 : 1;
      const finalTextX = textX + (dim.textXOffset || 0);
      const finalTextY = textY + (dim.textYOffset || 0);
      return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#000" stroke-width="1"/><text x="${finalTextX}" y="${finalTextY}" text-anchor="${textAnchor}" font-size="12" fill="#000">${dim.label || ''}</text>`;
    };

    const renderAngleMarker = (marker: any) => {
      let x = 0, y = 0;
      if (marker.vertex === 'top-left') { x = shapeX; y = shapeY; }
      else if (marker.vertex === 'top-right') { x = shapeX + w; y = shapeY; }
      else if (marker.vertex === 'bottom-left') { x = shapeX; y = shapeY + h; }
      else { x = shapeX + w; y = shapeY + h; }
      const size = marker.size || (marker.type === 'right-angle' ? 12 : 15);
      if (marker.type === 'right-angle') {
        return `<rect x="${x + (marker.offsetX||0) - size}" y="${y + (marker.offsetY||0) - size}" width="${size}" height="${size}" fill="none" stroke="#000" stroke-width="1.5"/>`;
      }
      const radius = size; const cx = x + (marker.offsetX||0); const cy = y + (marker.offsetY||0);
      const startAngle = ((marker.startAngle || 0) + (marker.rotation || 0)) * Math.PI / 180;
      const endAngle = ((marker.endAngle || 90) + (marker.rotation || 0)) * Math.PI / 180;
      const sx = cx + radius * Math.cos(startAngle); const sy = cy + radius * Math.sin(startAngle);
      const ex = cx + radius * Math.cos(endAngle); const ey = cy + radius * Math.sin(endAngle);
      return `<path d="M ${sx} ${sy} A ${radius} ${radius} 0 0 1 ${ex} ${ey}" fill="none" stroke="#000" stroke-width="2"/>`;
    };

    switch (type) {
      case 'circle': svgParts.push(`<circle cx="${shapeX + w / 2}" cy="${shapeY + h / 2}" r="${Math.min(w, h) / 2 - 5}" fill="${fill}" stroke="${c}" stroke-width="${sw}"/>`); break;
      case 'square': svgParts.push(`<rect x="${shapeX}" y="${shapeY}" width="${w}" height="${w}" fill="${fill}" stroke="${c}" stroke-width="${sw}"/>`); break;
      case 'rectangle': svgParts.push(`<rect x="${shapeX}" y="${shapeY}" width="${w}" height="${h}" fill="${fill}" stroke="${c}" stroke-width="${sw}"/>`); break;
      case 'triangle': svgParts.push(`<polygon points="${shapeX + w / 2},${shapeY} ${shapeX + w},${shapeY + h} ${shapeX},${shapeY + h}" fill="${fill}" stroke="${c}" stroke-width="${sw}"/>`); break;
    }
    if (radiusLabel) svgParts.push(`<text x="${shapeX + w / 2 + radiusLabelOffsetX}" y="${shapeY + h / 2 - Math.min(w, h) / 2 - 10 + radiusLabelOffsetY}" text-anchor="middle" font-size="12" fill="#000">${radiusLabel}</text>`);
    dimensions.forEach((d: any) => svgParts.push(renderDimension(d)));
    angleMarkers.forEach((m: any) => svgParts.push(renderAngleMarker(m)));
    const svgContent = `data:image/svg+xml,${encodeURIComponent(`<svg width="${svgWidth}" height="${svgHeight}" xmlns="http://www.w3.org/2000/svg">${svgParts.join('')}</svg>`)}`;
    if (svgContent) editor.chain().focus().setImage({ src: svgContent }).run();
  };

  const setLink = () => {
    const url = window.prompt('Enter URL:', editor.getAttributes('link').href || 'https://');
    if (url === null) return;
    if (url === '') { editor.chain().focus().unsetLink().run(); return; }
    editor.chain().focus().setLink({ href: url }).run();
  };

  const headingLabel = () => {
    if (editor.isActive('heading', { level: 1 })) return 'H1';
    if (editor.isActive('heading', { level: 2 })) return 'H2';
    if (editor.isActive('heading', { level: 3 })) return 'H3';
    return 'Normal';
  };

  const isTableSelected = editor.isActive('table');
  const isImageSelected = selectedNode?.type.name === 'image';

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-0.5 p-1.5 border rounded-lg bg-muted/20">

        {/* ── History ── */}
        <TB onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} title="Undo (Ctrl+Z)">
          <Undo className="h-4 w-4" />
        </TB>
        <TB onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} title="Redo (Ctrl+Y)">
          <Redo className="h-4 w-4" />
        </TB>

        <ToolSep />

        {/* ── Heading selector ── */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="inline-flex items-center gap-1 h-8 px-2 rounded text-xs font-medium hover:bg-accent transition-colors"
              title="Text style"
            >
              {headingLabel()} <ChevronDown className="h-3 w-3 opacity-60" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuItem onClick={() => editor.chain().focus().setParagraph().run()} className={cn(editor.isActive('paragraph') && 'bg-accent')}>
              Normal
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} className={cn(editor.isActive('heading', { level: 1 }) && 'bg-accent')}>
              <span className="font-bold text-lg">H1 — Heading 1</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} className={cn(editor.isActive('heading', { level: 2 }) && 'bg-accent')}>
              <span className="font-semibold text-base">H2 — Heading 2</span>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} className={cn(editor.isActive('heading', { level: 3 }) && 'bg-accent')}>
              <span className="font-medium">H3 — Heading 3</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <ToolSep />

        {/* ── Text formatting ── */}
        <TB onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="Bold (Ctrl+B)">
          <Bold className="h-4 w-4" />
        </TB>
        <TB onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="Italic (Ctrl+I)">
          <Italic className="h-4 w-4" />
        </TB>
        <TB onClick={() => (editor.chain().focus() as any).toggleUnderline().run()} active={editor.isActive('underline')} title="Underline (Ctrl+U)">
          <UnderlineIcon className="h-4 w-4" />
        </TB>
        <TB onClick={() => editor.chain().focus().toggleStrike().run()} active={editor.isActive('strike')} title="Strikethrough">
          <Strikethrough className="h-4 w-4" />
        </TB>
        <TB onClick={() => editor.chain().focus().toggleCode().run()} active={editor.isActive('code')} title="Inline Code">
          <Code className="h-4 w-4" />
        </TB>
        <TB onClick={() => (editor.chain().focus() as any).toggleHighlight().run()} active={editor.isActive('highlight')} title="Highlight">
          <Highlighter className="h-4 w-4" />
        </TB>
        <TB onClick={() => (editor.chain().focus() as any).toggleSuperscript().run()} active={editor.isActive('superscript')} title="Superscript">
          <SuperscriptIcon className="h-4 w-4" />
        </TB>
        <TB onClick={() => (editor.chain().focus() as any).toggleSubscript().run()} active={editor.isActive('subscript')} title="Subscript">
          <SubscriptIcon className="h-4 w-4" />
        </TB>
        <TB onClick={setLink} active={editor.isActive('link')} title="Insert / Edit Link">
          <Link2 className="h-4 w-4" />
        </TB>

        <ToolSep />

        {/* ── Alignment ── */}
        <TB onClick={() => (editor.chain().focus() as any).setTextAlign('left').run()} active={editor.isActive({ textAlign: 'left' })} title="Align Left">
          <AlignLeft className="h-4 w-4" />
        </TB>
        <TB onClick={() => (editor.chain().focus() as any).setTextAlign('center').run()} active={editor.isActive({ textAlign: 'center' })} title="Align Center">
          <AlignCenter className="h-4 w-4" />
        </TB>
        <TB onClick={() => (editor.chain().focus() as any).setTextAlign('right').run()} active={editor.isActive({ textAlign: 'right' })} title="Align Right">
          <AlignRight className="h-4 w-4" />
        </TB>
        <TB onClick={() => (editor.chain().focus() as any).setTextAlign('justify').run()} active={editor.isActive({ textAlign: 'justify' })} title="Justify">
          <AlignJustify className="h-4 w-4" />
        </TB>

        <ToolSep />

        {/* ── Lists ── */}
        <TB onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="Bullet List">
          <List className="h-4 w-4" />
        </TB>
        <TB onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="Numbered List">
          <ListOrdered className="h-4 w-4" />
        </TB>

        <ToolSep />

        {/* ── Formula ── */}
        <FormulaInserter onInsert={insertFormula} />

        {/* ── Media ── */}
        <Popover>
          <PopoverTrigger asChild>
            <button type="button" title="Upload Media" className="inline-flex items-center gap-1 h-8 px-2 rounded text-xs font-medium hover:bg-accent transition-colors">
              <Upload className="h-4 w-4" /> Media
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-80">
            <MediaUploader
              onImageUpload={insertImage}
              onAttachmentAdd={(attachment) => onUpdate({ ...question, attachments: [...question.attachments, attachment] })}
            />
          </PopoverContent>
        </Popover>

        {/* ── Table ── */}
        <button
          type="button"
          onClick={insertTable}
          title="Insert Table"
          className="inline-flex items-center gap-1 h-8 px-2 rounded text-xs font-medium hover:bg-accent transition-colors"
        >
          <TableIcon className="h-4 w-4" /> Table
        </button>

        <ToolSep />

        {/* ── Scientific Tools ── */}
        <Popover>
          <PopoverTrigger asChild>
            <button type="button" title="Scientific Tools" className="inline-flex items-center gap-1 h-8 px-2 rounded text-xs font-medium hover:bg-accent transition-colors">
              <FlaskConical className="h-4 w-4" /> Tools
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-[600px] p-0 max-h-[80vh] flex flex-col">
            <Tabs defaultValue="keyboard" className="w-full flex flex-col flex-1 min-h-0">
              <TabsList className="w-full grid grid-cols-6 flex-shrink-0">
                <TabsTrigger value="keyboard" className="text-xs">Keyboard</TabsTrigger>
                <TabsTrigger value="calculator"><Calculator className="h-4 w-4" /></TabsTrigger>
                <TabsTrigger value="periodic"><Atom className="h-4 w-4" /></TabsTrigger>
                <TabsTrigger value="units"><Ruler className="h-4 w-4" /></TabsTrigger>
                <TabsTrigger value="constants"><Pi className="h-4 w-4" /></TabsTrigger>
                <TabsTrigger value="shapes"><Shapes className="h-4 w-4" /></TabsTrigger>
              </TabsList>
              <div className="flex-1 overflow-y-auto min-h-0">
                <TabsContent value="keyboard" className="p-4">
                  <ScientificKeyboard onInsert={(s) => editor.chain().focus().insertContent(s).run()} />
                </TabsContent>
                <TabsContent value="calculator" className="p-4">
                  <CalculatorWidget onInsert={(v) => editor.chain().focus().insertContent(v).run()} />
                </TabsContent>
                <TabsContent value="periodic" className="p-4">
                  <PeriodicTableSelector onSelect={(e) => editor.chain().focus().insertContent(e.symbol).run()} />
                </TabsContent>
                <TabsContent value="units" className="p-4">
                  <UnitConverter onInsert={(v) => editor.chain().focus().insertContent(v).run()} />
                </TabsContent>
                <TabsContent value="constants" className="p-4">
                  <ConstantsLibrary onSelect={(c) => editor.chain().focus().insertContent(`${c.symbol} = ${c.value}`).run()} />
                </TabsContent>
                <TabsContent value="shapes" className="p-4">
                  <ShapeInserter onInsert={insertShapeSVG} />
                </TabsContent>
              </div>
            </Tabs>
          </PopoverContent>
        </Popover>

        {/* ── Graph ── */}
        <Popover>
          <PopoverTrigger asChild>
            <button type="button" title="Insert Graph" className="inline-flex items-center gap-1 h-8 px-2 rounded text-xs font-medium hover:bg-accent transition-colors">
              <BarChart3 className="h-4 w-4" /> Graph
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-96">
            <GraphBuilder onInsert={insertGraphHTML} />
          </PopoverContent>
        </Popover>
      </div>

      {/* ── Contextual controls ── */}
      {isTableSelected && <TableControls editor={editor} />}
      {isImageSelected && <ImageControls editor={editor} imageNode={selectedNode} />}
    </div>
  );
}
