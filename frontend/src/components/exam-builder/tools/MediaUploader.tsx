import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Upload, Image, Scan, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { attachmentsAPI } from '@/lib/api';

interface MediaUploaderProps {
  onImageUpload: (url: string) => void;
  onAttachmentAdd: (attachment: any) => void;
}

export function MediaUploader({ onImageUpload, onAttachmentAdd }: MediaUploaderProps) {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploadedFiles(acceptedFiles);
    setUploading(true);
    
    try {
      // Upload each file to backend
      for (const file of acceptedFiles) {
        try {
          const attachment = await attachmentsAPI.upload(file);
          
          // Get the full URL for display
          const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
          const fullUrl = apiBaseUrl.replace(/\/api\/?$/, '') + attachment.filePath;
          
          if (file.type.startsWith('image/')) {
            onImageUpload(fullUrl);
          }
          
          onAttachmentAdd({
            id: attachment.id,
            attachmentType: attachment.attachmentType,
            filePath: attachment.filePath,
            filename: attachment.filename,
            fileSize: attachment.fileSize,
            mimeType: attachment.mimeType,
          });
          
          toast.success(`Uploaded: ${file.name}`);
        } catch (error: any) {
          toast.error(`Failed to upload ${file.name}: ${error.message}`);
        }
      }
    } finally {
      setUploading(false);
    }
  }, [onImageUpload, onAttachmentAdd]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
      'application/pdf': ['.pdf'],
    },
  });

  return (
    <Tabs defaultValue="upload" className="w-full">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="upload">
          <Upload className="h-4 w-4 mr-2" />
          Upload
        </TabsTrigger>
        <TabsTrigger value="photo">
          <Image className="h-4 w-4 mr-2" />
          Photo
        </TabsTrigger>
        <TabsTrigger value="scan">
          <Scan className="h-4 w-4 mr-2" />
          Scan
        </TabsTrigger>
      </TabsList>

      <TabsContent value="upload" className="space-y-4">
        <div
          {...getRootProps()}
          className={cn(
            'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
            (isDragActive || uploading) ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50',
            uploading && 'opacity-50 cursor-wait'
          )}
        >
          <input {...getInputProps()} disabled={uploading} />
          <Upload className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
          <p className="text-sm font-medium mb-1">
            {uploading ? 'Uploading...' : isDragActive ? 'Drop files here' : 'Drag & drop files here'}
          </p>
          <p className="text-xs text-muted-foreground">
            {uploading ? 'Please wait...' : 'Click to browse (Images, PDFs)'}
          </p>
        </div>
      </TabsContent>

      <TabsContent value="photo" className="space-y-4">
        <div className="text-center p-6 border rounded-lg">
          <Image className="h-12 w-12 mx-auto mb-3 text-muted-foreground" />
          <p className="text-sm mb-3">Capture photo directly</p>
          <Button variant="outline" size="sm">
            <Image className="h-4 w-4 mr-2" />
            Open Camera
          </Button>
          <p className="text-xs text-muted-foreground mt-3">
            (Camera access required)
          </p>
        </div>
      </TabsContent>

      <TabsContent value="scan" className="space-y-4">
        <div className="text-center p-6 border rounded-lg">
          <Scan className="h-12 w-12 mx-auto mb-3 text-muted-foreground" />
          <p className="text-sm mb-3">Scan document</p>
          <Button variant="outline" size="sm">
            <Scan className="h-4 w-4 mr-2" />
            Start Scan
          </Button>
          <p className="text-xs text-muted-foreground mt-3">
            (Scanner required)
          </p>
        </div>
      </TabsContent>
    </Tabs>
  );
}

