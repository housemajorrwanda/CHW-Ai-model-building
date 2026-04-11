/** Backend serves `/uploads/...` from the API host (not under `/api`). */
export function getApiOrigin(): string {
  const raw = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
  return raw.replace(/\/api\/?$/i, '');
}

export function resolveAvatarUrl(avatar: string | undefined): string | undefined {
  if (!avatar) return undefined;
  const a = avatar.trim();
  if (!a) return undefined;
  if (a.startsWith('http://') || a.startsWith('https://')) return a;
  const origin = getApiOrigin();
  if (a.startsWith('/')) return `${origin}${a}`;
  return `${origin}/${a}`;
}
