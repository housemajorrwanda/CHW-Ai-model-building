import { Link, useParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Clock, CheckCircle2, MinusCircle, AlertCircle, Loader2,
  Edit2, Save, X, CheckCircle, ThumbsDown, FileDown, Maximize2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { submissionsAPI, examsAPI, type SubmissionDetail, type ExamDetail } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useState } from 'react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';

/** Status badge colours */
const STATUS_STYLES: Record<string, string> = {
  graded:            'bg-blue-50 text-blue-700 border-blue-200',
  awaiting_approval: 'bg-amber-50 text-amber-700 border-amber-200',
  approved:          'bg-emerald-50 text-emerald-700 border-emerald-200',
  pending:           'bg-yellow-50 text-yellow-700 border-yellow-200',
  grading:           'bg-purple-50 text-purple-700 border-purple-200',
};

const STATUS_LABELS: Record<string, string> = {
  graded:            'Auto-graded',
  awaiting_approval: 'Awaiting Approval',
  approved:          'Approved',
  pending:           'Pending',
  grading:           'Grading…',
};

/** Calm grading UI: avoid harsh reds for incorrect / partial credit */
const STEP_OK = 'bg-emerald-50/90 border-emerald-200/90';
const STEP_REVIEW = 'bg-stone-50 border-stone-200';
const BADGE_OK = 'bg-emerald-50 text-emerald-800 border-emerald-200';
const BADGE_REVIEW = 'bg-stone-100 text-stone-800 border-stone-300';

/** Page chrome — consistent surfaces */
const surfaceHero =
  'rounded-2xl border border-violet-200/70 bg-gradient-to-br from-violet-50/90 via-white to-indigo-50/40 shadow-md dark:from-violet-950/40 dark:via-card dark:to-indigo-950/20 dark:border-violet-900/50';
const surfaceCard =
  'rounded-2xl border-2 border-violet-100/90 bg-card shadow-md overflow-hidden transition-shadow hover:shadow-lg dark:border-violet-900/35';
const surfaceScore =
  'rounded-2xl border border-emerald-200/60 bg-gradient-to-br from-emerald-50/80 to-teal-50/30 shadow-md dark:from-emerald-950/30 dark:to-teal-950/10 dark:border-emerald-900/40';
const actionBar =
  'rounded-xl border border-violet-200/80 bg-background/95 backdrop-blur-sm shadow-lg dark:border-violet-900/50';
const btnPrimary =
  'shadow-sm font-semibold bg-violet-600 text-white hover:bg-violet-700 focus-visible:ring-2 focus-visible:ring-violet-400 focus-visible:ring-offset-2';
const btnSecondary =
  'border-violet-300/80 bg-white hover:bg-violet-50 text-violet-900 dark:border-violet-700 dark:bg-violet-950/40 dark:hover:bg-violet-900/50 dark:text-violet-100 font-medium shadow-sm';
const btnSuccess =
  'shadow-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2';

export default function SubmissionDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // Edit-mode state  
  const [isEditMode, setIsEditMode] = useState(false);
  const [editingGrades, setEditingGrades] = useState<
    Record<string, { score?: number; feedback?: string }>
  >({});
  const [editingSteps, setEditingSteps] = useState<
    Record<string, { score?: number; feedback?: string }>
  >({});

  const [markedPdfOpen, setMarkedPdfOpen] = useState(false);
  const [markedPdfPaper, setMarkedPdfPaper] = useState<'a4' | 'letter' | 'legal'>('a4');
  const [includeRefInPdf, setIncludeRefInPdf] = useState(false);
  const [markedPdfLoading, setMarkedPdfLoading] = useState(false);
  /** Question id for side-by-side compare / adjust modal */
  const [compareQuestionId, setCompareQuestionId] = useState<string | null>(null);

  // ── Queries ──────────────────────────────────────────────────────────────

  const { data: submission, isLoading, error } = useQuery<SubmissionDetail>({
    queryKey: ['submission', id],
    queryFn: () => submissionsAPI.getById(id!),
    enabled: !!id,
  });

  const { data: exam } = useQuery<ExamDetail>({
    queryKey: ['exam', submission?.examId],
    queryFn: () => examsAPI.getById(submission!.examId),
    enabled: !!submission?.examId,
  });

  // ── Mutations ─────────────────────────────────────────────────────────────

  const adjustGradesMutation = useMutation({
    mutationFn: (adjustments: any) => submissionsAPI.adjustGrades(id!, adjustments),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submission', id] });
      toast.success('Grades saved successfully');
      setIsEditMode(false);
      setEditingGrades({});
      setEditingSteps({});
    },
    onError: (err: any) => toast.error('Failed to save grades: ' + err.message),
  });

  const approveMutation = useMutation({
    mutationFn: () => submissionsAPI.approve(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submission', id] });
      toast.success('Submission approved and published to student');
    },
    onError: (err: any) => toast.error('Failed to approve: ' + err.message),
  });

  const rejectMutation = useMutation({
    mutationFn: () => submissionsAPI.reject(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submission', id] });
      toast.success(
        'Submission returned for review. The student no longer sees grades until you approve. You can still view their answers and adjust scores below.'
      );
    },
    onError: (err: any) => toast.error('Failed to reject: ' + err.message),
  });

  // ── Helpers ───────────────────────────────────────────────────────────────

  const isProfessor = user?.role === 'professor' || user?.role === 'admin';
  const isStudent = user?.role === 'student';
  /** Students only see scores and feedback after the instructor approves. */
  const studentGradesPublished = submission?.status === 'approved';
  const isGradedOrBeyond = ['graded', 'awaiting_approval', 'approved'].includes(
    submission?.status ?? ''
  );
  const hasGradingData = Boolean(
    submission?.answers?.some((a: { gradingResult?: unknown }) => a.gradingResult)
  );
  /** Grading breakdown UI: instructors whenever work is in the grading pipeline; students only after approval. */
  const showGradingUi = isProfessor
    ? ['graded', 'awaiting_approval', 'approved', 'grading'].includes(submission?.status ?? '') ||
      (submission?.status === 'pending' && hasGradingData)
    : studentGradesPublished;
  const canEdit = isProfessor && showGradingUi;
  const canApprove =
    isProfessor &&
    (['graded', 'awaiting_approval'].includes(submission?.status ?? '') ||
      (submission?.status === 'pending' && hasGradingData));
  const canReject = isProfessor && ['graded', 'awaiting_approval', 'approved'].includes(submission?.status ?? '');

  const canDownloadMarkedPdf =
    !!submission && (isProfessor || (isStudent && studentGradesPublished));

  const handleDownloadMarkedPdf = async () => {
    if (!id || !submission || !exam) return;
    setMarkedPdfLoading(true);
    try {
      const blob = await submissionsAPI.downloadMarkedPdf(id, {
        paper: markedPdfPaper,
        includeReferenceSolutions: isProfessor && includeRefInPdf,
      });
      if (blob.size === 0) throw new Error('Empty PDF');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `marked_${exam.title.replace(/\s+/g, '_').slice(0, 50)}_${submission.studentName?.replace(/\s+/g, '_') || 'submission'}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Marked PDF downloaded');
      setMarkedPdfOpen(false);
    } catch (e: any) {
      toast.error(e?.message || 'Failed to download marked PDF');
    } finally {
      setMarkedPdfLoading(false);
    }
  };

  const enterEditMode = () => {
    setEditingGrades({});
    setEditingSteps({});
    setIsEditMode(true);
  };

  const cancelEditMode = () => {
    setEditingGrades({});
    setEditingSteps({});
    setIsEditMode(false);
  };

  const handleSaveGrades = () => {
    if (!submission?.answers) return;

    const adjustments = {
      adjustments: submission.answers
        .filter((a: any) => a.gradingResult)
        .map((answer: any) => {
          const gid = answer.gradingResult?.id ?? answer.gradingResultId;
          const gradeEdit = editingGrades[gid];
          const stepAdjustments = (answer.gradingResult?.stepResults ?? [])
            .map((step: any) => {
              const s = editingSteps[step.id];
              if (!s || (s.score === undefined && !s.feedback)) return null;
              return { stepResultId: step.id, score: s.score, feedback: s.feedback };
            })
            .filter(Boolean);

          if (!gradeEdit && stepAdjustments.length === 0) return null;
          return {
            gradingResultId: gid,
            score: gradeEdit?.score,
            feedback: gradeEdit?.feedback,
            stepAdjustments,
          };
        })
        .filter(Boolean),
    };

    adjustGradesMutation.mutate(adjustments);
  };

  // ── Render guards ─────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px] px-4">
        <div className="flex flex-col items-center gap-4 rounded-2xl border-2 border-violet-200/60 bg-violet-50/50 px-10 py-12 dark:border-violet-900/50 dark:bg-violet-950/30">
          <Loader2 className="h-10 w-10 animate-spin text-violet-600" />
          <p className="text-sm font-medium text-muted-foreground">Loading submission…</p>
        </div>
      </div>
    );
  }

  if (error || !submission) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Submission not found</p>
      </div>
    );
  }

  const sumFromAnswerGrades =
    submission.answers?.reduce(
      (acc: number, a: { gradingResult?: { score?: number } }) =>
        acc + (a.gradingResult?.score ?? 0),
      0
    ) ?? 0;
  const effectiveTotalScore =
    submission.totalScore != null
      ? submission.totalScore
      : hasGradingData
        ? sumFromAnswerGrades
        : null;

  const scorePercentage =
    effectiveTotalScore != null && submission.maxScore > 0
      ? Math.round((effectiveTotalScore / submission.maxScore) * 100)
      : 0;

  const getGoldSteps = (q: any) => (q?.goldSolution?.steps ?? q?.goldSolutionSteps ?? []) as Array<{
    stepNumber: number;
    description?: string;
    expression?: string;
    latex?: string;
    points: number;
  }>;

  const activeCompareAnswer = compareQuestionId
    ? submission.answers?.find((a) => a.questionId === compareQuestionId)
    : null;
  const activeCompareQuestion = compareQuestionId
    ? exam?.questions?.find((q) => q.id === compareQuestionId)
    : null;
  const activeCompareResult = activeCompareAnswer?.gradingResult;
  const activeCompareGid =
    activeCompareResult?.id ?? activeCompareAnswer?.gradingResultId;

  // ── Main render ───────────────────────────────────────────────────────────

  return (
    <div className="max-w-4xl mx-auto space-y-8 text-base leading-relaxed pb-12">

      {/* ── Header ── */}
      <header className={cn('p-6 sm:p-8', surfaceHero)}>
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-violet-700 dark:text-violet-400">
              {isProfessor
                ? 'Submission review'
                : studentGradesPublished
                ? 'Your results'
                : 'Your submission'}
            </p>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">
              {exam?.title ?? 'Exam'}
            </h1>
            <p className="text-muted-foreground text-[1.05rem]">
              {isProfessor ? (
                <>
                  <span className="font-medium text-foreground">{submission.studentName}</span>
                  <span className="mx-2 text-border">·</span>
                </>
              ) : (
                <>
                  <span className="font-medium text-foreground">Submitted</span>
                  <span className="mx-2 text-border">·</span>
                </>
              )}
              {format(new Date(submission.submittedAt), 'MMMM d, yyyy')}
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:items-end shrink-0">
            <Badge
              variant="outline"
              className={cn(
                'text-sm px-3 py-1.5 font-semibold shadow-sm border-2',
                STATUS_STYLES[submission.status]
              )}
            >
              {STATUS_LABELS[submission.status] ?? submission.status}
            </Badge>

            <div
              className={cn(
                'flex flex-wrap items-center gap-2 p-2 rounded-xl border border-violet-200/50 bg-white/60 dark:bg-violet-950/30 dark:border-violet-800/60'
              )}
              role="toolbar"
              aria-label="Submission actions"
            >
              {canDownloadMarkedPdf && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setMarkedPdfOpen(true)}
                  className={cn('shrink-0 h-9', btnSecondary)}
                >
                  <FileDown className="h-4 w-4 mr-2" />
                  Marked PDF
                </Button>
              )}

              {isProfessor && (
                <>
                  {canEdit && !isEditMode && (
                    <Button size="sm" onClick={enterEditMode} className={cn('h-9', btnPrimary)}>
                      <Edit2 className="h-4 w-4 mr-2" />
                      Edit grades
                    </Button>
                  )}

                  {isEditMode && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={cancelEditMode}
                        disabled={adjustGradesMutation.isPending}
                        className={cn('h-9', btnSecondary)}
                      >
                        <X className="h-4 w-4 mr-2" />
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleSaveGrades}
                        disabled={adjustGradesMutation.isPending}
                        className={cn('h-9', btnPrimary)}
                      >
                        {adjustGradesMutation.isPending ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <Save className="h-4 w-4 mr-2" />
                        )}
                        Save changes
                      </Button>
                    </>
                  )}

                  {!isEditMode && canApprove && (
                    <Button
                      size="sm"
                      className={cn('h-9', btnSuccess)}
                      onClick={() => approveMutation.mutate()}
                      disabled={approveMutation.isPending}
                    >
                      {approveMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <CheckCircle className="h-4 w-4 mr-2" />
                      )}
                      Approve
                    </Button>
                  )}
                  {!isEditMode && canReject && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-9 font-medium border-amber-300/90 bg-amber-50/80 text-amber-950 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100 dark:hover:bg-amber-950/60"
                      onClick={() => rejectMutation.mutate()}
                      disabled={rejectMutation.isPending}
                    >
                      {rejectMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <ThumbsDown className="h-4 w-4 mr-2" />
                      )}
                      Reject
                    </Button>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {isStudent && !studentGradesPublished && (
        <div className="rounded-2xl border-2 border-sky-300/60 bg-gradient-to-r from-sky-50 to-indigo-50/50 px-5 py-4 shadow-sm dark:from-sky-950/40 dark:to-indigo-950/20 dark:border-sky-800">
          <p className="font-semibold text-sky-950 dark:text-sky-100">Grades are not visible yet</p>
          <p className="text-muted-foreground mt-1.5 text-[0.95rem] leading-relaxed">
            Your instructor reviews and may adjust auto-grades before publishing. You will see your score
            and feedback here after they <strong>approve</strong> your submission. You can still review
            what you wrote below.
          </p>
          <Button variant="link" className="mt-2 h-auto p-0 text-violet-700 dark:text-violet-400" asChild>
            <Link to="/my-results">Back to My Results</Link>
          </Button>
        </div>
      )}

      {/* Edit-mode banner */}
      {isEditMode && (
        <div className="flex items-center gap-3 px-5 py-4 rounded-2xl border-2 border-amber-300/70 bg-gradient-to-r from-amber-50 to-amber-100/50 text-amber-950 text-[0.95rem] shadow-sm dark:from-amber-950/50 dark:to-amber-950/20 dark:border-amber-800 dark:text-amber-100">
          <Edit2 className="h-5 w-5 shrink-0 text-amber-700 dark:text-amber-400" />
          <span>
            You are editing grades. Change any score or feedback below, then click{' '}
            <strong>Save Changes</strong>. The submission will be marked as{' '}
            <em>awaiting approval</em> until you approve it.
          </span>
        </div>
      )}

      {isProfessor && submission.status === 'pending' && hasGradingData && (
        <div className="flex items-start gap-3 px-5 py-4 rounded-2xl border-2 border-sky-300/60 bg-gradient-to-r from-sky-50 to-indigo-50/40 text-sky-950 text-[0.95rem] shadow-sm dark:from-sky-950/40 dark:to-indigo-950/20 dark:border-sky-800 dark:text-sky-100">
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5 text-sky-600 dark:text-sky-400" />
          <span>
            This attempt was returned for your review. The student does <strong>not</strong> see these
            scores yet. You can edit marks, then <strong>Approve</strong> when ready—or they can still
            resubmit if you ask them to.
          </span>
        </div>
      )}

      {/* ── Score overview ── */}
      {showGradingUi && (
        <Card className={cn('animate-fade-up border-0 shadow-none', surfaceScore)}>
          <CardHeader className="pb-2 pt-6 px-6 sm:px-8">
            <CardTitle className="text-xl font-semibold flex items-center gap-2 text-emerald-900 dark:text-emerald-100">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-600 text-white shadow-sm">
                <CheckCircle2 className="h-5 w-5" />
              </span>
              Overall score
            </CardTitle>
          </CardHeader>
          <CardContent className="px-6 sm:px-8 pb-6">
            <div className="flex items-end gap-3 mb-4">
              <span className="text-5xl sm:text-6xl font-bold tracking-tight">
                {effectiveTotalScore != null
                  ? Number.isInteger(effectiveTotalScore)
                    ? effectiveTotalScore
                    : effectiveTotalScore.toFixed(1)
                  : '—'}
              </span>
              <span className="text-2xl sm:text-3xl text-muted-foreground mb-1">/ {submission.maxScore}</span>
              <span
                className={cn(
                  'text-xl font-semibold ml-auto tabular-nums',
                  scorePercentage >= 70
                    ? 'text-emerald-700'
                    : scorePercentage >= 50
                    ? 'text-amber-800'
                    : 'text-stone-700'
                )}
              >
                {scorePercentage}%
              </span>
            </div>
            <Progress
              value={scorePercentage}
              className="h-4 border border-emerald-200/60 bg-white/70 dark:bg-emerald-950/40 dark:border-emerald-800/50"
            />
            {submission.status === 'approved' && (
              <p className="text-sm font-medium text-emerald-800 dark:text-emerald-300 mt-4 flex items-center gap-2 rounded-lg bg-white/60 dark:bg-emerald-950/40 px-3 py-2 border border-emerald-200/60 dark:border-emerald-800/50">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                Approved.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── Per-question results ── */}
      <section className="space-y-6" aria-labelledby="detailed-results-heading">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between border-b border-violet-200/60 dark:border-violet-900/50 pb-4">
          <div>
            <h2
              id="detailed-results-heading"
              className="text-2xl font-bold tracking-tight text-foreground"
            >
              {showGradingUi ? 'Detailed results' : 'Your responses'}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              {showGradingUi
                ? isProfessor
                  ? 'Each block is one exam question — review the answer, steps, and feedback.'
                  : 'Your submitted work for each question. Scores appear after your instructor approves.'
                : 'What you submitted for each question (scores are hidden until your instructor publishes them).'}
            </p>
          </div>
          {submission.answers && submission.answers.length > 0 && (
            <span className="inline-flex items-center rounded-full bg-violet-100 dark:bg-violet-950/80 px-3 py-1 text-sm font-semibold text-violet-900 dark:text-violet-200 border border-violet-200/80 dark:border-violet-800">
              {submission.answers.length} question{submission.answers.length === 1 ? '' : 's'}
            </span>
          )}
        </div>

        {submission.answers && submission.answers.length > 0 ? (
          submission.answers.map((answer: any, index: number) => {
            const question = exam?.questions?.find((q: any) => q.id === answer.questionId);
            const result = answer.gradingResult;
            const gid = result?.id ?? answer.gradingResultId;

            return (
              <Card
                key={answer.questionId}
                className={cn('animate-fade-up', surfaceCard)}
                style={{ animationDelay: `${index * 80}ms` }}
              >
                <CardHeader className="pb-4 border-b border-violet-100/80 bg-gradient-to-r from-violet-50/50 to-transparent dark:from-violet-950/25 dark:border-violet-900/40">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex gap-3 min-w-0">
                      <span
                        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-sm font-bold text-white shadow-md ring-2 ring-violet-200/50 dark:ring-violet-800/50"
                        aria-hidden
                      >
                        {answer.questionNumber}
                      </span>
                      <div className="min-w-0 pt-0.5">
                        <CardTitle className="text-lg font-bold text-foreground">
                          Question {answer.questionNumber}
                        </CardTitle>
                        {question && (
                          <p className="text-base text-muted-foreground mt-2 leading-relaxed">
                            {question.text}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col items-stretch sm:items-end gap-2 shrink-0">
                      {/* Score badge / editable score (hidden while compare modal open for this question) */}
                      {result && (
                        isEditMode && compareQuestionId !== answer.questionId ? (
                          <div className="flex items-center gap-1.5 shrink-0">
                            <Label className="text-sm text-muted-foreground whitespace-nowrap">Score:</Label>
                            <Input
                              type="number"
                              min={0}
                              max={result.maxScore}
                              step={0.5}
                              className="w-[5.5rem] h-9 text-base"
                              defaultValue={result.score}
                              onChange={(e) =>
                                setEditingGrades((prev) => ({
                                  ...prev,
                                  [gid]: { ...prev[gid], score: parseFloat(e.target.value) },
                                }))
                              }
                            />
                            <span className="text-base text-muted-foreground shrink-0">
                              / {result.maxScore} pts
                            </span>
                          </div>
                        ) : (
                          <Badge
                            variant="outline"
                            className={cn(
                              'shrink-0 text-sm px-2.5 py-0.5 font-medium',
                              result.isCorrect ? BADGE_OK : BADGE_REVIEW
                            )}
                          >
                            {result.score} / {result.maxScore} pts
                          </Badge>
                        )
                      )}
                      {(isProfessor || studentGradesPublished) && (
                        <Button
                          type="button"
                          size="sm"
                          className={cn('shrink-0 h-10 px-4 w-full sm:w-auto', btnPrimary)}
                          onClick={() => setCompareQuestionId(answer.questionId)}
                        >
                          <Maximize2 className="h-4 w-4 mr-2" />
                          {isProfessor ? 'View full comparison' : 'View details'}
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-6 text-base px-5 sm:px-6 py-6">
                  {/* Student's answer */}
                  <div className="relative rounded-xl border-2 border-violet-100 bg-gradient-to-b from-violet-50/40 to-muted/30 p-4 dark:border-violet-900/40 dark:from-violet-950/20">
                    <div className="absolute left-0 top-0 bottom-0 w-1 rounded-l-xl bg-violet-500/80 dark:bg-violet-500" aria-hidden />
                    <p className="text-sm font-bold text-violet-900 dark:text-violet-200 mb-3 pl-2 uppercase tracking-wide flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-violet-500" />
                      Student&apos;s answer
                    </p>
                    {answer.extractedText ? (
                      <div
                        className="prose prose-base max-w-none prose-p:leading-relaxed prose-headings:font-semibold"
                        dangerouslySetInnerHTML={{ __html: answer.extractedText }}
                      />
                    ) : (
                      <p className="font-mono text-base text-foreground/90">
                        {answer.extractedLatex ?? 'No answer provided'}
                      </p>
                    )}
                  </div>

                  {/* Step-by-step results */}
                  {result?.stepResults && result.stepResults.length > 0 && (
                    <div className="space-y-4 rounded-xl border border-border/80 bg-muted/20 p-4 dark:bg-muted/10">
                      <p className="text-sm font-bold text-foreground uppercase tracking-wide flex items-center gap-2 border-b border-border/60 pb-3">
                        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200 text-xs font-bold">
                          AI
                        </span>
                        Step-by-step analysis
                      </p>
                      {result.stepResults.map((step: any) => (
                        <div
                          key={step.stepNumber}
                          className={cn(
                            'flex items-start gap-3 p-4 rounded-xl border',
                            step.isCorrect ? STEP_OK : STEP_REVIEW
                          )}
                        >
                          {step.isCorrect ? (
                            <CheckCircle2 className="h-6 w-6 text-emerald-700 mt-0.5 shrink-0" />
                          ) : (
                            <MinusCircle className="h-6 w-6 text-amber-800/90 mt-0.5 shrink-0" />
                          )}

                          <div className="flex-1 space-y-2 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-semibold text-base">Step {step.stepNumber}</span>

                              {isEditMode && compareQuestionId !== answer.questionId ? (
                                <div className="flex items-center gap-1">
                                  <Input
                                    type="number"
                                    min={0}
                                    max={step.maxScore}
                                    step={0.5}
                                    className="w-[4.5rem] h-8 text-sm"
                                    defaultValue={step.score}
                                    onChange={(e) =>
                                      setEditingSteps((prev) => ({
                                        ...prev,
                                        [step.id]: {
                                          ...prev[step.id],
                                          score: parseFloat(e.target.value),
                                        },
                                      }))
                                    }
                                  />
                                  <span className="text-sm text-muted-foreground">
                                    / {step.maxScore} pts
                                  </span>
                                </div>
                              ) : (
                                <Badge variant="secondary" className="text-sm font-medium">
                                  {step.score} / {step.maxScore} pts
                                </Badge>
                              )}
                            </div>

                            {(step.expected || step.received) && (
                              <div className="grid grid-cols-2 gap-3 text-sm pt-0.5">
                                <div className="rounded-lg bg-background/95 border border-border/80 p-3 min-w-0">
                                  <span className="text-muted-foreground block mb-1 text-xs font-medium uppercase tracking-wide">
                                    Expected (matched target)
                                  </span>
                                  <span className="font-mono break-words block text-[0.95rem] leading-snug">
                                    {step.expected ?? '—'}
                                  </span>
                                </div>
                                <div className="rounded-lg bg-background/95 border border-border/80 p-3 min-w-0">
                                  <span className="text-muted-foreground block mb-1 text-xs font-medium uppercase tracking-wide">
                                    Received (extracted)
                                  </span>
                                  <span className="font-mono break-words block text-[0.95rem] leading-snug">
                                    {step.received ?? '—'}
                                  </span>
                                </div>
                              </div>
                            )}

                            {isEditMode && compareQuestionId !== answer.questionId ? (
                              <Textarea
                                className="text-base min-h-[72px] leading-relaxed"
                                defaultValue={step.feedback ?? ''}
                                placeholder="Feedback for this step…"
                                onChange={(e) =>
                                  setEditingSteps((prev) => ({
                                    ...prev,
                                    [step.id]: { ...prev[step.id], feedback: e.target.value },
                                  }))
                                }
                              />
                            ) : (
                              step.feedback && (
                                <p className="text-base text-muted-foreground leading-relaxed">{step.feedback}</p>
                              )
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Overall question feedback */}
                  {isEditMode && compareQuestionId !== answer.questionId ? (
                    <div className="space-y-2">
                      <Label className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                        Overall Feedback
                      </Label>
                      <Textarea
                        className="min-h-[88px] text-base leading-relaxed"
                        defaultValue={result?.feedback ?? ''}
                        placeholder="Add feedback for this question…"
                        onChange={(e) =>
                          setEditingGrades((prev) => ({
                            ...prev,
                            [gid]: { ...prev[gid], feedback: e.target.value },
                          }))
                        }
                      />
                    </div>
                  ) : result?.feedback && result.feedback.trim() !== '' ? (
                    <div className="flex items-start gap-3 p-4 rounded-xl bg-violet-50/60 border border-violet-200/70 dark:bg-violet-950/30 dark:border-violet-800/50">
                      <AlertCircle className="h-6 w-6 text-violet-700 dark:text-violet-400 mt-0.5 shrink-0" />
                      <div>
                        <p className="font-semibold text-base text-foreground">Feedback</p>
                        <p className="text-base text-muted-foreground leading-relaxed mt-1">{result.feedback}</p>
                      </div>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            );
          })
        ) : (
          <Card className={cn('border-dashed', surfaceCard)}>
            <CardContent className="py-12 text-center">
              <Clock className="h-12 w-12 text-violet-400 mx-auto mb-4" />
              <p className="text-muted-foreground font-medium">
                {submission.status === 'pending'
                  ? 'This submission is awaiting grading'
                  : 'Grading in progress…'}
              </p>
            </CardContent>
          </Card>
        )}
      </section>

      {/* ── Bottom action bar (save / approve from bottom of long page) ── */}
      {isProfessor && showGradingUi && (
        <>
          <Separator className="my-2 bg-violet-200/50 dark:bg-violet-900/50" />
          <div
            className={cn(
              'flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between p-4 sm:p-5 sticky bottom-4 z-10',
              actionBar
            )}
          >
            <p className="text-sm sm:text-base text-muted-foreground max-w-xl leading-relaxed font-medium">
              {isEditMode
                ? 'Review your changes above, then save.'
                : submission.status === 'approved'
                ? 'This submission has been approved and is visible to the student.'
                : 'Edit marks, open full comparison per question, then approve when ready.'}
            </p>
            <div className="flex flex-wrap items-center gap-2 justify-end">
              {isEditMode ? (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={cancelEditMode}
                    disabled={adjustGradesMutation.isPending}
                    className={cn('h-10', btnSecondary)}
                  >
                    <X className="h-4 w-4 mr-2" />
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSaveGrades}
                    disabled={adjustGradesMutation.isPending}
                    className={cn('h-10', btnPrimary)}
                  >
                    {adjustGradesMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4 mr-2" />
                    )}
                    Save changes
                  </Button>
                </>
              ) : (
                <>
                  {canEdit && (
                    <Button size="sm" onClick={enterEditMode} className={cn('h-10', btnPrimary)}>
                      <Edit2 className="h-4 w-4 mr-2" />
                      Edit grades
                    </Button>
                  )}
                  {canApprove && (
                    <Button
                      size="sm"
                      className={cn('h-10', btnSuccess)}
                      onClick={() => approveMutation.mutate()}
                      disabled={approveMutation.isPending}
                    >
                      {approveMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <CheckCircle className="h-4 w-4 mr-2" />
                      )}
                      Approve grades
                    </Button>
                  )}
                  {canReject && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-10 font-medium border-amber-300/90 bg-amber-50/80 text-amber-950 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100"
                      onClick={() => rejectMutation.mutate()}
                      disabled={rejectMutation.isPending}
                    >
                      {rejectMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <ThumbsDown className="h-4 w-4 mr-2" />
                      )}
                      Reject
                    </Button>
                  )}
                </>
              )}
            </div>
          </div>
        </>
      )}

      {/* Side-by-side compare: expected vs student + AI grading & adjustments */}
      <Dialog
        open={compareQuestionId !== null}
        onOpenChange={(open) => {
          if (!open) setCompareQuestionId(null);
        }}
      >
        <DialogContent className="max-w-6xl w-[min(100vw-2rem,1152px)] max-h-[92vh] overflow-hidden flex flex-col gap-0 p-0 border-2 border-violet-200/70 shadow-2xl rounded-2xl dark:border-violet-900/60">
          {activeCompareAnswer && (
            <>
              <DialogHeader className="px-6 pt-6 pb-5 shrink-0 border-b border-violet-200/60 bg-gradient-to-br from-violet-50/90 via-white to-indigo-50/30 space-y-3 dark:from-violet-950/50 dark:via-card dark:to-indigo-950/20 dark:border-violet-900/40">
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-600 text-sm font-bold text-white shadow-md">
                    {activeCompareAnswer.questionNumber}
                  </span>
                  <DialogTitle className="text-2xl font-bold tracking-tight text-left">
                    Question {activeCompareAnswer.questionNumber}
                  </DialogTitle>
                </div>
                {activeCompareQuestion?.text && (
                  <DialogDescription className="text-base text-muted-foreground text-left line-clamp-4 leading-relaxed mt-2 border-t border-violet-200/40 pt-4 dark:border-violet-800/40">
                    {activeCompareQuestion.text}
                  </DialogDescription>
                )}
              </DialogHeader>

              <ScrollArea className="h-[min(65vh,640px)] px-6">
                <div className="space-y-6 py-5 pr-3 text-base leading-relaxed">
                  <div
                    className={cn(
                      'grid gap-4',
                      isProfessor ? 'md:grid-cols-2' : 'grid-cols-1'
                    )}
                  >
                    {isProfessor && (
                      <div className="rounded-xl border border-border/70 bg-muted/40 p-4 space-y-3 min-h-[120px]">
                        <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                          Expected (reference)
                        </p>
                        {getGoldSteps(activeCompareQuestion).length > 0 ? (
                          <ul className="space-y-3">
                            {getGoldSteps(activeCompareQuestion).map((st) => (
                              <li
                                key={st.stepNumber}
                                className="rounded-lg border border-border/80 bg-background p-3 text-base"
                              >
                                <div className="flex items-center justify-between gap-2 mb-1">
                                  <span className="font-semibold">Step {st.stepNumber}</span>
                                  <Badge variant="secondary" className="text-sm shrink-0">
                                    {st.points} pts
                                  </Badge>
                                </div>
                                {st.description ? (
                                  <p className="text-muted-foreground text-base mb-1.5 leading-relaxed">{st.description}</p>
                                ) : null}
                                <p className="font-mono text-[0.95rem] break-words leading-snug">
                                  {st.latex || st.expression}
                                </p>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-base text-muted-foreground leading-relaxed">
                            No step-by-step reference was defined for this question.
                          </p>
                        )}
                        {(activeCompareQuestion?.finalAnswer ||
                          activeCompareQuestion?.finalAnswerLatex) && (
                          <div className="pt-2 border-t space-y-1">
                            <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                              Final answer (reference)
                            </p>
                            <p className="font-mono text-base leading-relaxed">
                              {activeCompareQuestion?.finalAnswerLatex ||
                                activeCompareQuestion?.finalAnswer}
                            </p>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="rounded-xl border border-border/70 bg-muted/40 p-4 space-y-2 min-h-[120px]">
                      <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                        {isProfessor ? "Student's response" : 'Your answer'}
                      </p>
                      {activeCompareAnswer.extractedText ? (
                        <div
                          className="prose prose-base max-w-none prose-p:leading-relaxed"
                          dangerouslySetInnerHTML={{ __html: activeCompareAnswer.extractedText }}
                        />
                      ) : (
                        <p className="font-mono text-base break-words leading-relaxed">
                          {activeCompareAnswer.extractedLatex ?? 'No answer provided'}
                        </p>
                      )}
                    </div>
                  </div>

                  {activeCompareResult && showGradingUi && (
                    <div className="rounded-xl border border-violet-200/60 bg-violet-50/40 dark:bg-violet-950/25 dark:border-violet-900/50 p-5 space-y-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-1.5">
                            AI grading & adjustments
                          </p>
                          <p className="text-base text-muted-foreground leading-relaxed">
                            {canEdit
                              ? 'Review how each step was matched and scored. Adjust points or feedback, then save.'
                              : 'How the grader evaluated each step for this answer.'}
                          </p>
                        </div>
                        {canEdit && activeCompareGid && (
                          <div className="flex items-center gap-1.5">
                            <Label className="text-sm text-muted-foreground whitespace-nowrap">
                              Question score
                            </Label>
                            <Input
                              type="number"
                              min={0}
                              max={activeCompareResult.maxScore}
                              step={0.5}
                              className="w-[5.5rem] h-9 text-base"
                              value={
                                editingGrades[activeCompareGid]?.score !== undefined
                                  ? String(editingGrades[activeCompareGid].score)
                                  : String(activeCompareResult.score)
                              }
                              onChange={(e) => {
                                const v = parseFloat(e.target.value);
                                setEditingGrades((prev) => ({
                                  ...prev,
                                  [activeCompareGid]: {
                                    ...prev[activeCompareGid],
                                    score: Number.isNaN(v) ? undefined : v,
                                  },
                                }));
                              }}
                            />
                            <span className="text-base text-muted-foreground">
                              / {activeCompareResult.maxScore} pts
                            </span>
                          </div>
                        )}
                        {!canEdit && (
                          <Badge
                            variant="outline"
                            className={cn(
                              'text-sm font-medium px-2.5 py-0.5',
                              activeCompareResult.isCorrect ? BADGE_OK : BADGE_REVIEW
                            )}
                          >
                            {activeCompareResult.score} / {activeCompareResult.maxScore} pts
                          </Badge>
                        )}
                      </div>

                      {activeCompareResult.stepResults &&
                        activeCompareResult.stepResults.length > 0 && (
                          <div className="space-y-3">
                            <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                              Step-by-step (AI)
                            </p>
                            {activeCompareResult.stepResults.map((step: any) => {
                              const stepScoreDisplay =
                                editingSteps[step.id]?.score !== undefined
                                  ? editingSteps[step.id].score
                                  : step.score;
                              return (
                                <div
                                  key={step.id ?? step.stepNumber}
                                  className={cn(
                                    'rounded-xl border p-4 space-y-3',
                                    step.isCorrect ? STEP_OK : STEP_REVIEW
                                  )}
                                >
                                  <div className="flex items-start gap-3">
                                    {step.isCorrect ? (
                                      <CheckCircle2 className="h-6 w-6 text-emerald-700 mt-0.5 shrink-0" />
                                    ) : (
                                      <MinusCircle className="h-6 w-6 text-amber-800/90 mt-0.5 shrink-0" />
                                    )}
                                    <div className="flex-1 min-w-0 space-y-3">
                                      <div className="flex flex-wrap items-center gap-2">
                                        <span className="font-semibold text-base">
                                          Step {step.stepNumber}
                                        </span>
                                        {canEdit ? (
                                          <div className="flex items-center gap-1">
                                            <Input
                                              type="number"
                                              min={0}
                                              max={step.maxScore}
                                              step={0.5}
                                              className="w-[4.5rem] h-8 text-sm"
                                              value={String(stepScoreDisplay)}
                                              onChange={(e) => {
                                                const v = parseFloat(e.target.value);
                                                setEditingSteps((prev) => ({
                                                  ...prev,
                                                  [step.id]: {
                                                    ...prev[step.id],
                                                    score: Number.isNaN(v) ? undefined : v,
                                                  },
                                                }));
                                              }}
                                            />
                                            <span className="text-sm text-muted-foreground">
                                              / {step.maxScore} pts
                                            </span>
                                          </div>
                                        ) : (
                                          <Badge variant="secondary" className="text-sm font-medium">
                                            {step.score} / {step.maxScore} pts
                                          </Badge>
                                        )}
                                      </div>
                                      {(step.expected || step.received) && (
                                        <div className="grid grid-cols-2 gap-3 text-sm">
                                          <div className="rounded-lg bg-background/95 border border-border/80 p-3 min-w-0">
                                            <span className="text-muted-foreground block mb-1 text-xs font-medium uppercase tracking-wide">
                                              Expected (matched target)
                                            </span>
                                            <span className="font-mono break-words text-[0.95rem] leading-snug">
                                              {step.expected ?? '—'}
                                            </span>
                                          </div>
                                          <div className="rounded-lg bg-background/95 border border-border/80 p-3 min-w-0">
                                            <span className="text-muted-foreground block mb-1 text-xs font-medium uppercase tracking-wide">
                                              Received (extracted)
                                            </span>
                                            <span className="font-mono break-words text-[0.95rem] leading-snug">
                                              {step.received ?? '—'}
                                            </span>
                                          </div>
                                        </div>
                                      )}
                                      {canEdit ? (
                                        <Textarea
                                          className="text-base min-h-[64px] leading-relaxed"
                                          value={
                                            editingSteps[step.id]?.feedback !== undefined
                                              ? editingSteps[step.id].feedback ?? ''
                                              : step.feedback ?? ''
                                          }
                                          placeholder="Feedback for this step…"
                                          onChange={(e) =>
                                            setEditingSteps((prev) => ({
                                              ...prev,
                                              [step.id]: {
                                                ...prev[step.id],
                                                feedback: e.target.value,
                                              },
                                            }))
                                          }
                                        />
                                      ) : (
                                        step.feedback && (
                                          <p className="text-base text-muted-foreground leading-relaxed">
                                            {step.feedback}
                                          </p>
                                        )
                                      )}
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}

                      {canEdit && activeCompareGid ? (
                        <div className="space-y-2 pt-1">
                          <Label className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                            Overall feedback (this question)
                          </Label>
                          <Textarea
                            className="min-h-[80px] text-base leading-relaxed"
                            value={
                              editingGrades[activeCompareGid]?.feedback !== undefined
                                ? editingGrades[activeCompareGid].feedback ?? ''
                                : activeCompareResult.feedback ?? ''
                            }
                            placeholder="Add feedback for this question…"
                            onChange={(e) =>
                              setEditingGrades((prev) => ({
                                ...prev,
                                [activeCompareGid]: {
                                  ...prev[activeCompareGid],
                                  feedback: e.target.value,
                                },
                              }))
                            }
                          />
                        </div>
                      ) : (
                        activeCompareResult.feedback &&
                        activeCompareResult.feedback.trim() !== '' && (
                          <div className="flex items-start gap-3 pt-1">
                            <AlertCircle className="h-5 w-5 text-violet-700 dark:text-violet-400 mt-0.5 shrink-0" />
                            <div>
                              <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                                Overall feedback
                              </p>
                              <p className="text-base text-muted-foreground leading-relaxed mt-1">
                                {activeCompareResult.feedback}
                              </p>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  )}

                  {(!activeCompareResult || !showGradingUi) && (
                    <p className="text-base text-muted-foreground text-center py-3 leading-relaxed">
                      {submission.status === 'pending' || submission.status === 'grading'
                        ? 'Grading is not available for this question yet.'
                        : 'No grading details for this question.'}
                    </p>
                  )}
                </div>
              </ScrollArea>

              <DialogFooter className="px-6 py-4 border-t border-violet-200/60 bg-muted/30 shrink-0 gap-3 sm:gap-2 flex-col-reverse sm:flex-row dark:border-violet-900/50">
                <Button
                  type="button"
                  variant="outline"
                  className={cn('text-base h-10 w-full sm:w-auto', btnSecondary)}
                  onClick={() => setCompareQuestionId(null)}
                >
                  Close
                </Button>
                {canEdit && activeCompareResult && (
                  <Button
                    type="button"
                    className={cn('text-base h-10 w-full sm:w-auto', btnPrimary)}
                    onClick={handleSaveGrades}
                    disabled={adjustGradesMutation.isPending}
                  >
                    {adjustGradesMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4 mr-2" />
                    )}
                    Save grade changes
                  </Button>
                )}
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={markedPdfOpen} onOpenChange={setMarkedPdfOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileDown className="h-5 w-5" />
              Download marked exam PDF
            </DialogTitle>
            <DialogDescription>
              Printable report: questions, the student&apos;s responses, scores, and step feedback.
              {isProfessor && ' You can optionally include reference (model) solutions.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="marked-paper" className="text-xs text-muted-foreground">
                Paper size
              </Label>
              <Select
                value={markedPdfPaper}
                onValueChange={(v) => setMarkedPdfPaper(v as 'a4' | 'letter' | 'legal')}
              >
                <SelectTrigger id="marked-paper">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="a4">A4 (210 × 297 mm)</SelectItem>
                  <SelectItem value="letter">US Letter (8.5 × 11 in)</SelectItem>
                  <SelectItem value="legal">US Legal (8.5 × 14 in)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {isProfessor && (
              <label className="flex items-start gap-3 cursor-pointer text-sm">
                <Checkbox
                  id="include-ref-pdf"
                  checked={includeRefInPdf}
                  onCheckedChange={(c) => setIncludeRefInPdf(c === true)}
                  className="mt-0.5"
                />
                <span>
                  <span className="font-medium">Include reference solutions</span>
                  <span className="block text-muted-foreground text-xs mt-0.5">
                    Appends model / gold solution steps after each question (instructor copy).
                  </span>
                </span>
              </label>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMarkedPdfOpen(false)} disabled={markedPdfLoading}>
              Cancel
            </Button>
            <Button onClick={handleDownloadMarkedPdf} disabled={markedPdfLoading || !exam}>
              {markedPdfLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating…
                </>
              ) : (
                <>
                  <FileDown className="h-4 w-4 mr-2" />
                  Download
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
