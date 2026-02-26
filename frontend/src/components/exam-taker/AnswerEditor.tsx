import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Superscript } from '@tiptap/extension-superscript';
import { Subscript } from '@tiptap/extension-subscript';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import Highlight from '@tiptap/extension-highlight';
import CharacterCount from '@tiptap/extension-character-count';
import { Mathematics, migrateMathStrings } from '@tiptap/extension-mathematics';
import 'katex/dist/katex.min.css';
import { Button } from '@/components/ui/button';
import { Toggle } from '@/components/ui/toggle';
import { Separator } from '@/components/ui/separator';
import {
  Bold, Italic, Underline as UnderlineIcon, Strikethrough,
  List, ListOrdered,
  AlignLeft, AlignCenter, AlignRight,
  Superscript as SuperscriptIcon, Subscript as SubscriptIcon,
  Undo, Redo, Calculator, Highlighter,
} from 'lucide-react';
import { useEffect, useState, useCallback } from 'react';
import Placeholder from '@tiptap/extension-placeholder';
import ScientificKeyboard from './ScientificKeyboard';
import { FormulaInserter } from '../exam-builder/tools/FormulaInserter';
import { cn } from '@/lib/utils';

interface AnswerEditorProps {
  questionNumber: number;
  questionText: string;
  questionPoints: number;
  answer: string;
  onUpdate: (answer: string) => void;
  placeholder?: string;
}

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
        'inline-flex items-center justify-center h-7 w-7 rounded text-sm transition-colors',
        'hover:bg-accent hover:text-accent-foreground',
        'disabled:pointer-events-none disabled:opacity-40',
        active && 'bg-accent text-accent-foreground font-semibold',
      )}
    >
      {children}
    </button>
  );
}

function TSep() {
  return <Separator orientation="vertical" className="h-5 mx-0.5" />;
}

export function AnswerEditor({
  questionNumber,
  questionText,
  questionPoints,
  answer,
  onUpdate,
  placeholder = 'Type your answer here…',
}: AnswerEditorProps) {
  const [showKeyboard, setShowKeyboard] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      Superscript,
      Subscript,
      Underline,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Highlight.configure({ multicolor: false }),
      CharacterCount,
      Mathematics,
      Placeholder.configure({ placeholder }),
    ],
    content: answer || '',
    onUpdate: ({ editor }) => {
      onUpdate(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class: 'prose prose-sm max-w-none focus:outline-none min-h-[250px] p-4',
      },
      transformPastedText: (text: string) =>
        text
          .replace(/\\\(([\s\S]*?)\\\)/g, (_: string, m: string) => `$${m}$`)
          .replace(/\\\[([\s\S]*?)\\\]/g, (_: string, m: string) => `$$${m}$$`),
    },
    immediatelyRender: false,
  });

  // After any paste, convert $...$ to proper math nodes
  useEffect(() => {
    if (!editor) return;
    const dom = editor.view.dom;
    const onPaste = () => setTimeout(() => migrateMathStrings(editor), 80);
    dom.addEventListener('paste', onPaste);
    return () => dom.removeEventListener('paste', onPaste);
  }, [editor]);

  useEffect(() => {
    if (!editor) return;
    const current = editor.getHTML();
    const next = answer || '';
    if (current !== next) {
      editor.commands.setContent(next, { emitUpdate: false });
    }
  }, [answer, questionNumber, editor]);

  const insertFormula = useCallback((latex: string, displayMode: boolean) => {
    if (!editor) return;
    const chain = editor.chain().focus() as any;
    if (displayMode) chain.insertBlockMath({ latex }).run();
    else chain.insertInlineMath({ latex }).run();
  }, [editor]);

  const insertSymbol = useCallback((symbol: string) => {
    editor?.chain().focus().insertContent(symbol).run();
  }, [editor]);

  if (!editor) return null;

  const words = editor.storage.characterCount?.words?.() ?? 0;
  const chars = editor.storage.characterCount?.characters?.() ?? 0;

  return (
    <div className="space-y-0 border rounded-lg overflow-hidden bg-background shadow-sm">
      {/* ── Toolbar ── */}
      <div className="flex flex-wrap items-center gap-0.5 px-2 py-1.5 border-b bg-muted/20 sticky top-0 z-10 backdrop-blur">
        {/* History */}
        <TB onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} title="Undo (Ctrl+Z)">
          <Undo className="h-3.5 w-3.5" />
        </TB>
        <TB onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} title="Redo (Ctrl+Y)">
          <Redo className="h-3.5 w-3.5" />
        </TB>

        <TSep />

        {/* Formatting */}
        <TB onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="Bold (Ctrl+B)">
          <Bold className="h-3.5 w-3.5" />
        </TB>
        <TB onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="Italic (Ctrl+I)">
          <Italic className="h-3.5 w-3.5" />
        </TB>
        <TB onClick={() => (editor.chain().focus() as any).toggleUnderline().run()} active={editor.isActive('underline')} title="Underline (Ctrl+U)">
          <UnderlineIcon className="h-3.5 w-3.5" />
        </TB>
        <TB onClick={() => editor.chain().focus().toggleStrike().run()} active={editor.isActive('strike')} title="Strikethrough">
          <Strikethrough className="h-3.5 w-3.5" />
        </TB>
        <TB onClick={() => (editor.chain().focus() as any).toggleHighlight().run()} active={editor.isActive('highlight')} title="Highlight">
          <Highlighter className="h-3.5 w-3.5" />
        </TB>

        <TSep />

        {/* Sub/Superscript */}
        <TB onClick={() => editor.chain().focus().toggleSuperscript().run()} active={editor.isActive('superscript')} title="Superscript (e.g. x²)">
          <SuperscriptIcon className="h-3.5 w-3.5" />
        </TB>
        <TB onClick={() => editor.chain().focus().toggleSubscript().run()} active={editor.isActive('subscript')} title="Subscript (e.g. H₂O)">
          <SubscriptIcon className="h-3.5 w-3.5" />
        </TB>

        <TSep />

        {/* Alignment */}
        <TB onClick={() => (editor.chain().focus() as any).setTextAlign('left').run()} active={editor.isActive({ textAlign: 'left' })} title="Align Left">
          <AlignLeft className="h-3.5 w-3.5" />
        </TB>
        <TB onClick={() => (editor.chain().focus() as any).setTextAlign('center').run()} active={editor.isActive({ textAlign: 'center' })} title="Align Center">
          <AlignCenter className="h-3.5 w-3.5" />
        </TB>
        <TB onClick={() => (editor.chain().focus() as any).setTextAlign('right').run()} active={editor.isActive({ textAlign: 'right' })} title="Align Right">
          <AlignRight className="h-3.5 w-3.5" />
        </TB>

        <TSep />

        {/* Lists */}
        <TB onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="Bullet List">
          <List className="h-3.5 w-3.5" />
        </TB>
        <TB onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="Numbered List">
          <ListOrdered className="h-3.5 w-3.5" />
        </TB>

        <TSep />

        {/* Formula */}
        <FormulaInserter onInsert={insertFormula} compact />

        {/* Scientific Keyboard toggle */}
        <TB onClick={() => setShowKeyboard((v) => !v)} active={showKeyboard} title="Scientific Keyboard">
          <Calculator className="h-3.5 w-3.5" />
        </TB>
      </div>

      {/* ── Scientific Keyboard ── */}
      {showKeyboard && (
        <div className="border-b p-3 bg-muted/10">
          <ScientificKeyboard onInsert={insertSymbol} />
        </div>
      )}

      {/* ── Editor Area ── */}
      <EditorContent editor={editor} className="prose-editor-expand" />

      {/* ── Footer: word / char count ── */}
      <div className="px-4 py-1.5 border-t bg-muted/20 flex items-center justify-end gap-3 text-xs text-muted-foreground">
        <span>{words} {words === 1 ? 'word' : 'words'}</span>
        <span>{chars} {chars === 1 ? 'char' : 'chars'}</span>
      </div>
    </div>
  );
}
