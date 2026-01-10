import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Superscript } from '@tiptap/extension-superscript';
import { Subscript } from '@tiptap/extension-subscript';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Bold, 
  Italic, 
  List, 
  ListOrdered, 
  Undo, 
  Redo,
  Sigma,
  Superscript as SuperscriptIcon,
  Subscript as SubscriptIcon,
  Calculator
} from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { Toggle } from '@/components/ui/toggle';
import { useEffect, useState } from 'react';
import ScientificKeyboard from './ScientificKeyboard';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

interface AnswerEditorProps {
  questionNumber: number;
  questionText: string;
  questionPoints: number;
  answer: string;
  onUpdate: (answer: string) => void;
}

export function AnswerEditor({ 
  questionNumber, 
  questionText, 
  questionPoints, 
  answer, 
  onUpdate 
}: AnswerEditorProps) {
  const [showKeyboard, setShowKeyboard] = useState(false);
  
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      Superscript,
      Subscript,
    ],
    content: answer || '<p>Type your answer here...</p>',
    onUpdate: ({ editor }) => {
      onUpdate(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[300px] p-4',
        style: 'min-height: 300px; max-height: none;',
      },
    },
    immediatelyRender: false,
  });

  // Update editor when answer changes externally
  useEffect(() => {
    if (editor && answer && editor.getHTML() !== answer) {
      editor.commands.setContent(answer, { emitUpdate: false });
    }
  }, [answer, editor]);

  const insertMath = () => {
    const latex = prompt('Enter LaTeX formula (e.g., x^2 + 2x + 1):');
    if (latex && editor) {
      editor.chain().focus().insertContent(`$$${latex}$$`).run();
    }
  };

  const insertSymbol = (symbol: string) => {
    if (editor) {
      editor.chain().focus().insertContent(symbol).run();
    }
  };

  if (!editor) {
    return null;
  }

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="border rounded-lg p-2 bg-muted/50 sticky top-0 z-10 bg-background/95 backdrop-blur">
          <div className="flex flex-wrap items-center gap-1">
            <Toggle
              size="sm"
              pressed={editor.isActive('bold')}
              onPressedChange={() => editor.chain().focus().toggleBold().run()}
              aria-label="Bold"
            >
              <Bold className="h-4 w-4" />
            </Toggle>
            <Toggle
              size="sm"
              pressed={editor.isActive('italic')}
              onPressedChange={() => editor.chain().focus().toggleItalic().run()}
              aria-label="Italic"
            >
              <Italic className="h-4 w-4" />
            </Toggle>
            
            <Separator orientation="vertical" className="h-6 mx-1" />
            
            <Toggle
              size="sm"
              pressed={editor.isActive('bulletList')}
              onPressedChange={() => editor.chain().focus().toggleBulletList().run()}
              aria-label="Bullet List"
            >
              <List className="h-4 w-4" />
            </Toggle>
            <Toggle
              size="sm"
              pressed={editor.isActive('orderedList')}
              onPressedChange={() => editor.chain().focus().toggleOrderedList().run()}
              aria-label="Numbered List"
            >
              <ListOrdered className="h-4 w-4" />
            </Toggle>
            
            <Separator orientation="vertical" className="h-6 mx-1" />
            
            <Toggle
              size="sm"
              pressed={editor.isActive('superscript')}
              onPressedChange={() => editor.chain().focus().toggleSuperscript().run()}
              aria-label="Superscript"
            >
              <SuperscriptIcon className="h-4 w-4" />
            </Toggle>
            <Toggle
              size="sm"
              pressed={editor.isActive('subscript')}
              onPressedChange={() => editor.chain().focus().toggleSubscript().run()}
              aria-label="Subscript"
            >
              <SubscriptIcon className="h-4 w-4" />
            </Toggle>
            
            <Separator orientation="vertical" className="h-6 mx-1" />
            
            <Button
              variant="ghost"
              size="sm"
              onClick={insertMath}
              className="h-8 px-2"
            >
              <Sigma className="h-4 w-4" />
            </Button>
            
            <Toggle
              size="sm"
              pressed={showKeyboard}
              onPressedChange={setShowKeyboard}
              aria-label="Scientific Keyboard"
            >
              <Calculator className="h-4 w-4" />
            </Toggle>
            
            <Separator orientation="vertical" className="h-6 mx-1" />
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor.chain().focus().undo().run()}
              disabled={!editor.can().undo()}
              className="h-8 px-2"
            >
              <Undo className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor.chain().focus().redo().run()}
              disabled={!editor.can().redo()}
              className="h-8 px-2"
            >
              <Redo className="h-4 w-4" />
            </Button>
          </div>
        </div>

      {/* Scientific Keyboard */}
      {showKeyboard && (
        <ScientificKeyboard onInsert={insertSymbol} />
      )}

      {/* Editor Area */}
      <div className="border rounded-lg bg-background focus-within:ring-2 focus-within:ring-primary/20 overflow-hidden">
        <EditorContent editor={editor} className="prose-editor-expand" />
      </div>
      
      <p className="text-xs text-muted-foreground">
        Tip: Use the <Calculator className="h-3 w-3 inline" /> button for scientific symbols, or the Σ button to insert mathematical formulas in LaTeX format. The editor will expand as you type.
      </p>
    </div>
  );
}

