import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { Image } from '@tiptap/extension-image';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import Highlight from '@tiptap/extension-highlight';
import { TextStyle } from '@tiptap/extension-text-style';
import { Color } from '@tiptap/extension-color';
import Link from '@tiptap/extension-link';
import CharacterCount from '@tiptap/extension-character-count';
import { Superscript } from '@tiptap/extension-superscript';
import { Subscript } from '@tiptap/extension-subscript';
import { ShapeExtension } from './extensions/ShapeExtension';
import { GraphExtension } from './extensions/GraphExtension';
import { Mathematics, migrateMathStrings } from '@tiptap/extension-mathematics';
import 'katex/dist/katex.min.css';
import Placeholder from '@tiptap/extension-placeholder';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ToolbarPanel } from './ToolbarPanel';
import { GoldSolutionEditor } from './GoldSolutionEditor';
import { AttachmentsList } from './AttachmentsList';
import { TheoryManager } from './TheoryManager';
import type { Question } from './QuestionBuilder';
import { Badge } from '@/components/ui/badge';
import { Plus } from 'lucide-react';
import { useRef, useEffect, useState } from 'react';
import { useEditorLatexCompletion } from '@/hooks/useEditorLatexCompletion';
import { EditorLatexCompletionsList } from '@/components/ui/latex-autocomplete';
import { FormulaInserter } from './tools/FormulaInserter';
import { questionOutlineLabel } from './questionOutlineLabel';
import { plainTextLooksLikeMath, plainTextWithMathToDoc } from '@/lib/plainTextWithMathToDoc';

interface QuestionEditorProps {
  question: Question;
  onUpdate: (question: Question) => void;
  onAddSubQuestion: () => void;
}

type EditingMath = { pos: number; latex: string; block: boolean };

export function QuestionEditor({ question, onUpdate, onAddSubQuestion }: QuestionEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const [editingMath, setEditingMath] = useState<EditingMath | null>(null);
  const onMathClickRef = useRef<(pos: number, latex: string, block: boolean) => void>(() => {});

  useEffect(() => {
    onMathClickRef.current = (pos, latex, block) => setEditingMath({ pos, latex, block });
  }, []);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      Underline,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Highlight.configure({ multicolor: false }),
      TextStyle,
      Color,
      Link.configure({ openOnClick: false, HTMLAttributes: { class: 'text-primary underline cursor-pointer' } }),
      CharacterCount,
      Superscript,
      Subscript,
      Table.configure({
        resizable: true,
        HTMLAttributes: { class: 'border-collapse border border-gray-300' },
      }),
      TableRow,
      TableHeader,
      TableCell.extend({
        addAttributes() {
          return { ...this.parent?.(), class: { default: 'border border-gray-300 px-3 py-2' } };
        },
      }),
      Image.configure({
        HTMLAttributes: { class: 'max-w-full rounded-lg cursor-pointer' },
        inline: false,
        allowBase64: true,
      }),
      ShapeExtension,
      GraphExtension,
      Mathematics.configure({
        inlineOptions: {
          onClick: (node, pos) => onMathClickRef.current?.(pos, node.attrs.latex ?? '', false),
        },
        blockOptions: {
          onClick: (node, pos) => onMathClickRef.current?.(pos, node.attrs.latex ?? '', true),
        },
      }),
      Placeholder.configure({ placeholder: 'Write your question here…' }),
    ],
    content: question.richContent || question.text || '',
    onUpdate: ({ editor }) => {
      onUpdate({
        ...question,
        richContent: editor.getJSON(),
        text: editor.getText(),
      });
    },
    editorProps: {
      attributes: {
        class: 'prose prose-sm sm:prose lg:prose-lg xl:prose-xl mx-auto focus:outline-none',
      },
      // Normalise LaTeX delimiters on plain-text paste so migrateMathStrings can convert them
      transformPastedText: (text: string) =>
        text
          .replace(/\\\(([\s\S]*?)\\\)/g, (_: string, m: string) => `$${m}$`)
          .replace(/\\\[([\s\S]*?)\\\]/g, (_: string, m: string) => `$$${m}$$`),
    },
    immediatelyRender: false,
    onCreate: ({ editor }) => {
      migrateMathStrings(editor);
    },
  });

  const latexCompletion = useEditorLatexCompletion(editor);

  useEffect(() => {
    if (!editor?.view) return;
    const dom = editor.view.dom;
    const onKeyDown = (e: KeyboardEvent) => {
      if (latexCompletion.handleKeyDown(editor.view as any, e)) e.preventDefault();
    };
    dom.addEventListener('keydown', onKeyDown, true);
    return () => dom.removeEventListener('keydown', onKeyDown, true);
  }, [editor, latexCompletion.handleKeyDown]);

  // After any paste event, convert $...$ text to proper math nodes
  useEffect(() => {
    if (!editor) return;
    const dom = editor.view.dom;
    const onPaste = () => setTimeout(() => migrateMathStrings(editor), 80);
    dom.addEventListener('paste', onPaste);
    return () => dom.removeEventListener('paste', onPaste);
  }, [editor]);

  // Update editor content when question changes
  useEffect(() => {
    if (!editor) return;
    
    // Use a ref to track if we've already set content for this question
    const questionId = question.id;
    const lastQuestionId = editorRef.current?.getAttribute('data-question-id');
    
    if (questionId !== lastQuestionId) {
      // Question changed, update content
      if (question.richContent) {
        editor.commands.setContent(question.richContent, { emitUpdate: false });
      } else if (question.text) {
        const t = question.text;
        if (plainTextLooksLikeMath(t)) {
          editor.commands.setContent(plainTextWithMathToDoc(t), { emitUpdate: false });
        } else {
          editor.commands.setContent(`<p>${t}</p>`, { emitUpdate: false });
        }
      } else {
        editor.commands.setContent('', { emitUpdate: false });
      }

      // Convert any raw $$...$$ / $...$ text to proper math nodes
      migrateMathStrings(editor);
      
      if (editorRef.current) {
        editorRef.current.setAttribute('data-question-id', questionId);
      }
    }
  }, [editor, question.id]);


  return (
    <div className="flex flex-col min-h-0 flex-1 space-y-6">
      {/* Question Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">
              Question {question.number}
              {question.outlineLevel > 1 && (
                <Badge variant="outline" className="ml-2">
                  Level {question.outlineLevel}
                </Badge>
              )}
            </CardTitle>
            <div className="flex items-center gap-2">
              <Label className="text-sm text-muted-foreground">Points:</Label>
              <Input
                type="number"
                value={question.points}
                onChange={(e) => onUpdate({ ...question, points: parseInt(e.target.value) || 0 })}
                className="w-20 h-8"
                min={0}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor={`outline-title-${question.id}`} className="text-sm">
              Outline label <span className="font-normal text-muted-foreground">(optional)</span>
            </Label>
            <Input
              id={`outline-title-${question.id}`}
              placeholder="e.g. Linear equations, Proof by induction"
              value={question.outlineTitle ?? ''}
              onChange={(e) =>
                onUpdate({
                  ...question,
                  outlineTitle: e.target.value,
                })
              }
              className="max-w-xl"
            />
            <p className="text-xs text-muted-foreground">
              Preview:{' '}
              <span className="font-medium text-foreground">
                Q{question.number} · {questionOutlineLabel({ ...question, outlineTitle: question.outlineTitle ?? '' })}
              </span>
            </p>
          </div>
          {/* Add Sub-question Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={onAddSubQuestion}
            className="w-full"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Sub-question
          </Button>
        </CardContent>
      </Card>

      {/* Rich Text Editor - expands to fill space (vertical and horizontal) */}
      <Card className="flex-1 flex flex-col min-h-[400px] w-full min-w-0">
        <CardHeader className="flex-none">
          <CardTitle className="text-base">Question Text</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col min-h-0 min-w-0 space-y-4 w-full">
          {/* Toolbar */}
          <ToolbarPanel editor={editor} question={question} onUpdate={onUpdate} />
          {/* Edit equation dialog (opened when clicking an existing math node) */}
          {editor && (
            <FormulaInserter
              onInsert={() => {}}
              open={editingMath !== null}
              onOpenChange={(open) => !open && setEditingMath(null)}
              initialLatex={editingMath?.latex}
              initialDisplayMode={editingMath?.block}
              onUpdate={(latex) => {
                if (!editingMath || !editor) return;
                if (editingMath.block) {
                  editor.chain().setNodeSelection(editingMath.pos).updateBlockMath({ latex }).focus().run();
                } else {
                  editor.chain().setNodeSelection(editingMath.pos).updateInlineMath({ latex }).focus().run();
                }
                setEditingMath(null);
              }}
            />
          )}

          {/* Editor Area - fills remaining vertical and horizontal space */}
          <div ref={editorRef} className="flex-1 min-h-[300px] w-full min-w-0 border rounded-lg focus-within:ring-2 focus-within:ring-primary/20 overflow-hidden relative flex flex-col">
            <div className="flex-1 min-h-0 min-w-0 flex flex-col p-4 w-full prose-editor-expand">
              <EditorContent editor={editor} className="prose prose-sm max-w-none w-full flex-1 min-w-0" />
            </div>
            {editor && latexCompletion.completionState && (
              <EditorLatexCompletionsList
                editor={editor}
                state={latexCompletion.completionState}
                onSelect={latexCompletion.applySnippet}
              />
            )}
            {editor && (
              <div className="px-3 py-1.5 border-t bg-muted/30 flex items-center justify-end gap-3 text-xs text-muted-foreground">
                <span>{editor.storage.characterCount?.words?.() ?? 0} words</span>
                <span>{editor.storage.characterCount?.characters?.() ?? 0} chars</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Attachments */}
      <AttachmentsList
        attachments={question.attachments}
        onUpdate={(attachments) => onUpdate({ ...question, attachments })}
      />

      {/* Theory & Constants */}
      <TheoryManager
        theories={question.theories}
        onUpdate={(theories) => onUpdate({ ...question, theories })}
      />

      {/* Embedded Content Display */}
      {question.embeddedContent.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Embedded Content</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {question.embeddedContent.map((content, idx) => (
                <div key={content.id} className="p-3 bg-muted rounded-lg text-sm">
                  <strong>{content.contentType}</strong>
                  {content.contentData.name && ` - ${content.contentData.name}`}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Gold Solution */}
      <GoldSolutionEditor
        steps={question.goldSolutionSteps}
        finalAnswer={question.finalAnswer}
        finalAnswerLatex={question.finalAnswerLatex}
        onUpdate={(updates) => onUpdate({ ...question, ...updates })}
      />
    </div>
  );
}

