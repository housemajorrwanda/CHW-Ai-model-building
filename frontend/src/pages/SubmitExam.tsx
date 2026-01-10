import { useState, useCallback } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Upload, Image, X, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';

export default function SubmitExam() {
  const [selectedExam, setSelectedExam] = useState<string>('');
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch exams
  const { data: exams, isLoading: examsLoading } = useQuery({
    queryKey: ['exams'],
    queryFn: () => api.exams.getAll(),
  });

  // Fetch courses
  const { data: courses } = useQuery({
    queryKey: ['courses'],
    queryFn: () => api.courses.getAll(),
  });

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: ({ examId, images }: { examId: string; images: File[] }) =>
      api.submissions.submit(examId, images),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      setIsSubmitted(true);
      toast({
        title: 'Submission successful!',
        description: 'Your exam has been submitted for grading.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Submission failed',
        description: error.message || 'Failed to submit exam',
        variant: 'destructive',
      });
    },
  });

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files).filter(
      (file) => file.type.startsWith('image/')
    );
    setUploadedFiles((prev) => [...prev, ...files]);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files).filter(
        (file) => file.type.startsWith('image/')
      );
      setUploadedFiles((prev) => [...prev, ...files]);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!selectedExam || uploadedFiles.length === 0) {
      toast({
        title: 'Missing information',
        description: 'Please select an exam and upload at least one image.',
        variant: 'destructive',
      });
      return;
    }

    submitMutation.mutate({ examId: selectedExam, images: uploadedFiles });
  };

  if (isSubmitted) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <Card className="max-w-md w-full text-center animate-fade-up">
            <CardContent className="pt-8 pb-8">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-success/10 mx-auto mb-4">
                <CheckCircle2 className="h-8 w-8 text-success" />
              </div>
              <h2 className="text-2xl font-bold mb-2">Submission Complete!</h2>
              <p className="text-muted-foreground mb-6">
                Your exam has been submitted and will be graded soon. You'll receive your results once grading is complete.
              </p>
              <Button onClick={() => {
                setIsSubmitted(false);
                setSelectedExam('');
                setUploadedFiles([]);
              }}>
                Submit Another Exam
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Submit Exam</h1>
          <p className="text-muted-foreground mt-1">
            Upload images of your handwritten exam answers for AI grading
          </p>
        </div>

        {/* Exam Selection */}
        <Card className="animate-fade-up">
          <CardHeader>
            <CardTitle className="text-lg">Select Exam</CardTitle>
            <CardDescription>Choose the exam you want to submit</CardDescription>
          </CardHeader>
          <CardContent>
            <Select value={selectedExam} onValueChange={setSelectedExam}>
              <SelectTrigger>
                <SelectValue placeholder="Select an exam" />
              </SelectTrigger>
              <SelectContent>
                {examsLoading ? (
                  <SelectItem value="loading" disabled>Loading exams...</SelectItem>
                ) : (exams || []).length === 0 ? (
                  <SelectItem value="none" disabled>No exams available</SelectItem>
                ) : (
                  (exams || []).map((exam: any) => {
                    const course = (courses || []).find((c: any) => c.id === exam.courseId);
                    return (
                      <SelectItem key={exam.id} value={exam.id}>
                        {exam.title} {course ? `(${course.code})` : ''}
                      </SelectItem>
                    );
                  })
                )}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        {/* File Upload */}
        <Card className="animate-fade-up" style={{ animationDelay: '100ms' }}>
          <CardHeader>
            <CardTitle className="text-lg">Upload Images</CardTitle>
            <CardDescription>
              Take photos or scan your handwritten exam answers
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Drop Zone */}
            <div
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              className={cn(
                'border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200',
                isDragging
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50 hover:bg-muted/50'
              )}
            >
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={handleFileInput}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                <Upload className="h-10 w-10 text-muted-foreground mx-auto mb-4" />
                <p className="font-medium mb-1">Drop images here or click to upload</p>
                <p className="text-sm text-muted-foreground">
                  Supports JPG, PNG, HEIC • Max 10MB per file
                </p>
              </label>
            </div>

            {/* Uploaded Files Preview */}
            {uploadedFiles.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium">Uploaded Files ({uploadedFiles.length})</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {uploadedFiles.map((file, index) => (
                    <div
                      key={index}
                      className="relative group rounded-lg border bg-muted/50 overflow-hidden"
                    >
                      <img
                        src={URL.createObjectURL(file)}
                        alt={`Upload ${index + 1}`}
                        className="w-full h-24 object-cover"
                      />
                      <div className="absolute inset-0 bg-foreground/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <Button
                          variant="destructive"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => removeFile(index)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                      <div className="p-2">
                        <p className="text-xs truncate">{file.name}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          disabled={!selectedExam || uploadedFiles.length === 0 || submitMutation.isPending}
          className="w-full h-12 text-base font-semibold"
        >
          {submitMutation.isPending ? (
            <>
              <div className="h-4 w-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin mr-2" />
              Submitting...
            </>
          ) : (
            <>
              <Upload className="h-5 w-5 mr-2" />
              Submit Exam for Grading
            </>
          )}
        </Button>
      </div>
    </DashboardLayout>
  );
}