import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Upload, Image, Scan, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface MediaUploaderProps {
  onImageUpload: (url: string) => void;
  onAttachmentAdd: (attachment: any) => void;
}

export function MediaUploader({ onImageUpload, onAttachmentAdd }: MediaUploaderProps) {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setUploadedFiles(acceptedFiles);
    
    // For demo, create object URLs
    acceptedFiles.forEach((file) => {
      const url = URL.createObjectURL(file);
      
      if (file.type.startsWith('image/')) {
        onImageUpload(url);
      }
      
      onAttachmentAdd({
        id: crypto.randomUUID(),
        attachmentType: file.type.startsWith('image/') ? 'image' : 'document',
        filePath: url,
        filename: file.name,
        fileSize: file.size,
        mimeType: file.type,
      });
      
      toast.success(`Uploaded: ${file.name}`);
    });
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
            isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
          )}
        >
          <input {...getInputProps()} />
          <Upload className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
          <p className="text-sm font-medium mb-1">
            {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
          </p>
          <p className="text-xs text-muted-foreground">
            or click to browse (Images, PDFs)
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

