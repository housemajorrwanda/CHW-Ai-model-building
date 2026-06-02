import { useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { X, ImagePlus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { attachmentsAPI } from '@/lib/api';
import type { Attachment } from './QuestionBuilder';
import { AttachmentImage } from '@/components/ui/AttachmentImage';

interface AttachmentsListProps {
  attachments: Attachment[];
  onUpdate: (attachments: Attachment[]) => void;
}

export function AttachmentsList({ attachments, onUpdate }: AttachmentsListProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const imageFiles = Array.from(files).filter((f) => f.type.startsWith('image/'));
    if (imageFiles.length === 0) {
      toast.error('Only image files are supported here.');
      return;
    }
    setUploading(true);
    try {
      const newAttachments: Attachment[] = [];
      for (const file of imageFiles) {
        const result = await attachmentsAPI.upload(file);
        newAttachments.push({
          id: result.id,
          attachmentType: 'image',
          filePath: result.filePath,
          filename: result.filename,
          mimeType: result.mimeType,
        });
      }
      onUpdate([...attachments, ...newAttachments]);
      toast.success(`${newAttachments.length} image${newAttachments.length > 1 ? 's' : ''} added`);
    } catch (e: any) {
      toast.error(e.message || 'Failed to upload image');
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const removeAttachment = (id: string) => {
    onUpdate(attachments.filter((a) => a.id !== id));
  };

  const imageAttachments = attachments.filter((a) => a.attachmentType === 'image');

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            Question Images
            {imageAttachments.length > 0 && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                ({imageAttachments.length})
              </span>
            )}
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <ImagePlus className="h-4 w-4 mr-2" />
            )}
            {uploading ? 'Uploading…' : 'Add Image'}
          </Button>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>
      </CardHeader>
      <CardContent>
        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
          onClick={() => imageAttachments.length === 0 && inputRef.current?.click()}
          className={`rounded-lg border-2 border-dashed transition-colors ${
            dragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
          } ${imageAttachments.length === 0 ? 'cursor-pointer hover:border-primary/50 hover:bg-muted/30' : ''}`}
        >
          {imageAttachments.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <ImagePlus className="h-8 w-8 text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">
                Drag & drop images here, or click <strong>Add Image</strong>
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Images will appear on the question for students
              </p>
            </div>
          ) : (
            <div className="p-3 grid grid-cols-2 gap-3">
              {imageAttachments.map((att) => (
                <div key={att.id} className="relative group rounded-lg overflow-hidden border bg-muted/20">
                  <AttachmentImage
                    filePath={att.filePath}
                    alt={att.filename}
                    className="w-full object-contain max-h-48"
                  />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
                  <Button
                    variant="destructive"
                    size="icon"
                    className="absolute top-1 right-1 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => { e.stopPropagation(); removeAttachment(att.id); }}
                    title="Remove image"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                  <p className="px-2 py-1 text-xs text-muted-foreground truncate border-t bg-background">
                    {att.filename}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

