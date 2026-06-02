const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const ORIGIN = API_BASE_URL.replace(/\/api\/?$/, '');

export function resolveAttachmentUrl(filePath: string): string {
  if (!filePath) return '';
  if (filePath.startsWith('http') || filePath.startsWith('blob:') || filePath.startsWith('data:')) {
    return filePath;
  }
  return `${ORIGIN}${filePath}`;
}

/** Load attachment bytes with JWT when needed (plain <img> cannot send Authorization). */
export async function loadAuthenticatedAttachmentUrl(filePath: string): Promise<string> {
  const url = resolveAttachmentUrl(filePath);
  if (!url || !filePath.includes('/api/attachments/')) {
    return url;
  }

  const token = localStorage.getItem('auth_token');
  if (!token) {
    return url;
  }

  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    return url;
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
