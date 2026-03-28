import { useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import type { MathfieldElement } from 'mathlive';
import 'mathlive/static.css';

export type VisualMathFieldHandle = {
  /** Insert a LaTeX fragment at the cursor (placeholders become active like Word equation editor). */
  insert: (latex: string) => boolean;
  focus: () => void;
  getLatex: () => string;
};

type Props = {
  value: string;
  onChange: (latex: string) => void;
  className?: string;
};

/**
 * Word-like visual math editor (MathLive). Outputs LaTeX for KaTeX / TipTap mathematics.
 */
export const VisualMathField = forwardRef<VisualMathFieldHandle, Props>(function VisualMathField(
  { value, onChange, className },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mfRef = useRef<MathfieldElement | null>(null);
  const onChangeRef = useRef(onChange);
  const valueRef = useRef(value);
  onChangeRef.current = onChange;
  valueRef.current = value;

  useImperativeHandle(ref, () => ({
    insert: (latexSnippet: string) => {
      const mf = mfRef.current;
      if (!mf) return false;
      const before = mf.getValue('latex');
      mf.focus();
      const opts = { format: 'latex' as const, selectionMode: 'placeholder' as const, focus: true };
      let after = before;
      let ok = mf.insert(latexSnippet, opts);
      after = mf.getValue('latex');
      if (after === before) {
        mf.executeCommand(['insert', latexSnippet, opts]);
        after = mf.getValue('latex');
        ok = ok || after !== before;
      }
      queueMicrotask(() => onChangeRef.current(after));
      return ok || after !== before;
    },
    focus: () => {
      mfRef.current?.focus();
    },
    getLatex: () => mfRef.current?.getValue('latex') ?? '',
  }));

  useEffect(() => {
    let disposed = false;
    let mf: MathfieldElement | undefined;

    import('mathlive')
      .then(({ MathfieldElement }) => {
        if (disposed || !containerRef.current) return;
        mf = new MathfieldElement();
        mf.style.width = '100%';
        mf.style.minHeight = '140px';
        mf.style.padding = '0.75rem 1rem';
        mf.style.borderRadius = '0.5rem';
        mf.style.border = '1px solid hsl(var(--border))';
        mf.style.background = 'hsl(var(--background))';
        mf.style.fontSize = '1.25rem';
        mf.defaultMode = 'math';
        mf.smartFence = true;
        mf.smartSuperscript = true;
        mf.mathVirtualKeyboardPolicy = 'auto';
        // Avoid stale closure: MathLive loads async; parent state may already include toolbar inserts.
        mf.value = valueRef.current;
        mf.addEventListener('input', () => onChangeRef.current(mf!.getValue('latex')));
        /** Plain-text LaTeX from clipboard (Overleaf, docs, ChatGPT) — default paste loses backslashes. */
        mf.addEventListener('paste', (ev: Event) => {
          const e = ev as ClipboardEvent;
          const plain = e.clipboardData?.getData('text/plain') ?? '';
          if (!plain.trim() || plain.length > 16_000) return;
          if (!plain.includes('\\') || !/\\[a-zA-Z]+/.test(plain)) return;
          e.preventDefault();
          e.stopPropagation();
          mf!.insert(plain.trim(), { format: 'latex', selectionMode: 'after', focus: true });
          queueMicrotask(() => onChangeRef.current(mf!.getValue('latex')));
        });
        containerRef.current.appendChild(mf);
        mfRef.current = mf;
      })
      .catch(() => {
        /* mathlive failed to load */
      });

    return () => {
      disposed = true;
      mfRef.current = null;
      mf?.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount once; value sync handled below
  }, []);

  // Keep in sync when parent updates `value` (e.g. Templates tab, dialog reopen, switch from LaTeX tab)
  useEffect(() => {
    const mf = mfRef.current;
    if (!mf) return;
    const cur = mf.getValue('latex');
    if (cur !== value) {
      mf.value = value;
    }
  }, [value]);

  return <div ref={containerRef} className={className} />;
});
