import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AnswerEditor } from '@/components/exam-taker/AnswerEditor';
import { QuestionDisplay, type SubQuestion } from '@/components/exam-taker/QuestionDisplay';
import { RichContentViewer } from '@/components/exam-taker/RichContentViewer';
import { MathText } from '@/components/ui/MathText';
import {
  Upload,
  X,
  CheckCircle2,
  FileText,
  AlertCircle,
  ChevronRight,
  ChevronLeft,
  FileUp,
  Eye,
  RefreshCw,
  Bookmark,
  Eraser,
  Send,
  Info,
  BookOpen,
  Image as ImageIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';
import { examsAPI, submissionsAPI, type AnswerPdfPreviewResponse } from '@/lib/api';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { questionOutlineLabel } from '@/components/exam-builder/questionOutlineLabel';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

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
type TakeExamSubQuestion = SubQuestion;

interface TakeExamPayload {
  title: string;
  description?: string | null;
  totalPoints?: number;
  questions?: {
    id: string;
    number?: number;
    points?: number;
    text?: string;
    outlineTitle?: string | null;
    richContent?: string;
    attachments?: Array<{
      id: string;
      filePath: string;
      filename: string;
      attachmentType?: string;
    }>;
    subQuestions?: TakeExamSubQuestion[];
  }[];
}

// ── Helpers ────────────────────────────────────────────────────────────────

const subLabel = (idx: number) => String.fromCharCode(97 + idx); // a, b, c, …

function displaySubLabel(sub: { outlineTitle?: string | null }, idx: number): string {
  const title = sub.outlineTitle?.trim();
  if (title) return title;
  return subLabel(idx);
}

function questionPointsDisplay(q: { points?: number; subQuestions?: { points?: number; subQuestions?: { points?: number }[] }[] }): number {
  const subs = q.subQuestions ?? [];
  if (subs.length > 0) return subs.reduce((s, sq) => s + questionPointsDisplay(sq), 0);
  return q.points ?? 0;
}

function isQuestionAnswered(ans: Answer | undefined): boolean {
  if (!ans) return false;
  if (ans.images.length > 0) return true;
  if (ans.subAnswers.length > 0) return ans.subAnswers.some(sa => sa.typedAnswer.trim() !== '');
  return ans.typedAnswer.trim() !== '';
}

/** PDF preview row implies this main question will receive content on submit (typed or image). */
function pdfPreviewRowIndicatesCapture(
  row: AnswerPdfPreviewResponse['rows'][number] | undefined
): boolean {
  if (!row || row.source === 'missing_page') return false;
  if (row.source === 'multi_section_split' || row.source?.startsWith('pdf_page_')) {
    return true;
  }
  if ((row.answerExcerpt || '').trim().length > 0) return true;
  if (row.subParts.length === 0) return false;
  return row.subParts.some(
    (sp) =>
      sp.delivery === 'ocr_image' ||
      sp.hasContent === true ||
      (typeof sp.chars === 'number' && sp.chars > 0)
  );
}

function buildPartsFromPdfPreviewRow(
  row: AnswerPdfPreviewResponse['rows'][number]
): { key: string; label: string; body: string }[] {
  const excerpt = (row.answerExcerpt || '').trim();
  const pageHint =
    row.pdfPage != null ? ` (PDF page ${row.pdfPage})` : '';
  const out: { key: string; label: string; body: string }[] = [];
  row.subParts.forEach((sp, i) => {
    const key = `pdf-${row.questionNumber}-${sp.part ?? i}`;
    const label =
      sp.part != null
        ? `Part (${sp.part})${pageHint}`
        : row.subParts.length > 1
          ? `Part ${i + 1}${pageHint}`
          : `Answer PDF (auto-routed)${pageHint}`;
    let body: string;
    if (sp.delivery === 'ocr_image') {
      body =
        'Scanned or handwritten work will be submitted as an image for this part. Compare the text below to your original PDF if anything looks wrong.';
    } else if (typeof sp.chars === 'number' && sp.chars > 0) {
      body = `Detected ~${sp.chars} characters of readable text from your answer PDF for this question.`;
    } else if (sp.hasContent === true) {
      body = 'Content from your answer PDF will be included for this question when you submit.';
    } else {
      body = 'Your full answer PDF is mapped to this question (see the PDF routing summary on the exam page).';
    }
    if (excerpt && i === 0) {
      body = `Text read from your PDF (approximate — verify against your scan):\n\n${excerpt}\n\n—\n\n${body}`;
    }
    out.push({ key, label, body });
  });
  return out;
}

function reviewQuestionTitle(q: { outlineTitle?: string | null; text?: string }, qNum: number): string {
  const outline = q.outlineTitle?.trim();
  if (outline) return outline;
  const text = typeof q.text === 'string' ? q.text : '';
  const fromLabel = questionOutlineLabel({ text, outlineTitle: '' }).trim();
  if (fromLabel) return fromLabel.length > 90 ? `${fromLabel.slice(0, 87)}…` : fromLabel;
  return `Question ${qNum}`;
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
  const fullPdfInputRef = useRef<HTMLInputElement>(null);
  const [fullPdfViewerOpen, setFullPdfViewerOpen] = useState(false);
  const [visitedQuestionIndices, setVisitedQuestionIndices] = useState<Set<number>>(() => new Set([0]));
  const [markedForReview, setMarkedForReview] = useState<Set<number>>(() => new Set());
  const [elapsedSec, setElapsedSec] = useState(0);
  const [leaveOpen, setLeaveOpen] = useState(false);
  const [reviewSubmitOpen, setReviewSubmitOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [instructionsOpen, setInstructionsOpen] = useState(false);
  const [pdfSectionOpen, setPdfSectionOpen] = useState(false);

  const fullAnswerPdfObjectUrl = useMemo(() => {
    if (!fullAnswerPdf) return null;
    return URL.createObjectURL(fullAnswerPdf);
  }, [fullAnswerPdf]);

  useEffect(() => {
    return () => {
      if (fullAnswerPdfObjectUrl) URL.revokeObjectURL(fullAnswerPdfObjectUrl);
    };
  }, [fullAnswerPdfObjectUrl]);

  useEffect(() => {
    setVisitedQuestionIndices((prev) => new Set(prev).add(currentQuestionIndex));
  }, [currentQuestionIndex]);

  useEffect(() => {
    const t = window.setInterval(() => setElapsedSec((s) => s + 1), 1000);
    return () => window.clearInterval(t);
  }, []);

  useEffect(() => {
    if (fullAnswerPdf) setPdfSectionOpen(true);
  }, [fullAnswerPdf]);

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
      toast({
        title: 'Submission successful!',
        description: 'Your answers are being graded automatically.',
      });
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
    e.target.value = '';
  };

  const triggerFullPdfPicker = () => fullPdfInputRef.current?.click();

  const removeImage = (questionId: string, imgIdx: number) => {
    setAnswers(prev => prev.map(a =>
      a.questionId === questionId ? { ...a, images: a.images.filter((_, i) => i !== imgIdx) } : a
    ));
  };

  const overviewStats = useMemo(() => {
    if (!exam?.questions?.length) return null;
    const n = exam.questions.length;
    let answered = 0;
    let notAnsweredVisited = 0;
    for (let i = 0; i < n; i++) {
      const q = exam.questions[i];
      const qNum = q.number || i + 1;
      const ans = answers.find((a) => a.questionId === q.id || a.questionNumber === qNum);
      const previewRow = pdfPreview?.rows.find((r) => r.questionNumber === qNum);
      const fromFullPdf =
        !!fullAnswerPdf &&
        !!pdfPreview &&
        !pdfPreviewLoading &&
        pdfPreviewRowIndicatesCapture(previewRow);
      const ok = isQuestionAnswered(ans) || fromFullPdf;
      if (ok) answered++;
      else if (visitedQuestionIndices.has(i)) notAnsweredVisited++;
    }
    return {
      total: n,
      visited: visitedQuestionIndices.size,
      answered,
      notVisited: Math.max(0, n - visitedQuestionIndices.size),
      notAnswered: notAnsweredVisited,
      marked: [...markedForReview].filter((i) => i < n).length,
      hasFullPdf: !!fullAnswerPdf,
      pdfPreviewLoading: !!fullAnswerPdf && pdfPreviewLoading,
    };
  }, [
    exam,
    answers,
    visitedQuestionIndices,
    markedForReview,
    fullAnswerPdf,
    pdfPreview,
    pdfPreviewLoading,
  ]);

  const reviewAnswerSummaries = useMemo(() => {
    if (!exam?.questions?.length) return [];
    return exam.questions.map((q: any, idx: number) => {
      const qNum = q.number || idx + 1;
      const ans = answers.find((a) => a.questionId === q.id || a.questionNumber === qNum);
      const previewRow = pdfPreview?.rows.find((r) => r.questionNumber === qNum);
      const fromFullPdf =
        !!fullAnswerPdf &&
        !!pdfPreview &&
        !pdfPreviewLoading &&
        pdfPreviewRowIndicatesCapture(previewRow);
      const subs = q.subQuestions ?? [];
      const title = reviewQuestionTitle(q, qNum);
      const parts: { key: string; label: string; body: string }[] = [];
      if (subs.length > 0 && ans) {
        subs.forEach((sub: any, si: number) => {
          const sa = ans.subAnswers.find((s: SubAnswer) => s.subQuestionId === sub.id);
          const body = (sa?.typedAnswer || '').trim();
          parts.push({
            key: String(sub.id ?? si),
            label: `Part ${displaySubLabel(sub, si)}`,
            body,
          });
        });
      } else if (ans && (ans.typedAnswer || '').trim()) {
        parts.push({ key: 'typed', label: 'Typed answer', body: ans.typedAnswer.trim() });
      }
      const hasTypedContent = parts.some((p) => (p.body || '').trim() !== '');
      if (
        !hasTypedContent &&
        fromFullPdf &&
        previewRow &&
        previewRow.subParts.length > 0
      ) {
        parts.length = 0;
        parts.push(...buildPartsFromPdfPreviewRow(previewRow));
      }
      const files = ans?.images ?? [];
      return {
        index: idx,
        qNum,
        title,
        parts,
        files,
        answered: isQuestionAnswered(ans) || fromFullPdf,
        marked: markedForReview.has(idx),
      };
    });
  }, [exam, answers, markedForReview, fullAnswerPdf, pdfPreview, pdfPreviewLoading]);

  const clearCurrentResponse = useCallback(() => {
    if (!exam?.questions?.length) return;
    const q = exam.questions[currentQuestionIndex];
    if (!q?.id) return;
    const qid = q.id;
    setAnswers((prev) =>
      prev.map((a) =>
        a.questionId === qid
          ? {
              ...a,
              typedAnswer: '',
              subAnswers: a.subAnswers.map((sa) => ({ ...sa, typedAnswer: '' })),
              images: [],
            }
          : a
      )
    );
  }, [exam, currentQuestionIndex]);

  const toggleMarkReview = useCallback(() => {
    setMarkedForReview((prev) => {
      const next = new Set(prev);
      if (next.has(currentQuestionIndex)) next.delete(currentQuestionIndex);
      else next.add(currentQuestionIndex);
      return next;
    });
  }, [currentQuestionIndex]);

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
  const canSubmit = answers.some(isQuestionAnswered) || !!fullAnswerPdf;
  const totalQuestions = exam.questions?.length || 0;
  const isLastQuestion = totalQuestions === 0 || currentQuestionIndex >= totalQuestions - 1;

  const h = Math.floor(elapsedSec / 3600);
  const m = Math.floor((elapsedSec % 3600) / 60);
  const s = elapsedSec % 60;

  const paletteClass = (idx: number) => {
    const q = exam.questions![idx];
    const qNum = q.number || idx + 1;
    const ans = answers.find((a) => a.questionId === q.id || a.questionNumber === qNum);
    const answered = isQuestionAnswered(ans);
    const isCurrent = idx === currentQuestionIndex;
    const marked = markedForReview.has(idx);
    const visited = visitedQuestionIndices.has(idx);
    if (isCurrent) {
      return cn(
        'h-9 w-9 rounded-md border-2 border-sky-700 bg-white text-sm font-semibold text-sky-950 tabular-nums shadow-sm ring-2 ring-sky-400/40 ring-offset-2 ring-offset-background transition-colors dark:border-sky-400 dark:bg-slate-950 dark:text-sky-50 dark:ring-sky-500/30'
      );
    }
    if (marked) {
      return 'h-9 w-9 rounded-md border border-violet-400 bg-violet-100 text-sm font-semibold text-violet-900 tabular-nums transition-colors dark:border-violet-600 dark:bg-violet-950/50 dark:text-violet-100';
    }
    if (answered) {
      return 'h-9 w-9 rounded-md border border-emerald-400 bg-emerald-50 text-sm font-semibold text-emerald-900 tabular-nums transition-colors dark:border-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-100';
    }
    if (visited) {
      return 'h-9 w-9 rounded-md border border-amber-300/90 bg-amber-50 text-sm font-medium text-amber-950 tabular-nums transition-colors dark:border-amber-800 dark:bg-amber-950/35 dark:text-amber-100';
    }
    return 'h-9 w-9 rounded-md border border-slate-200 bg-slate-100 text-sm font-medium text-slate-600 tabular-nums transition-colors hover:bg-slate-200/80 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-800';
  };

  const goNext = () => {
    if (currentQuestionIndex < totalQuestions - 1) {
      setCurrentQuestionIndex((i) => i + 1);
    }
  };

  return (
    <>
      <div className="flex min-h-[calc(100vh-5.5rem)] flex-col gap-3">
        <header className="flex flex-shrink-0 flex-col gap-3 rounded-xl border border-slate-200/90 bg-white px-4 py-3 shadow-sm dark:border-slate-800 dark:bg-slate-950 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <span className="truncate font-semibold text-foreground">{exam.title}</span>
              <ChevronRight className="h-4 w-4 shrink-0 opacity-50" aria-hidden />
              <span className="tabular-nums text-muted-foreground">
                Q{currentQuestionNumber} · {currentQuestionIndex + 1} / {totalQuestions}
              </span>
              <span className="hidden text-muted-foreground/80 sm:inline">·</span>
              <span className="hidden text-xs text-muted-foreground sm:inline">
                {exam.totalPoints ||
                  exam.questions?.reduce((acc: number, q: { points?: number }) => acc + (q.points || 0), 0) ||
                  0}{' '}
                pts total
              </span>
            </div>
          </div>
          <div className="flex flex-shrink-0 flex-wrap items-center justify-end gap-2">
            <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setLeaveOpen(true)}>
              Leave
            </Button>
            <Button
              size="sm"
              className="rounded-lg bg-slate-900 px-4 text-white shadow-sm hover:bg-slate-800 dark:bg-sky-700 dark:hover:bg-sky-600"
              onClick={() => setReviewSubmitOpen(true)}
              disabled={submitMutation.isPending}
            >
              <Send className="mr-2 h-4 w-4" />
              Review & submit
            </Button>
          </div>
        </header>

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 lg:grid-cols-[minmax(200px,228px)_1fr_minmax(220px,272px)] lg:gap-4">
          <aside className="order-2 flex max-h-[200px] flex-col overflow-hidden rounded-xl border border-slate-200/90 bg-slate-50/90 dark:border-slate-800 dark:bg-slate-900/50 lg:order-1 lg:max-h-none">
            <div className="border-b border-slate-200/80 px-3 py-2.5 dark:border-slate-800">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Palette</p>
              <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <span className="h-2 w-2 rounded-sm bg-emerald-500" />
                  Answered
                </span>
                <span className="inline-flex items-center gap-1">
                  <span className="h-2 w-2 rounded-sm bg-violet-500" />
                  Marked
                </span>
                <span className="inline-flex items-center gap-1">
                  <span className="h-2 w-2 rounded-sm bg-amber-400" />
                  Visited
                </span>
                <span className="inline-flex items-center gap-1">
                  <span className="h-2 w-2 rounded-sm bg-slate-300 dark:bg-slate-600" />
                  New
                </span>
              </div>
            </div>
            <ScrollArea className="min-h-0 flex-1">
              <div className="grid grid-cols-8 gap-2 p-3 sm:grid-cols-10 lg:grid-cols-5">
                {exam.questions?.map((question: any, idx: number) => {
                  const qNum = question.number || idx + 1;
                  return (
                    <button
                      key={question.id || idx}
                      type="button"
                      className={paletteClass(idx)}
                      aria-current={idx === currentQuestionIndex ? 'step' : undefined}
                      onClick={() => setCurrentQuestionIndex(idx)}
                    >
                      {qNum}
                    </button>
                  );
                })}
              </div>
            </ScrollArea>
          </aside>

          <main className="order-3 flex min-h-0 min-w-0 flex-col gap-3 lg:order-2">
        {/* ── Full-exam Answer PDF upload ─────────────────────────────── */}
        <Collapsible open={pdfSectionOpen} onOpenChange={setPdfSectionOpen} className="flex-shrink-0">
          <div className="rounded-xl border border-violet-200/60 bg-violet-50/50 dark:border-violet-900/50 dark:bg-violet-950/25">
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm font-semibold text-violet-950 dark:text-violet-100"
              >
                <span className="flex items-center gap-2">
                  <FileUp className="h-4 w-4 shrink-0" />
                  Answer PDF (optional)
                </span>
                <ChevronRight
                  className={cn('h-4 w-4 shrink-0 transition-transform', pdfSectionOpen && 'rotate-90')}
                />
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <Card className="border-0 bg-transparent shadow-none">
                <CardContent className="border-t border-violet-200/50 p-4 pt-3 dark:border-violet-900/40">
            <div className="flex items-start gap-3">
              <FileText className="h-6 w-6 shrink-0 text-violet-600 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-muted-foreground leading-snug">
                  One file for the whole exam — not per question. Label pages or sections clearly{' '}
                  <span className="font-mono text-[11px]">(Q1, Q2…)</span>. PDFs with real text use that text;
                  photo scans run OCR on submit. Handwriting is much harder than machine-printed PDFs — use{' '}
                  <strong className="font-medium text-foreground">Type Answer</strong> when you need reliable grading.
                </p>
                <input
                  ref={fullPdfInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  onChange={handleFullPdfInput}
                />
                {fullAnswerPdf ? (
                  <div className="mt-3 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-primary/20 bg-primary/10 px-3 py-2 text-sm">
                        <FileText className="h-4 w-4 shrink-0 text-primary" />
                        <span className="truncate font-medium">{fullAnswerPdf.name}</span>
                        <span className="shrink-0 text-xs text-muted-foreground">
                          ({(fullAnswerPdf.size / 1024).toFixed(0)} KB)
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="border-violet-300 font-medium"
                          onClick={() => setFullPdfViewerOpen(true)}
                        >
                          <Eye className="mr-1.5 h-4 w-4" />
                          Preview
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="font-medium"
                          onClick={triggerFullPdfPicker}
                        >
                          <RefreshCw className="mr-1.5 h-4 w-4" />
                          Replace PDF
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => {
                            setFullAnswerPdf(null);
                            setPdfPreview(null);
                            setPdfPreviewError(null);
                          }}
                        >
                          <X className="mr-1 h-4 w-4" />
                          Remove
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => setReviewSubmitOpen(true)}
                          disabled={submitMutation.isPending}
                        >
                          Review & submit
                        </Button>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Preview in browser · <strong>Replace</strong> before submit if needed
                    </p>
                  </div>
                ) : (
                  <div className="mt-2">
                    <Button type="button" size="sm" variant="outline" className="cursor-pointer" onClick={triggerFullPdfPicker}>
                      <Upload className="mr-1.5 h-3.5 w-3.5" />
                      Choose PDF
                    </Button>
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
                                  : row.source === 'single_page_numbered_sections' ||
                                      row.source === 'multi_section_split'
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
            </CollapsibleContent>
          </div>
        </Collapsible>

        {/* Question + answer area */}
        <ScrollArea className="min-h-0 flex-1 rounded-xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
          {currentQuestion && (
            <div className="space-y-4 p-4 pb-6 sm:p-5">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-3 dark:border-border/50">
                <p className="text-sm font-semibold text-foreground">
                  Q{currentQuestionNumber}
                  <span className="ml-2 font-normal text-muted-foreground">
                    ({questionPointsDisplay(currentQuestion)} pts)
                  </span>
                </p>
                <Button
                  type="button"
                  variant="link"
                  size="sm"
                  className="h-auto p-0 text-xs text-muted-foreground"
                  onClick={() =>
                    toast({
                      title: 'Thanks for the heads-up',
                      description: 'Tell your instructor if a question looks wrong. You can still continue the exam.',
                    })
                  }
                >
                  Report issue
                </Button>
              </div>
              <QuestionDisplay
                questionNumber={currentQuestionNumber}
                questionText={currentQuestion.richContent || currentQuestion.text}
                questionPoints={questionPointsDisplay(currentQuestion)}
                outlineTitle={currentQuestion.outlineTitle}
                attachments={currentQuestion.attachments}
                showQuestionHeader={false}
                subQuestions={(currentQuestion.subQuestions ?? []).map((sq, si) => ({
                  id: sq.id,
                  number: sq.number ?? si + 1,
                  text: sq.text ?? '',
                  richContent: sq.richContent,
                  points: sq.points ?? 0,
                  outlineTitle: sq.outlineTitle,
                  subQuestions: sq.subQuestions,
                }))}
              />

              {/* Answer section */}
              <Card className="rounded-xl border-slate-200/90 shadow-sm dark:border-slate-800">
                <CardContent className="p-0">
                  <Tabs value={currentTab} onValueChange={setCurrentTab}>
                    <div className="border-b border-border/60 px-4 pt-3 dark:border-border/50 sm:px-6 sm:pt-4">
                      <TabsList className="grid h-auto w-full max-w-md grid-cols-2 gap-0 rounded-none border-0 bg-transparent p-0">
                        <TabsTrigger
                          value="typed"
                          className="rounded-none border-b-2 border-transparent py-2.5 text-sm shadow-none data-[state=active]:border-slate-900 data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none dark:data-[state=active]:border-sky-500"
                        >
                          <FileText className="mr-2 h-4 w-4" />
                          Type answer
                        </TabsTrigger>
                        <TabsTrigger
                          value="upload"
                          className="rounded-none border-b-2 border-transparent py-2.5 text-sm shadow-none data-[state=active]:border-slate-900 data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none dark:data-[state=active]:border-sky-500"
                        >
                          <Upload className="mr-2 h-4 w-4" />
                          Upload file
                        </TabsTrigger>
                      </TabsList>
                    </div>

                    {/* ── Typed answer tab ──────────────────────────── */}
                    <TabsContent value="typed" className="p-6 pt-4 space-y-6">
                      <p className="text-xs text-muted-foreground bg-muted/50 border border-border/50 rounded-md px-3 py-2">
                        <strong>Tip:</strong> Put each step on a new line or number steps (1. …, 2. …) so the system can score them accurately.
                        If you paste or upload a <strong className="font-medium text-foreground">whole answer sheet</strong> in one
                        question, label sections clearly{' '}
                        <span className="font-mono text-[11px]">(Question 1, Q2, 3., …)</span>
                        — on submit, answers are routed to the matching questions when the layout is clear.
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
                                  {displaySubLabel(sub, idx)}
                                </span>
                                <div className="flex-1 min-w-0">
                                  <RichContentViewer
                                    content={sub.richContent || sub.text}
                                    className="text-sm"
                                  />
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
                                placeholder={`Answer for part ${displaySubLabel(sub, idx)}…`}
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
                              Typed answers grade most reliably. Scanned handwriting is read with OCR and may misread symbols.
                              A <strong className="font-medium text-foreground">single photo or PDF</strong> of every answer can be
                              split across questions when sections are labeled{' '}
                              <span className="font-mono text-[11px]">(Q1, Q2…)</span>.
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

        <div className="flex flex-shrink-0 flex-col gap-2 rounded-xl border border-slate-200/90 bg-slate-50/90 p-3 dark:border-slate-800 dark:bg-slate-900/40 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className={cn(
                'rounded-lg border-violet-300 bg-white dark:border-violet-800 dark:bg-slate-950',
                markedForReview.has(currentQuestionIndex) && 'border-violet-600 bg-violet-50 dark:bg-violet-950/40'
              )}
              onClick={toggleMarkReview}
            >
              <Bookmark className="mr-2 h-4 w-4" />
              {markedForReview.has(currentQuestionIndex) ? 'Marked' : 'Mark for review'}
            </Button>
            <Button type="button" variant="outline" size="sm" className="rounded-lg" onClick={clearCurrentResponse}>
              <Eraser className="mr-2 h-4 w-4" />
              Clear response
            </Button>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="rounded-lg"
              onClick={() => setCurrentQuestionIndex(Math.max(0, currentQuestionIndex - 1))}
              disabled={currentQuestionIndex === 0}
            >
              <ChevronLeft className="mr-1 h-4 w-4" />
              Previous
            </Button>
            {!isLastQuestion ? (
              <Button
                type="button"
                size="sm"
                className="rounded-lg bg-slate-900 text-white hover:bg-slate-800 dark:bg-sky-700 dark:hover:bg-sky-600"
                onClick={goNext}
              >
                Skip & next
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            ) : (
              <Button
                type="button"
                size="sm"
                className="rounded-lg bg-slate-900 text-white hover:bg-slate-800 dark:bg-sky-700 dark:hover:bg-sky-600"
                onClick={() => setReviewSubmitOpen(true)}
                disabled={submitMutation.isPending}
              >
                Finish & review
                <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </main>

      <aside className="order-4 flex flex-col gap-3 lg:order-3">
        <Card className="border-slate-200/90 shadow-sm dark:border-slate-800">
          <CardContent className="p-4 pt-5">
            <p className="text-center text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              Time in exam
            </p>
            <div className="mt-3 flex items-end justify-center gap-1.5 tabular-nums sm:gap-2">
              <div className="text-center">
                <p className="text-2xl font-bold leading-none text-slate-900 dark:text-slate-50 sm:text-3xl">
                  {String(h).padStart(2, '0')}
                </p>
                <p className="mt-1 text-[10px] text-muted-foreground">Hrs</p>
              </div>
              <span className="pb-5 text-lg font-light text-muted-foreground sm:pb-6 sm:text-xl">:</span>
              <div className="text-center">
                <p className="text-2xl font-bold leading-none text-slate-900 dark:text-slate-50 sm:text-3xl">
                  {String(m).padStart(2, '0')}
                </p>
                <p className="mt-1 text-[10px] text-muted-foreground">Min</p>
              </div>
              <span className="pb-5 text-lg font-light text-muted-foreground sm:pb-6 sm:text-xl">:</span>
              <div className="text-center">
                <p className="text-2xl font-bold leading-none text-slate-900 dark:text-slate-50 sm:text-3xl">
                  {String(s).padStart(2, '0')}
                </p>
                <p className="mt-1 text-[10px] text-muted-foreground">Sec</p>
              </div>
            </div>
            <p className="mt-3 text-center text-[10px] text-muted-foreground">Elapsed — not a countdown</p>
          </CardContent>
        </Card>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="flex-1 rounded-lg text-xs"
            onClick={() => setAboutOpen(true)}
          >
            <Info className="mr-1 h-3.5 w-3.5 shrink-0" />
            About
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="flex-1 rounded-lg text-xs"
            onClick={() => setInstructionsOpen(true)}
          >
            <BookOpen className="mr-1 h-3.5 w-3.5 shrink-0" />
            Tips
          </Button>
        </div>
        <Card className="border-slate-200/90 shadow-sm dark:border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-0 px-4 pb-4 text-sm">
            {overviewStats && (
              <>
                <div className="flex justify-between gap-2 border-b border-border/50 py-2 dark:border-border/40">
                  <span className="text-muted-foreground">Total</span>
                  <span className="font-semibold tabular-nums">{overviewStats.total}</span>
                </div>
                <div className="flex justify-between gap-2 border-b border-border/50 py-2 dark:border-border/40">
                  <span className="text-muted-foreground">Visited</span>
                  <span className="font-semibold tabular-nums">{overviewStats.visited}</span>
                </div>
                <div className="flex justify-between gap-2 border-b border-border/50 py-2 dark:border-border/40">
                  <span className="text-muted-foreground">Not visited</span>
                  <span className="font-semibold tabular-nums">{overviewStats.notVisited}</span>
                </div>
                <div className="flex justify-between gap-2 border-b border-border/50 py-2 dark:border-border/40">
                  <span className="text-muted-foreground">Answered</span>
                  <span className="font-semibold tabular-nums">{overviewStats.answered}</span>
                </div>
                <div className="flex justify-between gap-2 border-b border-border/50 py-2 dark:border-border/40">
                  <span className="text-muted-foreground">Not answered</span>
                  <span className="font-semibold tabular-nums">{overviewStats.notAnswered}</span>
                </div>
                <div className="flex justify-between gap-2 border-b border-border/50 py-2 dark:border-border/40">
                  <span className="text-muted-foreground">Marked</span>
                  <span className="font-semibold tabular-nums">{overviewStats.marked}</span>
                </div>
                <div className="flex flex-col gap-0.5 py-2">
                  <div className="flex justify-between gap-2">
                    <span className="text-muted-foreground">Answer PDF</span>
                    <span className="font-semibold">{overviewStats.hasFullPdf ? 'Yes' : '—'}</span>
                  </div>
                  {overviewStats.hasFullPdf && overviewStats.pdfPreviewLoading ? (
                    <p className="text-xs text-amber-800 dark:text-amber-200/90">
                      Mapping pages to your exam questions…
                    </p>
                  ) : null}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </aside>
        </div>
      </div>

    <AlertDialog open={leaveOpen} onOpenChange={setLeaveOpen}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Leave this exam?</AlertDialogTitle>
          <AlertDialogDescription>
            Your work is kept in this browser until you submit. You can return from My exams if the exam is still open.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Stay</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            onClick={() => navigate('/my-exams')}
          >
            Leave
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <Dialog open={reviewSubmitOpen} onOpenChange={setReviewSubmitOpen}>
      <DialogContent className="flex h-[min(88vh,820px)] w-[min(100vw-1rem,40rem)] max-w-none translate-x-[-50%] translate-y-[-50%] flex-col gap-0 overflow-hidden p-0 sm:h-[min(88vh,820px)] sm:w-full sm:max-w-3xl">
        <DialogHeader className="shrink-0 space-y-1 border-b border-border/60 px-6 py-4 pr-14 text-left">
          <DialogTitle className="text-xl">Review your work</DialogTitle>
          <DialogDescription>
            Confirm each answer below. You can jump back to edit a question before submitting.
          </DialogDescription>
        </DialogHeader>

        {pdfPreviewError && fullAnswerPdf ? (
          <div className="shrink-0 border-b border-amber-200/80 bg-amber-50/90 px-6 py-3 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/35 dark:text-amber-100">
            PDF routing preview failed ({pdfPreviewError}). Your answer PDF will still be submitted; confirm with your instructor if answers do not line up with questions.
          </div>
        ) : null}

        {overviewStats && (
          <div className="shrink-0 border-b border-border/50 bg-muted/35 px-6 py-3 dark:bg-muted/20">
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary" className="rounded-md px-2.5 py-0.5 font-normal tabular-nums">
                {overviewStats.answered} answered
              </Badge>
              <Badge variant="outline" className="rounded-md px-2.5 py-0.5 font-normal tabular-nums text-muted-foreground">
                {overviewStats.total - overviewStats.answered} empty
              </Badge>
              {overviewStats.marked > 0 ? (
                <Badge variant="outline" className="rounded-md border-violet-300 bg-violet-50 px-2.5 py-0.5 font-normal dark:border-violet-800 dark:bg-violet-950/40">
                  {overviewStats.marked} marked for review
                </Badge>
              ) : null}
              {overviewStats.hasFullPdf ? (
                <Badge variant="outline" className="rounded-md border-amber-300/80 bg-amber-50 px-2.5 py-0.5 font-normal dark:border-amber-900 dark:bg-amber-950/30">
                  Answer PDF: {fullAnswerPdf?.name ?? 'attached'}
                </Badge>
              ) : null}
              {overviewStats.hasFullPdf && overviewStats.pdfPreviewLoading ? (
                <Badge variant="outline" className="rounded-md font-normal">
                  PDF routing…
                </Badge>
              ) : null}
            </div>
          </div>
        )}

        <ScrollArea className="min-h-0 flex-1">
          <div className="space-y-3 px-6 py-4">
            {reviewAnswerSummaries.map((item) => (
              <div
                key={item.index}
                className={cn(
                  'rounded-xl border bg-card p-4 shadow-sm transition-colors',
                  item.answered
                    ? 'border-emerald-200/80 dark:border-emerald-900/50'
                    : 'border-border/70 dark:border-border/60',
                  item.marked && 'ring-1 ring-violet-400/50 dark:ring-violet-600/40'
                )}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="inline-flex h-7 min-w-[2rem] items-center justify-center rounded-md bg-slate-900 px-2 text-xs font-bold text-white dark:bg-sky-700">
                        Q{item.qNum}
                      </span>
                      {item.answered ? (
                        <Badge className="border-0 bg-emerald-600 text-white hover:bg-emerald-600">Has answer</Badge>
                      ) : (
                        <Badge variant="secondary">No answer</Badge>
                      )}
                      {item.marked ? (
                        <Badge variant="outline" className="border-violet-400 text-violet-900 dark:text-violet-100">
                          Marked
                        </Badge>
                      ) : null}
                    </div>
                    <p className="text-sm font-medium leading-snug text-foreground">{item.title}</p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="shrink-0 text-slate-700 hover:bg-slate-100 dark:text-sky-300 dark:hover:bg-sky-950/50"
                    onClick={() => {
                      setCurrentQuestionIndex(item.index);
                      setReviewSubmitOpen(false);
                    }}
                  >
                    Edit
                  </Button>
                </div>

                {item.parts.length > 0 ? (
                  <div className="mt-3 space-y-3">
                    {item.parts.map((part) => (
                      <div key={part.key}>
                        <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                          {part.label}
                        </p>
                        {part.body ? (
                          <div className="max-h-40 overflow-y-auto rounded-lg border border-border/60 bg-muted/30 px-3 py-2.5 dark:bg-muted/20">
                            <div className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-foreground">
                              <MathText text={part.body} />
                            </div>
                          </div>
                        ) : (
                          <p className="rounded-lg border border-dashed border-border/70 bg-muted/15 px-3 py-2 text-xs italic text-muted-foreground">
                            Nothing typed for this part.
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : null}

                {item.files.length > 0 ? (
                  <div className="mt-3 rounded-lg border border-border/50 bg-muted/25 p-3 dark:bg-muted/15">
                    <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                      Uploaded files ({item.files.length})
                    </p>
                    <ul className="space-y-2">
                      {item.files.map((file, fi) => {
                        const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
                        return (
                          <li key={`${file.name}-${fi}`} className="flex items-center gap-2 text-xs text-foreground">
                            {isPdf ? (
                              <FileText className="h-4 w-4 shrink-0 text-red-600 dark:text-red-400" />
                            ) : (
                              <ImageIcon className="h-4 w-4 shrink-0 text-sky-600 dark:text-sky-400" />
                            )}
                            <span className="min-w-0 flex-1 truncate font-medium">{file.name}</span>
                            <span className="shrink-0 tabular-nums text-muted-foreground">
                              {(file.size / 1024).toFixed(0)} KB
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ) : null}

                {!item.answered ? (
                  <p className="mt-3 text-xs text-muted-foreground">No typed text or files for this question.</p>
                ) : null}
              </div>
            ))}
          </div>
        </ScrollArea>

        {!canSubmit ? (
          <div className="shrink-0 border-t border-amber-200/80 bg-amber-50/90 px-6 py-3 text-sm text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100">
            Add at least one answer or upload a full answer PDF before you can submit.
          </div>
        ) : null}

        <DialogFooter className="shrink-0 gap-2 border-t border-border/60 bg-muted/20 px-6 py-4 dark:border-border/50 sm:justify-between">
          <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={() => setReviewSubmitOpen(false)}>
            Back to exam
          </Button>
          <Button
            type="button"
            className="w-full bg-slate-900 text-white hover:bg-slate-800 sm:w-auto dark:bg-sky-700 dark:hover:bg-sky-600"
            disabled={!canSubmit || submitMutation.isPending}
            onClick={() => {
              setReviewSubmitOpen(false);
              handleSubmit();
            }}
          >
            {submitMutation.isPending ? 'Submitting…' : 'Submit exam'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog open={aboutOpen} onOpenChange={setAboutOpen}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>About this exam</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          {exam.description?.trim()
            ? exam.description
            : 'Your instructor did not add a long description. Use the question text and any figures as your source of truth.'}
        </p>
        <DialogFooter>
          <Button type="button" onClick={() => setAboutOpen(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog open={instructionsOpen} onOpenChange={setInstructionsOpen}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Tips for this session</DialogTitle>
        </DialogHeader>
        <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
          <li>Typed answers with clear steps usually grade more reliably than scans.</li>
          <li>
            If you use a full answer PDF, open <strong>Review &amp; submit</strong> after the PDF finishes mapping so you can see which questions received your pages or sections.
          </li>
          <li>
            Handwritten scans are imperfect for automatic text recognition; your work is still stored as images for the grader when the system routes that way.
          </li>
          <li>Use Mark for review to flag questions you want to double-check before submitting.</li>
          <li>Clear response removes typed text, parts, and uploads for the current question only.</li>
          <li>Submit locks in your work — use Review & submit when you are finished.</li>
        </ul>
        <DialogFooter>
          <Button type="button" onClick={() => setInstructionsOpen(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog open={fullPdfViewerOpen} onOpenChange={setFullPdfViewerOpen}>
      <DialogContent className="flex max-h-[90vh] w-[min(100vw-1rem,56rem)] max-w-none flex-col gap-0 overflow-hidden p-0 sm:max-h-[90vh]">
        <DialogHeader className="shrink-0 space-y-1 border-b px-6 py-4 text-left">
          <DialogTitle className="truncate pr-8 text-lg">
            {fullAnswerPdf?.name ?? 'Answer sheet preview'}
          </DialogTitle>
          <p className="text-sm text-muted-foreground">
            Check every page before submitting. Use Replace PDF if you need to upload a new file.
          </p>
        </DialogHeader>
        {fullAnswerPdfObjectUrl ? (
          <iframe
            title="Uploaded answer PDF preview"
            src={`${fullAnswerPdfObjectUrl}#toolbar=1`}
            className="min-h-[60vh] w-full flex-1 border-0 bg-muted/40 dark:bg-muted/20"
          />
        ) : (
          <div className="flex min-h-[40vh] items-center justify-center text-muted-foreground">
            No file loaded
          </div>
        )}
        <DialogFooter className="shrink-0 flex-col gap-2 border-t bg-muted/20 px-4 py-4 sm:flex-row sm:justify-between sm:px-6">
          <Button
            type="button"
            variant="outline"
            className="w-full sm:w-auto"
            onClick={() => {
              if (fullAnswerPdfObjectUrl) {
                window.open(fullAnswerPdfObjectUrl, '_blank', 'noopener,noreferrer');
              }
            }}
          >
            Open in new tab
          </Button>
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
            <Button
              type="button"
              variant="outline"
              className="w-full sm:w-auto"
              onClick={() => {
                setFullPdfViewerOpen(false);
                triggerFullPdfPicker();
              }}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Replace PDF
            </Button>
            <Button type="button" className="w-full sm:w-auto" onClick={() => setFullPdfViewerOpen(false)}>
              Close
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  );
}
