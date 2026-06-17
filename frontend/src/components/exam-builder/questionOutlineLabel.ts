import type { Question } from './QuestionBuilder';

const COLLAPSE = /\s+/g;

export type OutlineLabelFields = Pick<Question, 'outlineTitle' | 'text'>;

/** Strip LaTeX noise for sidebar previews (OCR often returns raw \\begin{array}…). */
function readablePreview(raw: string, maxLen: number): string {
  let s = raw.trim();
  if (!s) return '';
  s = s.replace(/\$\$/g, ' ').replace(/\$/g, ' ');
  s = s.replace(/\\begin\{[^}]+\}/gi, ' ').replace(/\\end\{[^}]+\}/gi, ' ');
  s = s.replace(/\\[a-zA-Z]+\s*/g, ' ');
  s = s.replace(/\\\\/g, ' ');
  s = s.replace(/[{}]/g, ' ');
  s = s.replace(COLLAPSE, ' ').trim();
  if (s.length > maxLen) return `${s.slice(0, maxLen - 1)}…`;
  return s;
}

/** Label shown in the outline sidebar: custom title, else shortened plain text, else placeholder. */
export function questionOutlineLabel(question: OutlineLabelFields, maxLen = 52): string {
  const custom = (question.outlineTitle || '').trim();
  if (custom) {
    return custom.length > maxLen ? `${custom.slice(0, maxLen - 1)}…` : custom;
  }
  const plain = (question.text || '').trim().replace(COLLAPSE, ' ');
  if (plain) {
    const looksLikeLatex =
      /\$\$[\s\S]*?\$\$|\$[^$\n]+?\$/.test(plain) ||
      /\\begin\{|\\frac|\\left|\\right/.test(plain);
    if (looksLikeLatex) {
      const preview = readablePreview(plain, maxLen);
      if (preview) return preview;
    }
    return plain.length > maxLen ? `${plain.slice(0, maxLen - 1)}…` : plain;
  }
  return '(Untitled)';
}
