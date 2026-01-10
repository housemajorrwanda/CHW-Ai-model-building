import { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AnswerEditor } from '@/components/exam-taker/AnswerEditor';
import { QuestionDisplay } from '@/components/exam-taker/QuestionDisplay';
import { Upload, X, CheckCircle2, FileText, Image as ImageIcon, Clock, AlertCircle, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { examsAPI, submissionsAPI } from '@/lib/api';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';

interface Answer {
  questionId: string;
  questionNumber: number;
  typedAnswer: string;
  images: File[];
}

export default function TakeExam() {
  const { examId } = useParams<{ examId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [currentTab, setCurrentTab] = useState<string>('typed');
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

  // Fetch exam details
  const { data: exam, isLoading: examLoading } = useQuery({
    queryKey: ['exam', examId],
    queryFn: () => examsAPI.getById(examId!),
    enabled: !!examId,
  });

  // Initialize answers when exam loads
  const initializeAnswers = () => {
    if (exam?.questions && answers.length === 0) {
      const initialAnswers = exam.questions.map((q: any, idx: number) => ({
        questionId: q.id || `q-${idx}`,
        questionNumber: q.number || idx + 1,
        typedAnswer: '',
        images: [],
      }));
      setAnswers(initialAnswers);
    }
  };

  // Call initialize when exam loads
  if (exam && answers.length === 0) {
    initializeAnswers();
  }

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: async ({ examId, answers }: { examId: string; answers: Answer[] }) => {
      // For now, we'll submit both typed answers and images
      // The backend will need to be updated to handle typed answers
      const allImages = answers.flatMap(a => a.images);
      return submissionsAPI.submit(examId, allImages, answers);
    },
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

  const updateAnswer = (questionNumber: number, typedAnswer: string) => {
    setAnswers((prev) =>
      prev.map((a) =>
        a.questionNumber === questionNumber ? { ...a, typedAnswer } : a
      )
    );
  };

  const handleDrop = useCallback((e: React.DragEvent, questionNumber: number) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files).filter(
      (file) => file.type.startsWith('image/')
    );
    
    setAnswers((prev) =>
      prev.map((a) =>
        a.questionNumber === questionNumber
          ? { ...a, images: [...a.images, ...files] }
          : a
      )
    );
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>, questionNumber: number) => {
    if (e.target.files) {
      const files = Array.from(e.target.files).filter(
        (file) => file.type.startsWith('image/')
      );
      
      setAnswers((prev) =>
        prev.map((a) =>
          a.questionNumber === questionNumber
            ? { ...a, images: [...a.images, ...files] }
            : a
        )
      );
    }
  };

  const removeImage = (questionNumber: number, imageIndex: number) => {
    setAnswers((prev) =>
      prev.map((a) =>
        a.questionNumber === questionNumber
          ? { ...a, images: a.images.filter((_, i) => i !== imageIndex) }
          : a
      )
    );
  };

  const handleSubmit = async () => {
    // Validate that at least some answers are provided
    const hasTypedAnswers = answers.some(a => a.typedAnswer.trim() !== '<p>Type your answer here...</p>' && a.typedAnswer.trim() !== '');
    const hasImageAnswers = answers.some(a => a.images.length > 0);

    if (!hasTypedAnswers && !hasImageAnswers) {
      toast({
        title: 'No answers provided',
        description: 'Please provide at least one answer (typed or uploaded image).',
        variant: 'destructive',
      });
      return;
    }

    if (!examId) return;

    submitMutation.mutate({ examId, answers });
  };

  if (examLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="h-8 w-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading exam...</p>
        </div>
      </div>
    );
  }

  if (!exam) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
            <h2 className="text-xl font-bold mb-2">Exam Not Found</h2>
            <p className="text-muted-foreground mb-4">
              The exam you're looking for doesn't exist or has been removed.
            </p>
            <Button onClick={() => navigate('/browse-courses')}>
              Back to Courses
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isSubmitted) {
    return (
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
            <div className="flex gap-2 justify-center">
              <Button onClick={() => navigate('/my-exams')}>
                View My Exams
              </Button>
              <Button variant="outline" onClick={() => navigate('/browse-courses')}>
                Browse Courses
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const currentQuestion = exam.questions?.[currentQuestionIndex];
  const currentQuestionNumber = currentQuestion?.number || currentQuestionIndex + 1;
  const currentAnswer = answers.find(a => a.questionNumber === currentQuestionNumber);
  
  return (
    <div className="flex gap-6 h-[calc(100vh-120px)]">
      {/* Question Navigation Sidebar */}
      <div className="w-64 flex-shrink-0">
        <Card className="h-full">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Questions</CardTitle>
            <p className="text-xs text-muted-foreground">
              {answers.filter(a => a.typedAnswer || a.images.length > 0).length} / {exam.questions?.length || 0} answered
            </p>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[calc(100vh-280px)]">
              <div className="space-y-1 px-4 pb-4">
                {exam.questions?.map((question: any, idx: number) => {
                  const qNum = question.number || idx + 1;
                  const ans = answers.find(a => a.questionNumber === qNum);
                  const isAnswered = ans && (ans.typedAnswer?.trim() || ans.images.length > 0);
                  
                  return (
                    <Button
                      key={idx}
                      variant={currentQuestionIndex === idx ? 'default' : 'ghost'}
                      className={cn(
                        'w-full justify-between',
                        isAnswered && currentQuestionIndex !== idx && 'bg-success/10 hover:bg-success/20'
                      )}
                      onClick={() => setCurrentQuestionIndex(idx)}
                    >
                      <span>Question {qNum}</span>
                      <div className="flex items-center gap-1">
                        {isAnswered && <CheckCircle2 className="h-3 w-3" />}
                        <span className="text-xs">{question.points}pts</span>
                      </div>
                    </Button>
                  );
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="flex-1 space-y-4">
        {/* Header */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-2xl">{exam.title}</CardTitle>
                {exam.description && (
                  <CardDescription className="mt-2">{exam.description}</CardDescription>
                )}
              </div>
              <div className="text-right">
                <div className="text-sm text-muted-foreground">Total Marks</div>
                <div className="text-2xl font-bold">{exam.totalPoints || exam.questions?.reduce((sum: number, q: any) => sum + (q.points || 0), 0) || 0}</div>
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* Current Question */}
        <ScrollArea className="h-[calc(100vh-320px)]">
          {currentQuestion && (
            <div className="pr-4 space-y-4">
              {/* Question Display */}
              <QuestionDisplay
                questionNumber={currentQuestionNumber}
                questionText={currentQuestion.richContent || currentQuestion.text}
                questionPoints={currentQuestion.points || 0}
              />

              {/* Answer Tabs */}
              <Card>
                <CardContent className="p-0">
                  <Tabs value={currentTab} onValueChange={setCurrentTab}>
                    <div className="border-b px-6 pt-4">
                      <TabsList className="grid w-full max-w-md grid-cols-2">
                        <TabsTrigger value="typed">
                          <FileText className="h-4 w-4 mr-2" />
                          Type Answer
                        </TabsTrigger>
                        <TabsTrigger value="upload">
                          <ImageIcon className="h-4 w-4 mr-2" />
                          Upload Image
                        </TabsTrigger>
                      </TabsList>
                    </div>

                    <TabsContent value="typed" className="p-6 pt-4">
                      <AnswerEditor
                        questionNumber={currentQuestionNumber}
                        questionText={currentQuestion.richContent || currentQuestion.text}
                        questionPoints={currentQuestion.points || 0}
                        answer={currentAnswer?.typedAnswer || ''}
                        onUpdate={(newAnswer) => updateAnswer(currentQuestionNumber, newAnswer)}
                      />
                    </TabsContent>

                    <TabsContent value="upload" className="p-6 pt-4">
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-lg">Upload Images</CardTitle>
                          <CardDescription>
                            Upload images of your handwritten work for this question
                          </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                        {/* Drop Zone */}
                        <div
                          onDrop={(e) => handleDrop(e, currentQuestionNumber)}
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
                            onChange={(e) => handleFileInput(e, currentQuestionNumber)}
                            className="hidden"
                            id={`file-upload-${currentQuestionNumber}`}
                          />
                          <label htmlFor={`file-upload-${currentQuestionNumber}`} className="cursor-pointer">
                            <Upload className="h-10 w-10 text-muted-foreground mx-auto mb-4" />
                            <p className="font-medium mb-1">Drop images here or click to upload</p>
                            <p className="text-sm text-muted-foreground">
                              Supports JPG, PNG • Max 10MB per file
                            </p>
                          </label>
                        </div>

                        {/* Uploaded Files Preview */}
                        {currentAnswer && currentAnswer.images.length > 0 && (
                          <div className="space-y-2">
                            <p className="text-sm font-medium">Uploaded ({currentAnswer.images.length})</p>
                            <div className="grid grid-cols-2 gap-3">
                              {currentAnswer.images.map((file, imgIdx) => (
                                <div
                                  key={imgIdx}
                                  className="relative group rounded-lg border bg-muted/50 overflow-hidden"
                                >
                                  <img
                                    src={URL.createObjectURL(file)}
                                    alt={`Upload ${imgIdx + 1}`}
                                    className="w-full h-32 object-cover"
                                  />
                                  <div className="absolute inset-0 bg-foreground/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                    <Button
                                      variant="destructive"
                                      size="icon"
                                      className="h-8 w-8"
                                      onClick={() => removeImage(currentQuestionNumber, imgIdx)}
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
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
            </div>
          )}
        </ScrollArea>

        {/* Navigation Buttons */}
        <div className="flex justify-between items-center pt-4 border-t">
          <Button
            variant="outline"
            onClick={() => setCurrentQuestionIndex(Math.max(0, currentQuestionIndex - 1))}
            disabled={currentQuestionIndex === 0}
          >
            Previous
          </Button>
          
          <div className="text-sm text-muted-foreground">
            Question {currentQuestionIndex + 1} of {exam.questions?.length || 0}
          </div>

          {currentQuestionIndex < (exam.questions?.length || 0) - 1 ? (
            <Button
              onClick={() => setCurrentQuestionIndex(currentQuestionIndex + 1)}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={submitMutation.isPending}
              className="min-w-[150px]"
            >
              {submitMutation.isPending ? (
                <>
                  <div className="h-4 w-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin mr-2" />
                  Submitting...
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Submit Exam
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

