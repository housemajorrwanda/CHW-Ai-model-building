/**
 * Read-only TipTap renderer with full Mathematics (KaTeX) support.
 * Used to display professor-authored question content to students.
 */
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { Image } from '@tiptap/extension-image';
import { Mathematics, migrateMathStrings } from '@tiptap/extension-mathematics';
import 'katex/dist/katex.min.css';
import { useEffect } from 'react';
import { GraphExtension } from '@/components/exam-builder/extensions/GraphExtension';
import { resolveEditorContent } from '@/lib/plainTextWithMathToDoc';

interface RichContentViewerProps {
  content: string | object | null | undefined;
  className?: string;
}

export function RichContentViewer({ content, className }: RichContentViewerProps) {
  const editor = useEditor({
    editable: false,
    extensions: [
      StarterKit,
      Table,
      TableRow,
      TableHeader,
      TableCell,
      Image.configure({ allowBase64: true }),
      GraphExtension,
      Mathematics,
    ],
    content: resolveContent(content),
    immediatelyRender: false,
    onCreate: ({ editor }) => {
      migrateMathStrings(editor);
    },
  });

  // Update when content prop changes
  useEffect(() => {
    if (!editor) return;
    const resolved = resolveContent(content);
    editor.commands.setContent(resolved ?? '', false);
    migrateMathStrings(editor);
  }, [content, editor]);

  if (!content) return null;

  return (
    <div className={`prose prose-sm max-w-none ${className ?? ''}`}>
      <EditorContent editor={editor} />
    </div>
  );
}

const PLACEHOLDER_PREFIX = '[Question text could not be displayed';

/** Remove placeholder paragraphs from a TipTap doc node */
function stripPlaceholders(doc: any): any {
  if (!doc || typeof doc !== 'object') return doc;
  if (doc.type !== 'doc' || !Array.isArray(doc.content)) return doc;
  const filtered = doc.content.filter((node: any) => {
    if (node.type !== 'paragraph') return true;
    const text = (node.content ?? [])
      .filter((c: any) => c.type === 'text')
      .map((c: any) => c.text ?? '')
      .join('');
    return !text.startsWith(PLACEHOLDER_PREFIX);
  });
  return { ...doc, content: filtered };
}

/** Accepts TipTap JSON object, HTML string, or plain text string */
function resolveContent(content: string | object | null | undefined): object | string | null {
  if (!content) return null;
  if (typeof content === 'object') return stripPlaceholders(content); // TipTap JSON
  if (typeof content === 'string') {
    if (content.startsWith(PLACEHOLDER_PREFIX)) return null;
    return resolveEditorContent(content);
  }
  return null;
}
