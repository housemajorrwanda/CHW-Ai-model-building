import { useRef, useState, useCallback, useMemo } from 'react';
import { filterLatexCompletions } from '@/lib/latex-snippets';
import { cn } from '@/lib/utils';

function findBackslashPos(text: string, cursor: number): number {
  for (let i = cursor - 1; i >= 0; i--) {
    if (text[i] === '\\') return i;
    if (/[\s{}\\]/.test(text[i])) return -1;
  }
  return -1;
}

function placeCursorInFirstBraces(
  el: HTMLInputElement | HTMLTextAreaElement | null,
  insertStart: number,
  snippet: string
) {
  if (!el) return;
  const idx = snippet.indexOf('{}');
  if (idx === -1) {
    el.setSelectionRange(insertStart + snippet.length, insertStart + snippet.length);
    return;
  }
  const pos = insertStart + idx + 1;
  el.setSelectionRange(pos, pos);
}

export function useLatexAutocomplete(
  value: string,
  setValue: (v: string) => void
) {
  const ref = useRef<HTMLInputElement | HTMLTextAreaElement>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [cursorPos, setCursorPos] = useState(0);

  const { backslashPos, completions } = useMemo(() => {
    const cursor = cursorPos;
    const text = value;
    const bs = findBackslashPos(text, cursor);
    if (bs === -1) return { backslashPos: -1, completions: [] };
    const frag = text.slice(bs, cursor);
    const list = filterLatexCompletions(frag);
    return { backslashPos: bs, completions: list };
  }, [value, cursorPos]);

  const showList = completions.length > 0;

  const apply = useCallback(
    (snippet: string) => {
      const el = ref.current;
      if (!el || backslashPos < 0) return;
      const end = el.selectionEnd ?? backslashPos;
      const before = value.slice(0, backslashPos);
      const after = value.slice(end);
      const next = before + snippet + after;
      setValue(next);
      setSelectedIndex(0);
      requestAnimationFrame(() => placeCursorInFirstBraces(el, backslashPos, snippet));
    },
    [backslashPos, value, setValue]
  );

  const dismiss = useCallback(() => setSelectedIndex(0), []);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!showList) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((i) => (i + 1) % completions.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((i) => (i - 1 + completions.length) % completions.length);
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        apply(completions[selectedIndex].snippet);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        dismiss();
      }
    },
    [showList, completions, selectedIndex, apply, dismiss]
  );

  const onChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const el = e.target;
      setValue(el.value);
      setCursorPos(el.selectionStart ?? 0);
      setSelectedIndex(0);
    },
    [setValue]
  );

  return {
    ref,
    value,
    onChange,
    onKeyDown,
    completions,
    selectedIndex,
    showList,
    apply,
    dismiss,
  };
}

interface LatexCompletionsListProps {
  completions: { trigger: string; snippet: string }[];
  selectedIndex: number;
  onSelect: (snippet: string) => void;
  className?: string;
}

export function LatexCompletionsList({
  completions,
  selectedIndex,
  onSelect,
  className,
}: LatexCompletionsListProps) {
  if (completions.length === 0) return null;
  return (
    <ul
      className={cn(
        'absolute z-50 mt-0.5 w-full rounded-md border bg-popover py-1 text-popover-foreground shadow-md',
        'max-h-56 overflow-auto',
        className
      )}
      role="listbox"
    >
      {completions.map((item, i) => (
        <li
          key={item.trigger}
          role="option"
          aria-selected={i === selectedIndex}
          className={cn(
            'cursor-pointer px-3 py-1.5 text-sm font-mono',
            i === selectedIndex ? 'bg-accent' : 'hover:bg-muted/70'
          )}
          onMouseDown={(e) => {
            e.preventDefault();
            onSelect(item.snippet);
          }}
        >
          {item.trigger}
        </li>
      ))}
    </ul>
  );
}

/** In-editor completion list positioned at the caret. Use with useEditorLatexCompletion. */
export function EditorLatexCompletionsList({
  editor,
  state,
  onSelect,
}: {
  editor: { view: { coordsAtPos: (pos: number) => { top: number; left: number; bottom: number } } } | null;
  state: { from: number; completions: { trigger: string; snippet: string }[]; selectedIndex: number } | null;
  onSelect: (snippet: string) => void;
}) {
  if (!state || !editor?.view || state.completions.length === 0) return null;
  const rect = editor.view.coordsAtPos(state.from);
  return (
    <ul
      className="fixed z-[100] max-h-52 w-48 overflow-auto rounded-md border bg-popover py-1 shadow-lg"
      role="listbox"
      style={{ top: rect.bottom + 4, left: rect.left }}
    >
      {state.completions.map((item, i) => (
        <li
          key={item.trigger}
          role="option"
          aria-selected={i === state.selectedIndex}
          className={cn(
            'cursor-pointer px-3 py-1.5 text-sm font-mono',
            i === state.selectedIndex ? 'bg-accent' : 'hover:bg-muted/70'
          )}
          onMouseDown={(e) => {
            e.preventDefault();
            onSelect(item.snippet);
          }}
        >
          {item.trigger}
        </li>
      ))}
    </ul>
  );
}
