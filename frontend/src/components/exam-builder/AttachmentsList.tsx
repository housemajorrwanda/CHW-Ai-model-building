import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { X, FileText, Image, Scan } from 'lucide-react';
import type { Attachment } from './QuestionBuilder';

interface AttachmentsListProps {
  attachments: Attachment[];
  onUpdate: (attachments: Attachment[]) => void;
}

export function AttachmentsList({ attachments, onUpdate }: AttachmentsListProps) {
  const removeAttachment = (id: string) => {
    onUpdate(attachments.filter((a) => a.id !== id));
  };

  if (attachments.length === 0) return null;

  const getIcon = (type: string) => {
    switch (type) {
      case 'image':
        return <Image className="h-4 w-4" />;
      case 'scan':
        return <Scan className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Attachments ({attachments.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {attachments.map((attachment) => (
            <div
              key={attachment.id}
              className="flex items-center justify-between p-2 border rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                {getIcon(attachment.attachmentType)}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{attachment.filename}</p>
                  {attachment.fileSize && (
                    <p className="text-xs text-muted-foreground">
                      {(attachment.fileSize / 1024).toFixed(1)} KB
                    </p>
                  )}
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-destructive hover:text-destructive"
                onClick={() => removeAttachment(attachment.id)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

