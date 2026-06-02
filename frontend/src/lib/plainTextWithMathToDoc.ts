/**
 * Convert plain OCR text with $...$ / $$...$$ into TipTap JSON for RichContentViewer.
 */
type TipTapNode = { type: string; text?: string; attrs?: Record<string, string>; content?: TipTapNode[] };

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
  const s = text.trim();
  const content: TipTapNode[] = [];
  let pos = 0;

  while (pos < s.length) {
    const blockStart = s.indexOf('$$', pos);
    if (blockStart === -1) {
      const tail = s.slice(pos).trim();
      if (tail) content.push(...paragraphsFromPlain(tail));
      break;
    }
    if (blockStart > pos) {
      const prefix = s.slice(pos, blockStart).trim();
      if (prefix) content.push(...paragraphsFromPlain(prefix));
    }
    const blockEnd = s.indexOf('$$', blockStart + 2);
    if (blockEnd === -1) {
      content.push(...paragraphsFromPlain(s.slice(blockStart).trim()));
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
  return /\$\$[\s\S]*?\$\$|\$[^$\n]+?\$/.test(text) || /\\begin\{|\\frac|\\prime/.test(text);
}
