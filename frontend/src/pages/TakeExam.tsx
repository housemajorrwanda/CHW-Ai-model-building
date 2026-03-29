import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AnswerEditor } from '@/components/exam-taker/AnswerEditor';
import { QuestionDisplay } from '@/components/exam-taker/QuestionDisplay';
import { Upload, X, CheckCircle2, FileText, AlertCircle, ChevronRight, FileUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { examsAPI, submissionsAPI, type AnswerPdfPreviewResponse } from '@/lib/api';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';

// ── Types ──────────────────────────────────────────────────────────────────

interface SubAnswer {
  subQuestionId: string;
  subNumber: number;   // 1-based (a=1, b=2, …)
  typedAnswer: string;
}

interface Answer {
  questionId: string;
  questionNumber: number;
  /** Used when the question has NO sub-questions */
  typedAnswer: string;
  /** Per-sub-question typed answers (for questions with sub-questions) */
  subAnswers: SubAnswer[];
  /** Uploaded handwritten images (always at parent-question level) */
  images: File[];
}

/** API shape for GET /exams/:id on the take-exam page */
interface TakeExamPayload {
  title: string;
  description?: string | null;
  totalPoints?: number;
  questions?: {
    id: string;
    number?: number;
    points?: number;
    text?: string;
    richContent?: string;
    attachments?: Array<{
      id: string;
      filePath: string;
      filename: string;
      attachmentType?: string;
    }>;
    subQuestions?: {
      id: string;
      number?: number;
      text?: string;
      richContent?: unknown;
      points?: number;
    }[];
  }[];
}

// ── Helpers ────────────────────────────────────────────────────────────────

const subLabel = (idx: number) => String.fromCharCode(97 + idx); // a, b, c, …

function isQuestionAnswered(ans: Answer | undefined): boolean {
  if (!ans) return false;
  if (ans.images.length > 0) return true;
  if (ans.subAnswers.length > 0) return ans.subAnswers.some(sa => sa.typedAnswer.trim() !== '');
  return ans.typedAnswer.trim() !== '';
}

// ── Component ──────────────────────────────────────────────────────────────

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
  // Full-exam answer PDF (covers all questions, page N = question N)
  const [fullAnswerPdf, setFullAnswerPdf] = useState<File | null>(null);
  const [pdfPreview, setPdfPreview] = useState<AnswerPdfPreviewResponse | null>(null);
  const [pdfPreviewLoading, setPdfPreviewLoading] = useState(false);
  const [pdfPreviewError, setPdfPreviewError] = useState<string | null>(null);

  // ── Exam query ─────────────────────────────────────────────────────────

  const { data: exam, isLoading: examLoading } = useQuery({
    queryKey: ['exam', examId],
    queryFn: () => examsAPI.getById(examId!) as Promise<TakeExamPayload>,
    enabled: !!examId,
  });

  // Initialise one Answer entry per top-level question
  if (exam?.questions && answers.length === 0) {
    const initial: Answer[] = exam.questions.map((q, idx: number) => ({
      questionId: q.id || `q-${idx}`,
      questionNumber: q.number || idx + 1,
      typedAnswer: '',
      subAnswers: (q.subQuestions ?? []).map((sq, si: number) => ({
        subQuestionId: sq.id,
        subNumber: si + 1,
        typedAnswer: '',
      })),
      images: [],
    }));
    setAnswers(initial);
  }

  useEffect(() => {
    if (!fullAnswerPdf || !examId) {
      setPdfPreview(null);
      setPdfPreviewError(null);
      setPdfPreviewLoading(false);
      return;
    }
    let cancelled = false;
    setPdfPreviewLoading(true);
    setPdfPreviewError(null);
    setPdfPreview(null);
    examsAPI
      .previewAnswerPdf(examId, fullAnswerPdf)
      .then((data) => {
        if (!cancelled) setPdfPreview(data);
      })
      .catch((e: Error) => {
        if (!cancelled) setPdfPreviewError(e.message || 'Could not analyze PDF');
      })
      .finally(() => {
        if (!cancelled) setPdfPreviewLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [fullAnswerPdf, examId]);

  // ── Submit ─────────────────────────────────────────────────────────────

  const submitMutation = useMutation({
    mutationFn: async ({ examId, answers }: { examId: string; answers: Answer[] }) => {
      // Flatten typed answers: one entry per question (or per sub-question)
      const flatAnswers: { questionId: string; questionNumber: number; typedAnswer: string }[] = [];

      for (const ans of answers) {
        if (ans.subAnswers.length > 0) {
          // Submit each sub-question answer separately so the grader matches by sub-question ID
          for (const sa of ans.subAnswers) {
            if (sa.typedAnswer.trim()) {
              flatAnswers.push({
                questionId: sa.subQuestionId,
                questionNumber: sa.subNumber,
                typedAnswer: sa.typedAnswer,
              });
            }
          }
        } else if (ans.typedAnswer.trim()) {
          flatAnswers.push({
            questionId: ans.questionId,
            questionNumber: ans.questionNumber,
            typedAnswer: ans.typedAnswer,
          });
        }
      }

      // Build { questionId, file } pairs so the backend can route each
      // image to the correct question.
      const imageEntries = answers.flatMap(a =>
        a.images.map((file: File) => ({ questionId: a.questionId, file }))
      );
      return submissionsAPI.submit(examId, imageEntries, flatAnswers, fullAnswerPdf);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
      setIsSubmitted(true);
      toast({ title: 'Submission successful!', description: 'Your exam has been submitted for grading.' });
    },
    onError: (error: any) => {
      toast({ title: 'Submission failed', description: error.message || 'Failed to submit exam', variant: 'destructive' });
    },
  });

  // ── Answer updaters ────────────────────────────────────────────────────

  const updateParentAnswer = (questionId: string, questionNumber: number, typedAnswer: string) => {
    setAnswers(prev => prev.map(a =>
      a.questionId === questionId || a.questionNumber === questionNumber
        ? { ...a, typedAnswer }
        : a
    ));
  };

  const updateSubAnswer = (questionId: string, subQuestionId: string, typedAnswer: string) => {
    setAnswers(prev => prev.map(a =>
      a.questionId === questionId
        ? {
            ...a,
            subAnswers: a.subAnswers.map(sa =>
              sa.subQuestionId === subQuestionId ? { ...sa, typedAnswer } : sa
            ),
          }
        : a
    ));
  };

  const isAllowedFile = (f: File) =>
    f.type.startsWith('image/') || f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf');

  const handleDrop = useCallback((e: React.DragEvent, questionId: string) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files).filter(isAllowedFile);
    setAnswers(prev => prev.map(a => a.questionId === questionId ? { ...a, images: [...a.images, ...files] } : a));
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>, questionId: string) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files).filter(isAllowedFile);
    setAnswers(prev => prev.map(a => a.questionId === questionId ? { ...a, images: [...a.images, ...files] } : a));
  };

  const handleFullPdfInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'))) {
      setFullAnswerPdf(file);
    }
  };

  const removeImage = (questionId: string, imgIdx: number) => {
    setAnswers(prev => prev.map(a =>
      a.questionId === questionId ? { ...a, images: a.images.filter((_, i) => i !== imgIdx) } : a
    ));
  };

  // ── Submit handler ─────────────────────────────────────────────────────

  const handleSubmit = () => {
    const hasAny = answers.some(isQuestionAnswered) || !!fullAnswerPdf;
    if (!hasAny) {
      toast({ title: 'No answers provided', description: 'Please answer at least one question, or upload your answer PDF.', variant: 'destructive' });
      return;
    }
    if (examId) submitMutation.mutate({ examId, answers });
  };

  // ── Loading / not-found screens ────────────────────────────────────────

  if (examLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="h-8 w-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading exam…</p>
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
            <p className="text-muted-foreground mb-4">The exam you're looking for doesn't exist or has been removed.</p>
            <Button onClick={() => navigate('/browse-courses')}>Back to Courses</Button>
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
              <Button onClick={() => navigate('/my-exams')}>View My Exams</Button>
              <Button variant="outline" onClick={() => navigate('/browse-courses')}>Browse Courses</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Main render ────────────────────────────────────────────────────────

  const currentQuestion = exam.questions?.[currentQuestionIndex];
  const currentQuestionNumber = currentQuestion?.number || currentQuestionIndex + 1;
  const currentAnswer = answers.find(a =>
    a.questionId === currentQuestion?.id || a.questionNumber === currentQuestionNumber
  );
  const hasSubQuestions = (currentQuestion?.subQuestions?.length ?? 0) > 0;
  const answeredCount = answers.filter(isQuestionAnswered).length;
  const canSubmit = answers.some(isQuestionAnswered) || !!fullAnswerPdf;
  const totalQuestions = exam.questions?.length || 0;
  const isLastQuestion = totalQuestions === 0 || currentQuestionIndex >= totalQuestions - 1;

  return (
    <div className="flex gap-6 h-[calc(100vh-120px)]">
      {/* ── Sidebar: question navigation ─────────────────────────────── */}
      <div className="w-64 flex-shrink-0">
        <Card className="h-full">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Questions</CardTitle>
            <p className="text-xs text-muted-foreground">
              {answeredCount} / {exam.questions?.length || 0} answered
            </p>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[calc(100vh-280px)]">
              <div className="space-y-1 px-4 pb-4">
                {exam.questions?.map((question: any, idx: number) => {
                  const qNum = question.number || idx + 1;
                  const ans = answers.find(a => a.questionId === question.id || a.questionNumber === qNum);
                  const answered = isQuestionAnswered(ans);
                  return (
                    <Button
                      key={idx}
                      variant={currentQuestionIndex === idx ? 'default' : 'ghost'}
                      className={cn(
                        'w-full justify-between',
                        answered && currentQuestionIndex !== idx && 'bg-success/10 hover:bg-success/20'
                      )}
                      onClick={() => setCurrentQuestionIndex(idx)}
                    >
                      <span>Question {qNum}</span>
                      <div className="flex items-center gap-1">
                        {answered && <CheckCircle2 className="h-3 w-3" />}
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

      {/* ── Main content ──────────────────────────────────────────────── */}
      <div className="flex-1 space-y-4 flex flex-col min-h-0">
        {/* Exam header */}
        <Card className="flex-shrink-0">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-2xl">{exam.title}</CardTitle>
                {exam.description && <CardDescription className="mt-2">{exam.description}</CardDescription>}
              </div>
              <div className="text-right">
                <div className="text-sm text-muted-foreground">Total Marks</div>
                <div className="text-2xl font-bold">
                  {exam.totalPoints || exam.questions?.reduce((s: number, q: any) => s + (q.points || 0), 0) || 0}
                </div>
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* ── Full-exam Answer PDF upload ─────────────────────────────── */}
        <Card className="flex-shrink-0 border-primary/30 bg-primary/5">
          <CardContent className="p-4">
            <div className="flex items-start gap-4">
              <FileUp className="h-8 w-8 text-primary shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm">Upload Full Answer Sheet (PDF)</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Have all your answers in one document? Upload here (not under a single question). Use one PDF page per main question
                  (page&nbsp;1&nbsp;=&nbsp;Q1, page&nbsp;2&nbsp;=&nbsp;Q2, …), or a single page with clear headings such as{' '}
                  <span className="font-mono">1.</span>, <span className="font-mono">Question 2</span>, or{' '}
                  <span className="font-mono">Q3</span> on new lines. Typed PDFs are read directly; scans use OCR.
                </p>
                {fullAnswerPdf ? (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/20 text-sm flex-1 min-w-0">
                      <FileText className="h-4 w-4 text-primary shrink-0" />
                      <span className="truncate font-medium">{fullAnswerPdf.name}</span>
                      <span className="text-xs text-muted-foreground shrink-0">
                        ({(fullAnswerPdf.size / 1024).toFixed(0)} KB)
                      </span>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive hover:text-destructive"
                      onClick={() => {
                        setFullAnswerPdf(null);
                        setPdfPreview(null);
                        setPdfPreviewError(null);
                      }}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleSubmit}
                      disabled={submitMutation.isPending}
                    >
                      {submitMutation.isPending ? 'Submitting…' : 'Submit exam now'}
                    </Button>
                  </div>
                ) : (
                  <div className="mt-2">
                    <input
                      type="file"
                      accept=".pdf,application/pdf"
                      id="full-answer-pdf"
                      className="hidden"
                      onChange={handleFullPdfInput}
                    />
                    <label htmlFor="full-answer-pdf">
                      <Button size="sm" variant="outline" className="cursor-pointer" asChild>
                        <span>
                          <Upload className="h-3.5 w-3.5 mr-1.5" />
                          Choose PDF
                        </span>
                      </Button>
                    </label>
                  </div>
                )}

                {fullAnswerPdf && (
                  <div className="mt-3 space-y-2 border-t border-primary/15 pt-3">
                    <p className="text-xs font-medium text-foreground">Routing preview</p>
                    {pdfPreviewLoading && (
                      <p className="text-xs text-muted-foreground flex items-center gap-2">
                        <span className="h-3.5 w-3.5 border-2 border-primary/30 border-t-primary rounded-full animate-spin shrink-0" />
                        Analyzing PDF…
                      </p>
                    )}
                    {pdfPreviewError && (
                      <Alert variant="destructive" className="py-2">
                        <AlertTitle className="text-xs">Preview failed</AlertTitle>
                        <AlertDescription className="text-xs">{pdfPreviewError}</AlertDescription>
                      </Alert>
                    )}
                    {pdfPreview && !pdfPreviewLoading && (
                      <div className="rounded-md border bg-background/80 text-xs space-y-2 p-3">
                        <p className="text-muted-foreground leading-snug">{pdfPreview.summary}</p>
                        {pdfPreview.warnings.length > 0 && (
                          <Alert variant="default" className="py-2 border-amber-500/40 bg-amber-500/5">
                            <AlertTitle className="text-xs text-amber-900 dark:text-amber-200">
                              Heads up
                            </AlertTitle>
                            <AlertDescription className="text-xs text-amber-900/90 dark:text-amber-100/90">
                              <ul className="list-disc pl-4 space-y-0.5 mt-1">
                                {pdfPreview.warnings.map((w, i) => (
                                  <li key={i}>{w}</li>
                                ))}
                              </ul>
                            </AlertDescription>
                          </Alert>
                        )}
                        <ul className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                          {pdfPreview.rows.map((row, rowIdx) => (
                            <li
                              key={`pdf-preview-row-${rowIdx}-${row.questionNumber}-${row.source}`}
                              className="rounded border border-border/60 bg-muted/30 px-2 py-1.5"
                            >
                              <span className="font-semibold">{row.questionLabel}</span>
                              <span className="text-muted-foreground">
                                {' '}
                                ·{' '}
                                {row.source === 'missing_page'
                                  ? 'no page'
                                  : row.source === 'single_page_numbered_sections'
                                    ? 'from numbered sections'
                                    : row.source.replace(/^pdf_page_/, 'page ')}
                              </span>
                              {row.note && (
                                <span className="block text-amber-700 dark:text-amber-300 mt-0.5">
                                  {row.note}
                                </span>
                              )}
                              {row.subParts.length > 0 && (
                                <span className="block text-muted-foreground mt-0.5 pl-0">
                                  {row.subParts
                                    .map((sp) => {
                                      const label = sp.part ? `(${sp.part})` : 'Answer';
                                      const mode =
                                        sp.delivery === 'typed_text'
                                          ? 'typed'
                                          : 'OCR at submit';
                                      if (sp.chars != null) {
                                        return `${label} ~${sp.chars} chars · ${mode}`;
                                      }
                                      return `${label} · ${mode}`;
                                    })
                                    .join(' · ')}
                                </span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Question + answer area */}
        <ScrollArea className="flex-1 min-h-0">
          {currentQuestion && (
            <div className="pr-4 space-y-4 pb-4">
              {/* Question display (text, image, sub-question list) */}
              <QuestionDisplay
                questionNumber={currentQuestionNumber}
                questionText={currentQuestion.richContent || currentQuestion.text}
                questionPoints={currentQuestion.points || 0}
                attachments={currentQuestion.attachments}
                subQuestions={(currentQuestion.subQuestions ?? []).map((sq, si) => ({
                  id: sq.id,
                  number: sq.number ?? si + 1,
                  text: sq.text ?? '',
                  richContent: sq.richContent,
                  points: sq.points ?? 0,
                }))}
              />

              {/* Answer section */}
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
                          <Upload className="h-4 w-4 mr-2" />
                          Upload File
                        </TabsTrigger>
                      </TabsList>
                    </div>

                    {/* ── Typed answer tab ──────────────────────────── */}
                    <TabsContent value="typed" className="p-6 pt-4 space-y-6">
                      <p className="text-xs text-muted-foreground bg-muted/50 border border-border/50 rounded-md px-3 py-2">
                        <strong>Tip:</strong> Put each step on a new line or number steps (1. …, 2. …) so the system can score them accurately.
                      </p>
                      {hasSubQuestions ? (
                        /* Per-sub-question editors */
                        (currentQuestion.subQuestions as any[]).map((sub: any, idx: number) => {
                          const subAns = currentAnswer?.subAnswers.find(sa => sa.subQuestionId === sub.id);
                          return (
                            <div key={sub.id || idx} className="space-y-2">
                              {/* Sub-question label + text */}
                              <div className="flex gap-2 items-start px-1">
                                <span className="font-semibold text-primary shrink-0 pt-0.5">
                                  ({subLabel(idx)})
                                </span>
                                <div>
                                  <p className="text-sm font-medium">{sub.text}</p>
                                  <span className="text-xs text-muted-foreground">
                                    [{sub.points} {sub.points === 1 ? 'point' : 'points'}]
                                  </span>
                                </div>
                              </div>
                              {/* Answer editor for this sub-question */}
                              <AnswerEditor
                                key={`sub-editor-${sub.id}-${currentQuestion.id}`}
                                questionNumber={idx + 1}
                                questionText={sub.text}
                                questionPoints={sub.points || 1}
                                answer={subAns?.typedAnswer || ''}
                                placeholder={`Answer for part (${subLabel(idx)})…`}
                                onUpdate={(val) => updateSubAnswer(currentQuestion.id, sub.id, val)}
                              />
                            </div>
                          );
                        })
                      ) : (
                        /* Single editor for questions without sub-questions */
                        <AnswerEditor
                          key={`editor-${currentQuestion.id}`}
                          questionNumber={currentQuestionNumber}
                          questionText={currentQuestion.richContent || currentQuestion.text}
                          questionPoints={currentQuestion.points || 0}
                          answer={currentAnswer?.typedAnswer || ''}
                          onUpdate={(val) => updateParentAnswer(currentQuestion.id, currentQuestionNumber, val)}
                        />
                      )}
                    </TabsContent>

                    {/* ── Image / PDF upload tab ────────────────────── */}
                    <TabsContent value="upload" className="p-6 pt-4">
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-lg">Upload Handwritten Work</CardTitle>
                          <CardDescription>
                            {hasSubQuestions
                              ? 'Upload photos or a PDF of your handwritten answers for this question.'
                              : 'Upload a photo or PDF of your handwritten work for this question.'}
                            <span className="block mt-1 text-xs text-primary font-medium">
                              Tip: PDF uploads give better accuracy than phone photos.
                            </span>
                          </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div
                            onDrop={(e) => handleDrop(e, currentQuestion.id)}
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
                              accept="image/*,.pdf,application/pdf"
                              multiple
                              onChange={(e) => handleFileInput(e, currentQuestion.id)}
                              className="hidden"
                              id={`file-upload-${currentQuestion.id}`}
                            />
                            <label htmlFor={`file-upload-${currentQuestion.id}`} className="cursor-pointer">
                              <Upload className="h-10 w-10 text-muted-foreground mx-auto mb-4" />
                              <p className="font-medium mb-1">Drop files or click to upload</p>
                              <p className="text-sm text-muted-foreground">
                                JPG, PNG or PDF · Max 20 MB per file
                              </p>
                            </label>
                          </div>

                          {currentAnswer && currentAnswer.images.length > 0 && (
                            <div className="space-y-2">
                              <p className="text-sm font-medium">Uploaded ({currentAnswer.images.length})</p>
                              <div className="grid grid-cols-2 gap-3">
                                {currentAnswer.images.map((file, imgIdx) => {
                                  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
                                  return (
                                    <div
                                      key={imgIdx}
                                      className="relative group rounded-lg border bg-muted/50 overflow-hidden"
                                    >
                                      {isPdf ? (
                                        <div className="flex flex-col items-center justify-center h-32 gap-2 bg-red-50">
                                          <FileText className="h-10 w-10 text-red-500" />
                                          <span className="text-xs text-red-700 font-medium">PDF</span>
                                        </div>
                                      ) : (
                                        <img
                                          src={URL.createObjectURL(file)}
                                          alt={`Upload ${imgIdx + 1}`}
                                          className="w-full h-32 object-cover"
                                        />
                                      )}
                                      <div className="absolute inset-0 bg-foreground/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                        <Button
                                          variant="destructive"
                                          size="icon"
                                          className="h-8 w-8"
                                          onClick={() => removeImage(currentQuestion.id, imgIdx)}
                                        >
                                          <X className="h-4 w-4" />
                                        </Button>
                                      </div>
                                      <div className="p-2">
                                        <p className="text-xs truncate">{file.name}</p>
                                        {isPdf && (
                                          <p className="text-xs text-muted-foreground">
                                            {(file.size / 1024).toFixed(0)} KB
                                          </p>
                                        )}
                                      </div>
                                    </div>
                                  );
                                })}
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

        {/* Navigation */}
        <div className="flex justify-between items-center pt-2 border-t flex-shrink-0 gap-2 flex-wrap">
          <Button
            variant="outline"
            onClick={() => setCurrentQuestionIndex(Math.max(0, currentQuestionIndex - 1))}
            disabled={currentQuestionIndex === 0}
          >
            Previous
          </Button>

          <div className="text-sm text-muted-foreground order-last sm:order-none w-full sm:w-auto text-center sm:text-left">
            Question {currentQuestionIndex + 1} of {totalQuestions}
          </div>

          <div className="flex gap-2 items-center">
            {canSubmit && !isLastQuestion && (
              <Button
                onClick={handleSubmit}
                disabled={submitMutation.isPending}
                className="min-w-[130px]"
                variant="secondary"
              >
                {submitMutation.isPending ? (
                  <>
                    <div className="h-4 w-4 border-2 border-secondary-foreground/30 border-t-secondary-foreground rounded-full animate-spin mr-2" />
                    Submitting…
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Submit exam
                  </>
                )}
              </Button>
            )}
            {!isLastQuestion ? (
              <Button onClick={() => setCurrentQuestionIndex(currentQuestionIndex + 1)}>
                Next <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                disabled={submitMutation.isPending || !canSubmit}
                className="min-w-[150px]"
              >
                {submitMutation.isPending ? (
                  <>
                    <div className="h-4 w-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin mr-2" />
                    Submitting…
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
    </div>
  );
}
