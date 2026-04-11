export const GENDER_OPTIONS = [
  { value: '_none', label: 'Prefer not to say' },
  { value: 'woman', label: 'Woman' },
  { value: 'man', label: 'Man' },
  { value: 'non_binary', label: 'Non-binary' },
  { value: 'other', label: 'Other' },
] as const;

export function labelForGender(code: string | undefined): string {
  if (!code) return '—';
  const row = GENDER_OPTIONS.find((o) => o.value === code);
  return row?.label ?? code;
}
