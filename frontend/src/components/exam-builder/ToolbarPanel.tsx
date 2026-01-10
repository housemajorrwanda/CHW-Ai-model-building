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
    // Insert shape node using insertContent directly
    const result = editor.chain().focus().insertContent({
      type: 'shape',
      attrs: shapeData,
    }).run();
    
    // Log for debugging
    const content = editor.getJSON();
    console.log('After shape insert, editor content:', content);
    console.log('Shape data:', shapeData);
    
    const newContent = {
      id: crypto.randomUUID(),
      contentType: 'shape',
      contentData: shapeData,
    };
    onUpdate({
      ...question,
      embeddedContent: [...question.embeddedContent, newContent],
    });
  };

  const insertGraphHTML = (graphData: any) => {
    const graphAttrs = {
      graphType: graphData.type,
      data: graphData.data,
      title: graphData.title || 'Graph',
      xLabel: graphData.xLabel || 'X Axis',
      yLabel: graphData.yLabel || 'Y Axis',
    };
    
    // Insert graph node using insertContent directly
    const result = editor.chain().focus().insertContent({
      type: 'graph',
      attrs: graphAttrs,
    }).run();
    
    // Log for debugging
    const content = editor.getJSON();
    console.log('After graph insert, editor content:', content);
    console.log('Graph attrs:', graphAttrs);
    
    const newContent = {
      id: crypto.randomUUID(),
      contentType: 'graph',
      contentData: graphData,
    };
    onUpdate({
      ...question,
      embeddedContent: [...question.embeddedContent, newContent],
    });
  };

  const insertFormula = (latex: string, displayMode: boolean) => {
    // Insert formula node using insertContent directly
    const result = editor.chain().focus().insertContent({
      type: 'formula',
      attrs: {
        latex,
        display: displayMode,
      },
    }).run();
    
    // Log for debugging
    const content = editor.getJSON();
    console.log('After formula insert, editor content:', content);
    console.log('Formula latex:', latex);
  };

  const addEmbeddedContent = (contentType: string, data: any) => {
    const newContent = {
      id: crypto.randomUUID(),
      contentType,
      contentData: data,
    };
    onUpdate({
      ...question,
      embeddedContent: [...question.embeddedContent, newContent],
    });
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
        <PopoverContent className="w-[600px] p-0">
          <Tabs defaultValue="keyboard" className="w-full">
            <TabsList className="w-full grid grid-cols-6">
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
                  addEmbeddedContent('periodic_element', element);
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

