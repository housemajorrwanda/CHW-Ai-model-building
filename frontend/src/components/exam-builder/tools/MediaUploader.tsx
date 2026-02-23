import { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Upload, Image, Camera } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { attachmentsAPI } from '@/lib/api';

interface MediaUploaderProps {
  onImageUpload: (url: string) => void;
  onAttachmentAdd: (attachment: any) => void;
}

export function MediaUploader({ onImageUpload, onAttachmentAdd }: MediaUploaderProps) {
  const [uploading, setUploading] = useState(false);

  // Camera state
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const streamRef = useRef<MediaStream | null>(null);

  const uploadFile = async (file: File) => {
    try {
      const attachment = await attachmentsAPI.upload(file);
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
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploading(true);
    try {
      for (const file of acceptedFiles) {
        await uploadFile(file);
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

  const startCamera = async () => {
    setCameraError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setCameraActive(true);
    } catch (err: any) {
      setCameraError('Camera access denied or not available. Please allow camera access in your browser settings.');
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  const capturePhoto = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0);

    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const file = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
      stopCamera();
      setUploading(true);
      try {
        await uploadFile(file);
      } finally {
        setUploading(false);
      }
    }, 'image/jpeg', 0.92);
  };

  return (
    <Tabs defaultValue="upload" className="w-full">
      <TabsList className="grid w-full grid-cols-2">
        <TabsTrigger value="upload">
          <Upload className="h-4 w-4 mr-2" />
          Upload
        </TabsTrigger>
        <TabsTrigger value="camera" onClick={stopCamera}>
          <Camera className="h-4 w-4 mr-2" />
          Camera
        </TabsTrigger>
      </TabsList>

      {/* File Upload Tab */}
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
            {uploading ? 'Please wait...' : 'Click to browse — Images & PDFs supported'}
          </p>
        </div>
      </TabsContent>

      {/* Camera Tab */}
      <TabsContent value="camera" className="space-y-3">
        <canvas ref={canvasRef} className="hidden" />

        {cameraError && (
          <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-lg">
            {cameraError}
          </div>
        )}

        {cameraActive ? (
          <div className="space-y-2">
            <video
              ref={videoRef}
              className="w-full rounded-lg border bg-black"
              autoPlay
              playsInline
              muted
            />
            <div className="flex gap-2">
              <Button
                className="flex-1"
                onClick={capturePhoto}
                disabled={uploading}
              >
                <Camera className="h-4 w-4 mr-2" />
                {uploading ? 'Uploading...' : 'Capture Photo'}
              </Button>
              <Button variant="outline" onClick={stopCamera}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="text-center p-6 border rounded-lg space-y-3">
            <Image className="h-12 w-12 mx-auto text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Take a photo of a diagram or handwritten content</p>
            <Button onClick={startCamera}>
              <Camera className="h-4 w-4 mr-2" />
              Open Camera
            </Button>
          </div>
        )}
      </TabsContent>
    </Tabs>
  );
}
