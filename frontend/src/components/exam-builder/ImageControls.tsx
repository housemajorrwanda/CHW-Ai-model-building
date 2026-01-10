import { Button } from '@/components/ui/button';
import { Trash2, Maximize2, Crop } from 'lucide-react';
import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { Editor } from '@tiptap/react';

interface ImageControlsProps {
  editor: Editor;
  imageNode: any;
}

export function ImageControls({ editor, imageNode }: ImageControlsProps) {
  const [isResizeOpen, setIsResizeOpen] = useState(false);
  const [width, setWidth] = useState('');
  const [height, setHeight] = useState('');

  useEffect(() => {
    if (imageNode) {
      setWidth(imageNode.attrs?.width?.toString() || '');
      setHeight(imageNode.attrs?.height?.toString() || '');
    }
  }, [imageNode]);

  const handleResize = () => {
    if (imageNode) {
      const attrs: any = { src: imageNode.attrs.src };
      if (width) attrs.width = parseInt(width);
      if (height) attrs.height = parseInt(height);
      
      editor.chain().focus().setImage(attrs).run();
      setIsResizeOpen(false);
    }
  };

  const handleRemove = () => {
    editor.chain().focus().deleteSelection().run();
  };

  const handleCrop = () => {
    if (!imageNode) return;
    
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = imageNode.attrs.src;
    
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (ctx) {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        
        const dataUrl = canvas.toDataURL('image/png');
        editor.chain().focus().setImage({ src: dataUrl }).run();
      }
    };
    
    img.onerror = () => {
      alert('Unable to crop image. Please try uploading a new image.');
    };
  };

  if (!imageNode) return null;

  return (
    <div className="flex items-center gap-1 border rounded p-1 bg-background">
      <Button
        variant="ghost"
        size="sm"
        className="h-7 px-2"
        onClick={() => setIsResizeOpen(true)}
      >
        <Maximize2 className="h-3 w-3 mr-1" />
        Resize
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-7 px-2"
        onClick={handleCrop}
        title="Crop Image"
      >
        <Crop className="h-3 w-3 mr-1" />
        Crop
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-7 px-2 text-destructive"
        onClick={handleRemove}
      >
        <Trash2 className="h-3 w-3 mr-1" />
        Remove
      </Button>

      <Dialog open={isResizeOpen} onOpenChange={setIsResizeOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resize Image</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Width (px)</Label>
                <Input
                  type="number"
                  value={width}
                  onChange={(e) => setWidth(e.target.value)}
                  placeholder="Auto"
                />
              </div>
              <div>
                <Label>Height (px)</Label>
                <Input
                  type="number"
                  value={height}
                  onChange={(e) => setHeight(e.target.value)}
                  placeholder="Auto"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setIsResizeOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleResize}>Apply</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

