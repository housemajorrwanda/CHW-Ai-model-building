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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
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
import { AttachmentImage } from '@/components/ui/AttachmentImage';
import { RichContentViewer } from '@/components/exam-taker/RichContentViewer';
import { AnswerKeyUpload } from '@/components/exam-builder/AnswerKeyUpload';

/** Question tree returned by GET /exams/:id (top-level and nested sub-questions). */
interface ExamDetailQuestion {
  id: string;
  number: number;
  text?: string;
  richContent?: unknown;
  points: number;
  attachments?: Array<{
    id: string;
    filePath: string;
    filename: string;
    attachmentType?: string;
  }>;
  embeddedContent?: Array<{ contentType?: string }>;
  goldSolutionSteps?: Array<{
    stepNumber: number;
    points: number;
    required?: boolean;
    description?: string;
    expression?: string;
    latex?: string;
  }>;
  finalAnswer?: string;
  finalAnswerLatex?: string;
  outlineTitle?: string | null;
  subQuestions?: ExamDetailQuestion[];
}

interface ExamDetailData {
  id: string;
  title: string;
  courseId: string;
  description?: string | null;
  dueDate?: string | null;
  duration?: number | null;
  isPublished: boolean;
  totalPoints?: number;
  questions?: ExamDetailQuestion[];
}

interface CourseDetailSummary {
  code: string;
  name?: string;
}

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
  /** Paper size for PDF export (matches backend `paper` query param). */
  const [pdfPaper, setPdfPaper] = useState<'a4' | 'letter' | 'legal'>('a4');

  const { data: exam, isLoading } = useQuery({
    queryKey: ['exam', examId],
    queryFn: () => api.exams.getById(examId!) as Promise<ExamDetailData>,
    enabled: !!examId,
  });

  const { data: course } = useQuery({
    queryKey: ['course', exam?.courseId],
    queryFn: () => api.courses.getById(exam!.courseId) as Promise<CourseDetailSummary>,
    enabled: !!exam?.courseId,
  });

  const downloadPDF = async (includeSolutions: boolean) => {
    if (!examId || !exam) return;
    setIsDownloading(true);
    setDownloadDialogOpen(false);
    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
      const token = localStorage.getItem('auth_token');
      const url = `${API_BASE_URL}/exams/${examId}/view-pdf?include_solutions=${includeSolutions}&paper=${encodeURIComponent(pdfPaper)}&t=${Date.now()}`;
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

  const renderSubParts = (subs: ExamDetailQuestion[], depth = 0): JSX.Element => (
    <div className={depth > 0 ? 'ml-4 mt-2 space-y-2' : 'space-y-3'}>
      {subs.map((sub, idx) => {
        const label = sub.outlineTitle?.trim() || String.fromCharCode(97 + idx);
        return (
          <div key={sub.id || `${depth}-${idx}`}>
            <div className="flex gap-3 pl-2 border-l-2 border-primary/30">
              <span className="font-semibold text-primary shrink-0 min-w-[2rem] pt-0.5">
                {label}
              </span>
              <div className="flex-1 min-w-0">
                <RichContentViewer content={sub.richContent || sub.text} className="text-sm" />
                <span className="text-xs text-muted-foreground">
                  [{sub.points} {sub.points === 1 ? 'point' : 'points'}]
                </span>
              </div>
            </div>
            {sub.subQuestions && sub.subQuestions.length > 0
              ? renderSubParts(sub.subQuestions, depth + 1)
              : null}
          </div>
        );
      })}
    </div>
  );

  const renderQuestion = (question: ExamDetailQuestion) => {
    return (
      <Card key={question.id}>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <Badge variant="default">
                Q{question.number}
              </Badge>
              <div>
                <CardTitle className="text-base">
                  {question.richContent ? (
                    <RichContentViewer content={question.richContent} />
                  ) : (
                    question.text || '(No question text)'
                  )}
                </CardTitle>
                {question.richContent && question.text && (
                  <p className="sr-only">{question.text}</p>
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
                {question.attachments.map((att) => {
                  if (att.attachmentType === 'image' || !att.attachmentType) {
                    return (
                      <AttachmentImage
                        key={att.id}
                        filePath={att.filePath}
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

          {/* Sub-questions nested under this question */}
          {question.subQuestions && question.subQuestions.length > 0 && (
            <div className="border-t pt-4">
              <p className="text-sm font-semibold mb-3">Parts:</p>
              {renderSubParts(question.subQuestions)}
            </div>
          )}

          {/* Embedded Content */}
          {question.embeddedContent && question.embeddedContent.length > 0 && (
            <div>
              <p className="text-sm font-semibold mb-2">Embedded Content:</p>
              <div className="flex flex-wrap gap-2">
                {question.embeddedContent.map((content, idx: number) => (
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
                {question.goldSolutionSteps.map((step, idx: number) => (
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

        </CardContent>
      </Card>
    );
  };

  const sumQuestionPoints = (q: ExamDetailQuestion): number => {
    const subs = q.subQuestions ?? [];
    if (subs.length > 0) return subs.reduce((s, sub) => s + sumQuestionPoints(sub), 0);
    return q.points ?? 0;
  };

  const totalPoints =
    exam.questions?.reduce((sum, q) => sum + sumQuestionPoints(q), 0) || 0;

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

        {user?.role === 'professor' && examId && (
          <AnswerKeyUpload examId={examId} examTitle={exam.title} />
        )}

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
                {exam.questions.map((question, idx: number) => (
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
              Choose paper size and what to include in the downloaded PDF.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2 pt-2">
            <Label htmlFor="pdf-paper" className="text-xs text-muted-foreground">
              Paper size
            </Label>
            <Select value={pdfPaper} onValueChange={(v) => setPdfPaper(v as 'a4' | 'letter' | 'legal')}>
              <SelectTrigger id="pdf-paper" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="a4">A4 (210 × 297 mm)</SelectItem>
                <SelectItem value="letter">US Letter (8.5 × 11 in)</SelectItem>
                <SelectItem value="legal">US Legal (8.5 × 14 in)</SelectItem>
              </SelectContent>
            </Select>
          </div>

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

