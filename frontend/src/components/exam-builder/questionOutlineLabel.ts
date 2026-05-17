import type { Question } from './QuestionBuilder';

const COLLAPSE = /\s+/g;

export type OutlineLabelFields = Pick<Question, 'outlineTitle' | 'text'>;

/** Label shown in the outline sidebar: custom title, else shortened plain text, else placeholder. */
export function questionOutlineLabel(question: OutlineLabelFields, maxLen = 52): string {
  const custom = (question.outlineTitle || '').trim();
  if (custom) {
    return custom.length > maxLen ? `${custom.slice(0, maxLen - 1)}…` : custom;
  }
  const plain = (question.text || '').trim().replace(COLLAPSE, ' ');
  if (plain) {
    return plain.length > maxLen ? `${plain.slice(0, maxLen - 1)}…` : plain;
  }
  return '(Untitled)';
}
