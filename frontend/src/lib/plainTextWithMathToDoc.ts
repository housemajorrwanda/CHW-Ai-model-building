/**
 * Convert plain OCR text with $...$ / $$...$$ into TipTap JSON for RichContentViewer / AnswerEditor.
 */
type TipTapNode = { type: string; text?: string; attrs?: Record<string, string>; content?: TipTapNode[] };

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function looksLikeTipTapHtml(content: string): boolean {
  const t = (content || '').trim();
  return (
    t.startsWith('<') ||
    /data-latex\s*=|data-type\s*=\s*"(?:inline|block)-math"/.test(t)
  );
}

/** Normalize OCR / Mathpix delimiters to $...$ / $$...$$ for TipTap math migration. */
export function normalizeMathDelimiters(text: string): string {
  return text
    .replace(/\\\(([\s\S]*?)\\\)/g, (_: string, m: string) => `$${m.trim()}$`)
    .replace(/\\\[([\s\S]*?)\\\]/g, (_: string, m: string) => `$$${m.trim()}$$`);
}

function inlineNodesFromLine(line: string): TipTapNode[] {
  const nodes: TipTapNode[] = [];
  const re = /\$([^$\n]+?)\$/g;
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = re.exec(line)) !== null) {
    if (match.index > last) {
      nodes.push({ type: 'text', text: line.slice(last, match.index) });
    }
    const latex = match[1].trim();
    if (latex) nodes.push({ type: 'inlineMath', attrs: { latex } });
    last = match.index + match[0].length;
  }

  if (last < line.length) {
    nodes.push({ type: 'text', text: line.slice(last) });
  }
  return nodes;
}

function paragraphsFromPlain(text: string): TipTapNode[] {
  const out: TipTapNode[] = [];
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line) continue;
    const nodes = inlineNodesFromLine(line);
    if (nodes.length) out.push({ type: 'paragraph', content: nodes });
  }
  return out;
}

export function plainTextWithMathToDoc(text: string): { type: 'doc'; content: TipTapNode[] } {
  let s = normalizeMathDelimiters(text.trim());
  // Close unclosed block delimiters from OCR
  if ((s.match(/\$\$/g) || []).length % 2 === 1) {
    s = `${s}\n$$`;
  }
  const content: TipTapNode[] = [];
  let pos = 0;

  while (pos < s.length) {
    const blockStart = s.indexOf('$$', pos);
    if (blockStart === -1) {
      const tail = s.slice(pos).trim();
      if (tail) {
        if (plainTextLooksLikeMath(tail) && !tail.includes('$$')) {
          content.push({ type: 'blockMath', attrs: { latex: tail.replace(/^\$+|\$+$/g, '') } });
        } else {
          content.push(...paragraphsFromPlain(tail));
        }
      }
      break;
    }
    if (blockStart > pos) {
      const prefix = s.slice(pos, blockStart).trim();
      if (prefix) content.push(...paragraphsFromPlain(prefix));
    }
    const blockEnd = s.indexOf('$$', blockStart + 2);
    if (blockEnd === -1) {
      const latex = s.slice(blockStart + 2).trim();
      if (latex) content.push({ type: 'blockMath', attrs: { latex } });
      break;
    }
    const latex = s.slice(blockStart + 2, blockEnd).trim();
    if (latex) content.push({ type: 'blockMath', attrs: { latex } });
    pos = blockEnd + 2;
  }

  if (!content.length) {
    content.push({ type: 'paragraph', content: [{ type: 'text', text: s.slice(0, 10000) }] });
  }

  return { type: 'doc', content };
}

export function plainTextLooksLikeMath(text: string): boolean {
  const t = normalizeMathDelimiters(text);
  return (
    /\$\$[\s\S]*?\$\$|\$[^$\n]+?\$/.test(t) ||
    /\\begin\{|\\frac|\\prime|\\left|\\sqrt|\\sum|\\int/.test(t) ||
    /\\\([\s\S]*?\\\)/.test(text) ||
    /\\\[[\s\S]*?\\\]/.test(text)
  );
}

/** Plain text (no HTML) → simple paragraph HTML for TipTap. */
export function plainTextToSimpleHtml(text: string): string {
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  if (!lines.length) return '';
  return lines.map((l) => `<p>${escapeHtml(l)}</p>`).join('');
}

/** Resolve stored answer / OCR excerpt into TipTap HTML or JSON doc. */
export function resolveEditorContent(content: string): string | { type: 'doc'; content: TipTapNode[] } {
  const raw = (content || '').trim();
  if (!raw) return '';
  if (raw.startsWith('<')) return raw;
  const normalized = normalizeMathDelimiters(raw);
  if (plainTextLooksLikeMath(normalized)) {
    return plainTextWithMathToDoc(normalized);
  }
  return plainTextToSimpleHtml(normalized);
}
