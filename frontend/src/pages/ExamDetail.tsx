import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { api } from '@/api/client';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  ArrowLeft,
  FileText,
  Calendar,
  Clock,
  Award,
  BookOpen,
  CheckCircle2,
  Image,
  Atom,
  Download,
  Trash2,
  Globe,
  GlobeLock,
  BookOpenCheck,
  ListChecks,
} from 'lucide-react';
import { format } from 'date-fns';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

export default function ExamDetail() {
  const { examId } = useParams<{ examId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const deleteExamMutation = useMutation({
    mutationFn: (id: string) => api.exams.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exams'] });
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      toast.success('Exam deleted');
      navigate('/exams');
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to delete exam');
    },
  });

  const publishMutation = useMutation({
    mutationFn: (id: string) => api.exams.publish(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exam', examId] });
      queryClient.invalidateQueries({ queryKey: ['exams'] });
      toast.success('Exam published — students can now see it');
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to publish exam');
    },
  });

  const unpublishMutation = useMutation({
    mutationFn: (id: string) => api.exams.unpublish(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exam', examId] });
      queryClient.invalidateQueries({ queryKey: ['exams'] });
      toast.success('Exam unpublished');
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to unpublish exam');
    },
  });

  const [downloadDialogOpen, setDownloadDialogOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const downloadPDF = async (includeSolutions: boolean) => {
    if (!examId || !exam) return;
    setIsDownloading(true);
    setDownloadDialogOpen(false);
    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
      const token = localStorage.getItem('auth_token');
      const url = `${API_BASE_URL}/exams/${examId}/view-pdf?include_solutions=${includeSolutions}&t=${Date.now()}`;
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to download PDF: ${response.status} ${errorText}`);
      }
      const blob = await response.blob();
      if (blob.size === 0) throw new Error('Received empty PDF file');
      const objectUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      const suffix = includeSolutions ? '_with_solutions' : '_questions_only';
      a.download = `${exam.title.replace(/\s+/g, '_')}${suffix}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(objectUrl);
      document.body.removeChild(a);
      toast.success('PDF downloaded successfully');
    } catch (error: any) {
      console.error('Failed to download PDF:', error);
      toast.error(`Failed to download PDF: ${error.message || 'Unknown error'}`);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleDelete = () => {
    if (!examId || !exam) return;
    if (!window.confirm(`Delete "${exam.title}"? This will also remove all submissions for this exam.`)) return;
    deleteExamMutation.mutate(examId);
  };

  // Fetch exam details
  const { data: exam, isLoading } = useQuery({
    queryKey: ['exam', examId],
    queryFn: () => api.exams.getById(examId!),
    enabled: !!examId,
  });

  // Fetch course info
  const { data: course } = useQuery({
    queryKey: ['course', exam?.courseId],
    queryFn: () => api.courses.getById(exam!.courseId),
    enabled: !!exam?.courseId,
  });

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <p>Loading exam...</p>
        </div>
      </DashboardLayout>
    );
  }

  if (!exam) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-64">
          <p className="text-muted-foreground mb-4">Exam not found</p>
          <Button onClick={() => navigate('/exams')}>Back to Exams</Button>
        </div>
      </DashboardLayout>
    );
  }

  const renderQuestion = (question: any, parentNumber: string = '', level: number = 0) => {
    const questionNumber = parentNumber ? `${parentNumber}.${question.number}` : question.number.toString();

    return (
      <Card key={question.id} className={level > 0 ? 'ml-8 border-l-2' : ''}>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <Badge variant={level === 0 ? 'default' : 'secondary'}>
                Q{questionNumber}
              </Badge>
              <div>
                <CardTitle className="text-base">
                  {question.text || '(No question text)'}
                </CardTitle>
                {question.richContent && (
                  <div className="mt-2 prose prose-sm max-w-none">
                    {/* Render rich content if available */}
                    <p className="text-sm text-muted-foreground">
                      (Rich content available)
                    </p>
                  </div>
                )}
              </div>
            </div>
            <Badge variant="outline">{question.points} pts</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Attachments (images extracted from PDF) */}
          {question.attachments && question.attachments.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm font-semibold">Diagrams / Images</p>
              <div className="flex flex-wrap gap-4">
                {question.attachments.map((att: any) => {
                  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
                  const origin = apiBase.replace(/\/api\/?$/, '');
                  const src = att.filePath?.startsWith('http') ? att.filePath : `${origin}${att.filePath}`;
                  if (att.attachmentType === 'image' || !att.attachmentType) {
                    return (
                      <img
                        key={att.id}
                        src={src}
                        alt={att.filename}
                        className="max-w-full max-h-80 rounded-lg border object-contain"
                      />
                    );
                  }
                  return (
                    <Badge key={att.id} variant="secondary" className="gap-1">
                      <Image className="h-3 w-3" />
                      {att.filename}
                    </Badge>
                  );
                })}
              </div>
            </div>
          )}

          {/* Sub-questions (a), (b), (c) */}
          {question.subQuestions && question.subQuestions.length > 0 && level === 0 && (
            <div className="space-y-3">
              {question.subQuestions.map((sub: any, idx: number) => (
                <div key={sub.id || idx} className="flex gap-3 pl-2 border-l-2 border-primary/30">
                  <span className="font-semibold text-primary shrink-0 w-6 pt-0.5">
                    ({String.fromCharCode(97 + idx)})
                  </span>
                  <div className="flex-1">
                    <p className="text-sm">{sub.text || '(No text)'}</p>
                    <span className="text-xs text-muted-foreground">
                      [{sub.points} {sub.points === 1 ? 'point' : 'points'}]
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Embedded Content */}
          {question.embeddedContent && question.embeddedContent.length > 0 && (
            <div>
              <p className="text-sm font-semibold mb-2">Embedded Content:</p>
              <div className="flex flex-wrap gap-2">
                {question.embeddedContent.map((content: any, idx: number) => (
                  <Badge key={idx} variant="secondary" className="gap-1">
                    <Atom className="h-3 w-3" />
                    {content.contentType}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Gold Solution Steps */}
          {question.goldSolutionSteps && question.goldSolutionSteps.length > 0 && (
            <div className="border-t pt-4">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <p className="text-sm font-semibold">Gold Solution Steps:</p>
              </div>
              <div className="space-y-2">
                {question.goldSolutionSteps.map((step: any, idx: number) => (
                  <div key={idx} className="p-3 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-green-900">
                        Step {step.stepNumber}
                      </span>
                      <span className="text-xs text-green-700">
                        {step.points} pts
                        {step.required && (
                          <Badge variant="secondary" className="ml-2 text-xs">
                            Required
                          </Badge>
                        )}
                      </span>
                    </div>
                    {step.description && (
                      <p className="text-sm text-green-800 mb-1">{step.description}</p>
                    )}
                    <p className="text-sm font-mono bg-white px-2 py-1 rounded">
                      {step.expression}
                    </p>
                    {step.latex && (
                      <p className="text-xs text-green-700 mt-1">LaTeX: {step.latex}</p>
                    )}
                  </div>
                ))}
              </div>
              {question.finalAnswer && (
                <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm font-semibold text-blue-900 mb-1">Final Answer:</p>
                  <p className="text-sm font-mono text-blue-800">{question.finalAnswer}</p>
                  {question.finalAnswerLatex && (
                    <p className="text-xs text-blue-700 mt-1">
                      LaTeX: {question.finalAnswerLatex}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Sub-questions */}
          {question.subQuestions && question.subQuestions.length > 0 && (
            <div className="border-t pt-4 space-y-3">
              <p className="text-sm font-semibold">Sub-questions:</p>
              {question.subQuestions.map((subQ: any) =>
                renderQuestion(subQ, questionNumber, level + 1)
              )}
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const totalPoints = exam.questions?.reduce((sum: number, q: any) => {
    const subPoints = q.subQuestions?.reduce((subSum: number, sub: any) => subSum + sub.points, 0) || 0;
    return sum + q.points + subPoints;
  }, 0) || 0;

  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/exams')}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <div className="flex items-center gap-3 mb-2 flex-wrap">
                <h1 className="text-3xl font-bold tracking-tight">{exam.title}</h1>
                <Badge variant="secondary">{course?.code}</Badge>
                {exam.isPublished ? (
                  <Badge className="bg-green-100 text-green-800 border-green-200">
                    <Globe className="h-3 w-3 mr-1" />
                    Published
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-muted-foreground">
                    <GlobeLock className="h-3 w-3 mr-1" />
                    Draft
                  </Badge>
                )}
              </div>
              {exam.description && (
                <p className="text-muted-foreground">{exam.description}</p>
              )}
              <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
                {exam.dueDate && (
                  <div className="flex items-center gap-1.5">
                    <Calendar className="h-4 w-4" />
                    Due: {format(new Date(exam.dueDate), 'MMM d, yyyy')}
                  </div>
                )}
                {exam.duration && (
                  <div className="flex items-center gap-1.5">
                    <Clock className="h-4 w-4" />
                    {exam.duration} minutes
                  </div>
                )}
                <div className="flex items-center gap-1.5">
                  <Award className="h-4 w-4" />
                  {totalPoints} total points
                </div>
                <div className="flex items-center gap-1.5">
                  <FileText className="h-4 w-4" />
                  {exam.questions?.length || 0} questions
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              disabled={isDownloading}
              onClick={() => setDownloadDialogOpen(true)}
            >
              <Download className="h-4 w-4 mr-2" />
              {isDownloading ? 'Downloading…' : 'Download PDF'}
            </Button>
            {user?.role === 'professor' && (
              <>
                {exam.isPublished ? (
                  <Button
                    variant="outline"
                    onClick={() => unpublishMutation.mutate(examId!)}
                    disabled={unpublishMutation.isPending}
                  >
                    <GlobeLock className="h-4 w-4 mr-2" />
                    {unpublishMutation.isPending ? 'Unpublishing...' : 'Unpublish'}
                  </Button>
                ) : (
                  <Button
                    onClick={() => publishMutation.mutate(examId!)}
                    disabled={publishMutation.isPending}
                  >
                    <Globe className="h-4 w-4 mr-2" />
                    {publishMutation.isPending ? 'Publishing...' : 'Publish Exam'}
                  </Button>
                )}
                <Button variant="outline" onClick={() => navigate(`/exams/${examId}/edit`)}>
                  Edit Exam
                </Button>
                <Button
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  onClick={handleDelete}
                  disabled={deleteExamMutation.isPending}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Exam
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Exam Preview */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Exam Preview
            </CardTitle>
            <CardDescription>
              Complete exam preview with all questions and solutions
            </CardDescription>
          </CardHeader>
          <CardContent>
            {exam.questions && exam.questions.length > 0 ? (
              <div className="space-y-6">
                {exam.questions.map((question: any, idx: number) => (
                  <div key={question.id || idx}>
                    {renderQuestion(question)}
                    {idx < exam.questions.length - 1 && (
                      <Separator className="my-6" />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <FileText className="h-12 w-12 mx-auto mb-3 opacity-20" />
                <p>No questions in this exam</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Download PDF dialog */}
      <Dialog open={downloadDialogOpen} onOpenChange={setDownloadDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Download className="h-5 w-5" />
              Download Exam PDF
            </DialogTitle>
            <DialogDescription>
              Choose what to include in the downloaded PDF.
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-1 gap-3 pt-2">
            <button
              onClick={() => downloadPDF(false)}
              className="flex items-start gap-4 rounded-lg border p-4 text-left hover:bg-muted/50 transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <ListChecks className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-sm">Questions only</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Export the exam questions and answer spaces — suitable for printing and distributing to students.
                </p>
              </div>
            </button>

            <button
              onClick={() => downloadPDF(true)}
              className="flex items-start gap-4 rounded-lg border p-4 text-left hover:bg-muted/50 transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-green-100 text-green-700">
                <BookOpenCheck className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-sm">Questions + Golden Answers</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Include the reference solution steps and final answers — suitable for your own records or marking guides.
                </p>
              </div>
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
}

