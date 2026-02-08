import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { Image } from '@tiptap/extension-image';
import { ShapeExtension } from './extensions/ShapeExtension';
import { GraphExtension } from './extensions/GraphExtension';
import { FormulaExtension } from './extensions/FormulaExtension';
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
import { useRef, useEffect } from 'react';

interface QuestionEditorProps {
  question: Question;
  onUpdate: (question: Question) => void;
  onAddSubQuestion: () => void;
}

export function QuestionEditor({ question, onUpdate, onAddSubQuestion }: QuestionEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Allow HTML content
      }),
      Table.configure({
        resizable: true,
        HTMLAttributes: {
          class: 'border-collapse border border-gray-300',
        },
      }),
      TableRow,
      TableHeader,
      TableCell.extend({
        addAttributes() {
          return {
            ...this.parent?.(),
            class: {
              default: 'border border-gray-300 px-3 py-2',
            },
          };
        },
      }),
      Image.configure({
        HTMLAttributes: {
          class: 'max-w-full rounded-lg cursor-pointer',
        },
        inline: false,
        allowBase64: true,
      }),
      ShapeExtension,
      GraphExtension,
      FormulaExtension,
    ],
    content: question.richContent || question.text || '<p>Enter your question here...</p>',
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
    },
    immediatelyRender: false,
  });

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
        editor.commands.setContent(`<p>${question.text}</p>`, { emitUpdate: false });
      } else {
        editor.commands.setContent('<p>Enter your question here...</p>', { emitUpdate: false });
      }
      
      if (editorRef.current) {
        editorRef.current.setAttribute('data-question-id', questionId);
      }
    }
  }, [editor, question.id]);


  return (
    <div className="space-y-6">
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

      {/* Rich Text Editor */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Question Text</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Toolbar */}
          <ToolbarPanel editor={editor} question={question} onUpdate={onUpdate} />

          {/* Editor Area */}
          <div ref={editorRef} className="border rounded-lg p-4 min-h-[200px] prose max-w-none focus-within:ring-2 focus-within:ring-primary/20">
            <EditorContent editor={editor} />
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

