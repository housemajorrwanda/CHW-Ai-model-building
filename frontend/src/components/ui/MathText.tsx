/**
 * Renders a plain string that may contain $...$ (inline) or $$...$$ (block) LaTeX.
 * Non-math segments are rendered as plain text.
 */
import { useEffect, useRef } from 'react';

interface MathTextProps {
  text: string;
  className?: string;
}

interface Segment {
  type: 'text' | 'inline' | 'block';
  content: string;
}

function parseSegments(text: string): Segment[] {
  const segments: Segment[] = [];
  // Match $$...$$ first, then $...$
  const re = /(\$\$[\s\S]*?\$\$|\$[^$\n]*?\$)/g;
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = re.exec(text)) !== null) {
    if (match.index > last) {
      segments.push({ type: 'text', content: text.slice(last, match.index) });
    }
    const raw = match[0];
    if (raw.startsWith('$$')) {
      segments.push({ type: 'block', content: raw.slice(2, -2) });
    } else {
      segments.push({ type: 'inline', content: raw.slice(1, -1) });
    }
    last = match.index + raw.length;
  }

  if (last < text.length) {
    segments.push({ type: 'text', content: text.slice(last) });
  }

  return segments;
}

function KatexSpan({ latex, display }: { latex: string; display: boolean }) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    import('katex').then((m) => {
      try {
        m.default.render(latex, ref.current!, {
          throwOnError: false,
          displayMode: display,
        });
      } catch {
        if (ref.current) ref.current.textContent = latex;
      }
    });
  }, [latex, display]);

  return display
    ? <span ref={ref} className="block text-center my-1" />
    : <span ref={ref} />;
}

export function MathText({ text, className }: MathTextProps) {
  if (!text) return null;

  const segments = parseSegments(text);

  return (
    <span className={className}>
      {segments.map((seg, i) => {
        if (seg.type === 'text') return <span key={i}>{seg.content}</span>;
        return <KatexSpan key={i} latex={seg.content} display={seg.type === 'block'} />;
      })}
    </span>
  );
}
