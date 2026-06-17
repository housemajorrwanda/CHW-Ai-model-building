import { Fragment, useMemo, type ReactNode } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import { cn } from '@/lib/utils';

function stripMathDelimiters(s: string): string {
  let t = s.trim();
  if (t.startsWith('$$') && t.endsWith('$$')) return t.slice(2, -2).trim();
  if (t.startsWith('$') && t.endsWith('$')) return t.slice(1, -1).trim();
  return t;
}

/** Clean OCR / HTML noise before KaTeX. */
export function normalizeStepLatexInput(s: string): string {
  let t = s
    .replace(/<\s*br\s*\/?>/gi, ' ')
    .replace(/<[^>]+>/g, '')
    .replace(/^\{\s*\d+\s*\}\s*/, '')
    .trim();
  t = t.replace(/(^|\s)l\s*\(/gi, '$1\\left(');
  t = t.replace(/\)\s*\$\s*(?=[a-zA-Z(])/g, ') ');
  t = t.replace(/\(\s*(\d+)\s*\$\s*(points?|pts?)\s*\$/gi, '($1 \\text{ $2 })');
  t = t.replace(/\\left/g, '\x00LEFT\x00');
  t = t.replace(/\\right/g, '\x00RIGHT\x00');
  t = t.replace(/\\frac/g, '\x00FRAC\x00');
  t = t.replace(/\s*\^\s*\{\s*/g, '^{');
  t = t.replace(/\s+\}/g, '}');
  t = t.replace(/\(\s+/g, '(');
  t = t.replace(/\s+\)/g, ')');
  t = t.replace(/\x00LEFT\x00/g, '\\left');
  t = t.replace(/\x00RIGHT\x00/g, '\\right');
  t = t.replace(/\x00FRAC\x00/g, '\\frac');
  t = t.replace(/\\left\s*\(\s*/g, '\\left(');
  t = t.replace(/\s*\\right\s*\)/g, '\\right)');
  return t.replace(/\s+/g, ' ').trim();
}

export function looksLikeLatex(s: string): boolean {
  const t = normalizeStepLatexInput(s);
  if (!t) return false;
  return (
    /\\[a-zA-Z]+/.test(t) ||
    /\$[^$]+\$/.test(t) ||
    (/\d/.test(t) && /[\^+\-*/=()]/.test(t)) ||
    (t.includes('^') && /[a-zA-Z0-9]/.test(t))
  );
}

/** Plain numeric / short math phrase → inline LaTeX when possible. */
function plainToInlineLatex(s: string): string | null {
  const t = s.trim();
  if (!t) return null;
  if (looksLikeLatex(t)) return normalizeStepLatexInput(t);
  if (/^-?\d+(\.\d+)?$/.test(t)) return t;
  if (/^\d+\s*\(\s*\d+\s*points?\s*\)$/i.test(t)) {
    const m = t.match(/^(\d+)\s*\(\s*(\d+)\s*points?\s*\)$/i);
    if (m) return `${m[1]} \\text{ (${m[2]} points)}`;
  }
  return null;
}

type Segment = { kind: 'math' | 'text'; value: string };

function splitLatexPrefixFromProse(cleaned: string): Segment[] | null {
  const rightClose = cleaned.match(/^(.*\\right\))\s*(.+)$/);
  if (rightClose) {
    const mathPart = rightClose[1].trim();
    const prose = rightClose[2].trim();
    if (looksLikeLatex(mathPart) && prose) {
      return [
        { kind: 'math', value: mathPart },
        { kind: 'text', value: prose },
      ];
    }
  }

  const colonSplit = cleaned.match(/^(\$\$?.+?\$\$?|\\[a-zA-Z].+?)\s*:\s*(.+)$/);
  if (colonSplit) {
    const head = colonSplit[1].trim();
    const tail = colonSplit[2].trim();
    if (looksLikeLatex(head) && tail) {
      return [
        { kind: 'math', value: stripMathDelimiters(head) },
        { kind: 'text', value: `: ${tail}` },
      ];
    }
  }

  return null;
}

function splitDollarDelimitedMath(cleaned: string): Segment[] | null {
  const segments: Segment[] = [];
  const re = /\$\$([^$]+)\$\$|\$([^$]+)\$/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let found = false;

  while ((match = re.exec(cleaned)) !== null) {
    found = true;
    if (match.index > last) {
      const between = cleaned.slice(last, match.index).trim();
      if (between) segments.push({ kind: 'text', value: between });
    }
    const latex = (match[1] ?? match[2] ?? '').trim();
    if (latex) segments.push({ kind: 'math', value: latex });
    last = match.index + match[0].length;
  }

  if (!found) return null;

  const tail = cleaned.slice(last).trim();
  if (tail) segments.push({ kind: 'text', value: tail });
  return segments;
}

export function splitMixedMathContent(raw: string): Segment[] {
  const cleaned = normalizeStepLatexInput(raw);
  if (!cleaned) return [];

  const dollarSegments = splitDollarDelimitedMath(cleaned);
  if (dollarSegments?.length) return dollarSegments;

  const prefixSegments = splitLatexPrefixFromProse(cleaned);
  if (prefixSegments?.length) return prefixSegments;

  if (looksLikeLatex(cleaned)) {
    return [{ kind: 'math', value: cleaned }];
  }

  const asLatex = plainToInlineLatex(cleaned);
  if (asLatex) return [{ kind: 'math', value: asLatex }];

  return [{ kind: 'text', value: cleaned }];
}

function RenderedLatex({ latex, displayMode }: { latex: string; displayMode?: boolean }) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(stripMathDelimiters(latex), {
        throwOnError: false,
        displayMode: displayMode !== false,
        strict: false,
      });
    } catch {
      return '';
    }
  }, [latex, displayMode]);
  if (!html) return null;
  return (
    <span
      className={cn(
        displayMode === false
          ? 'inline-block align-middle [&_.katex]:text-[0.95rem]'
          : 'block overflow-x-auto [&_.katex]:text-[0.95rem]'
      )}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

/** Render prose with standalone numbers as inline KaTeX. */
function TextWithInlineNumbers({ text }: { text: string }) {
  const parts = text.split(/(\d+(?:\.\d+)?)/g).filter((p) => p.length > 0);
  if (parts.length === 1) {
    return <span className="break-words">{text}</span>;
  }
  return (
    <span className="break-words">
      {parts.map((part, i) =>
        /^\d+(?:\.\d+)?$/.test(part) ? (
          <RenderedLatex key={i} latex={part} displayMode={false} />
        ) : (
          <Fragment key={i}>{part}</Fragment>
        )
      )}
    </span>
  );
}

function renderSegment(seg: Segment, i: number, displayMode: boolean): ReactNode {
  if (seg.kind === 'math') {
    return <RenderedLatex key={i} latex={seg.value} displayMode={displayMode} />;
  }
  const inline = plainToInlineLatex(seg.value);
  if (inline) {
    return <RenderedLatex key={i} latex={inline} displayMode={false} />;
  }
  return <TextWithInlineNumbers key={i} text={seg.value} />;
}

/** Renders strings that may mix LaTeX, $...$, and short plain text. */
export function MixedMathContent({
  text,
  displayMode = false,
  className,
}: {
  text?: string | null;
  displayMode?: boolean;
  className?: string;
}) {
  const raw = (text || '').trim();
  if (!raw || raw === '—') return <span>—</span>;

  const lines = raw.split(/<\s*br\s*\/?>|\n/gi).map((l) => l.trim()).filter(Boolean);
  const rows = (lines.length > 1 ? lines : [raw]).map((line) => splitMixedMathContent(line));

  if (!rows.some((r) => r.length)) return <span>—</span>;

  const Wrapper = displayMode === false ? 'span' : 'div';

  return (
    <Wrapper className={cn(displayMode === false ? 'inline leading-relaxed' : 'space-y-2 leading-relaxed', className)}>
      {rows.map((segments, rowIdx) => (
        <span
          key={rowIdx}
          className={cn(
            displayMode === false ? 'inline' : 'block',
            rowIdx > 0 && 'mt-1.5 block'
          )}
        >
          {segments.map((seg, i) => renderSegment(seg, rowIdx * 100 + i, displayMode))}
        </span>
      ))}
    </Wrapper>
  );
}

/** Renders rubric step expected/received text with KaTeX when LaTeX is detected. */
export function StepMathContent({
  text,
  displayMode = false,
}: {
  text?: string | null;
  displayMode?: boolean;
}) {
  return <MixedMathContent text={text} displayMode={displayMode} />;
}
