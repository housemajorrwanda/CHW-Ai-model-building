import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { loadAuthenticatedAttachmentUrl, resolveAttachmentUrl } from '@/lib/attachmentUrl';

interface AttachmentImageProps {
  filePath: string;
  alt: string;
  className?: string;
}

export function AttachmentImage({ filePath, alt, className }: AttachmentImageProps) {
  const [src, setSrc] = useState(() => resolveAttachmentUrl(filePath));

  useEffect(() => {
    let blobUrl: string | null = null;
    let cancelled = false;

    setSrc(resolveAttachmentUrl(filePath));

    loadAuthenticatedAttachmentUrl(filePath)
      .then((loaded) => {
        if (cancelled) {
          if (loaded.startsWith('blob:')) URL.revokeObjectURL(loaded);
          return;
        }
        if (loaded.startsWith('blob:')) {
          blobUrl = loaded;
        }
        setSrc(loaded);
      })
      .catch(() => {
        if (!cancelled) {
          setSrc(resolveAttachmentUrl(filePath));
        }
      });

    return () => {
      cancelled = true;
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [filePath]);

  if (!src) return null;

  return <img src={src} alt={alt} className={cn(className)} />;
}
