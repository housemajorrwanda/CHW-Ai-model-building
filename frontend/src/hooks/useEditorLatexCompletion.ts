import { useState, useCallback, useRef } from 'react';
import type { Editor } from '@tiptap/core';
import { filterLatexCompletions } from '@/lib/latex-snippets';

export type EditorCompletionState = {
  from: number;
  fragment: string;
  completions: { trigger: string; snippet: string }[];
  selectedIndex: number;
};

export function useEditorLatexCompletion(editor: Editor | null) {
  const [state, setState] = useState<EditorCompletionState | null>(null);
  const stateRef = useRef(state);
  stateRef.current = state;

  const applyCurrent = useCallback(() => {
    const s = stateRef.current;
    if (!s || !editor) return;
    const snippet = s.completions[s.selectedIndex]?.snippet;
    if (!snippet) return;
    editor
      .chain()
      .focus()
      .deleteRange({ from: s.from - s.fragment.length, to: s.from })
      .insertContent(snippet)
      .run();
    setState(null);
  }, [editor]);

  const applySnippet = useCallback(
    (snippet: string) => {
      const s = stateRef.current;
      if (!s || !editor) return;
      editor
        .chain()
        .focus()
        .deleteRange({ from: s.from - s.fragment.length, to: s.from })
        .insertContent(snippet)
        .run();
      setState(null);
    },
    [editor]
  );

  const handleKeyDown = useCallback(
    (view: { state: { selection: { from: number; $from: { start: () => number } }; doc: { textBetween: (a: number, b: number) => string } } }, event: KeyboardEvent) => {
      const s = stateRef.current;
      if (s) {
        if (event.key === 'Escape') {
          setState(null);
          return true;
        }
        if (event.key === 'ArrowDown') {
          setState((prev) =>
            prev ? { ...prev, selectedIndex: (prev.selectedIndex + 1) % prev.completions.length } : null
          );
          return true;
        }
        if (event.key === 'ArrowUp') {
          setState((prev) =>
            prev ? { ...prev, selectedIndex: (prev.selectedIndex - 1 + prev.completions.length) % prev.completions.length } : null
          );
          return true;
        }
        if (event.key === 'Enter' || event.key === 'Tab') {
          applyCurrent();
          return true;
        }
      }

      const { state: pmState } = view;
      const from = pmState.selection.from;
      const $from = pmState.selection.$from;
      const blockStart = $from.start();
      const textBefore = pmState.doc.textBetween(blockStart, from);
      const match = textBefore.match(/\\([a-zA-Z]*)$/);
      if (match) {
        const fragment = '\\' + match[1];
        const list = filterLatexCompletions(fragment);
        if (list.length) setState({ from, fragment, completions: list, selectedIndex: 0 });
      } else {
        setState(null);
      }
      return false;
    },
    [applyCurrent]
  );

  return { completionState: state, handleKeyDown, apply: applyCurrent, applySnippet };
}
