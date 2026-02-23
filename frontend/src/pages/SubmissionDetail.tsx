import { useParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Clock, CheckCircle2, XCircle, AlertCircle, Loader2,
  Edit2, Save, X, CheckCircle, ThumbsDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { submissionsAPI, examsAPI } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useState } from 'react';
import { toast } from 'sonner';

/** Status badge colours */
const STATUS_STYLES: Record<string, string> = {
  graded:            'bg-blue-50 text-blue-700 border-blue-200',
  awaiting_approval: 'bg-amber-50 text-amber-700 border-amber-200',
  approved:          'bg-emerald-50 text-emerald-700 border-emerald-200',
  pending:           'bg-yellow-50 text-yellow-700 border-yellow-200',
  grading:           'bg-purple-50 text-purple-700 border-purple-200',
};

const STATUS_LABELS: Record<string, string> = {
  graded:            'AI Graded',
  awaiting_approval: 'Awaiting Approval',
  approved:          'Approved',
  pending:           'Pending',
  grading:           'Grading…',
};

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

  // ── Queries ──────────────────────────────────────────────────────────────

  const { data: submission, isLoading, error } = useQuery({
    queryKey: ['submission', id],
    queryFn: () => submissionsAPI.getById(id!),
    enabled: !!id,
  });

  const { data: exam } = useQuery({
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
      toast.success('Submission reset — student can resubmit');
    },
    onError: (err: any) => toast.error('Failed to reject: ' + err.message),
  });

  // ── Helpers ───────────────────────────────────────────────────────────────

  const isProfessor = user?.role === 'professor' || user?.role === 'admin';
  const isGradedOrBeyond = ['graded', 'awaiting_approval', 'approved'].includes(
    submission?.status ?? ''
  );
  const canEdit = isProfessor && isGradedOrBeyond;
  const canApprove = isProfessor && ['graded', 'awaiting_approval'].includes(submission?.status ?? '');
  const canReject  = isProfessor && ['graded', 'awaiting_approval', 'approved'].includes(submission?.status ?? '');

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
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
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

  const scorePercentage = submission.totalScore
    ? Math.round((submission.totalScore / submission.maxScore) * 100)
    : 0;

  // ── Main render ───────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 max-w-4xl">

      {/* ── Header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{exam?.title ?? 'Exam'}</h1>
          <p className="text-muted-foreground mt-1">
            Submitted by <span className="font-medium text-foreground">{submission.studentName}</span>{' '}
            on {format(new Date(submission.submittedAt), 'MMMM d, yyyy')}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Badge
            variant="outline"
            className={cn('text-sm px-3 py-1', STATUS_STYLES[submission.status])}
          >
            {STATUS_LABELS[submission.status] ?? submission.status}
          </Badge>

          {/* Professor action buttons */}
          {isProfessor && (
            <div className="flex items-center gap-2">
              {/* Edit Grades toggle */}
              {canEdit && !isEditMode && (
                <Button size="sm" variant="outline" onClick={enterEditMode}>
                  <Edit2 className="h-4 w-4 mr-1.5" />
                  Edit Grades
                </Button>
              )}

              {/* Save / Cancel while editing */}
              {isEditMode && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={cancelEditMode}
                    disabled={adjustGradesMutation.isPending}
                  >
                    <X className="h-4 w-4 mr-1.5" />
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSaveGrades}
                    disabled={adjustGradesMutation.isPending}
                  >
                    {adjustGradesMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4 mr-1.5" />
                    )}
                    Save Changes
                  </Button>
                </>
              )}

              {/* Approve / Reject (only when not in edit mode) */}
              {!isEditMode && canApprove && (
                <Button
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending}
                >
                  {approveMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                  ) : (
                    <CheckCircle className="h-4 w-4 mr-1.5" />
                  )}
                  Approve
                </Button>
              )}
              {!isEditMode && canReject && (
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => rejectMutation.mutate()}
                  disabled={rejectMutation.isPending}
                >
                  {rejectMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                  ) : (
                    <ThumbsDown className="h-4 w-4 mr-1.5" />
                  )}
                  Reject
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Edit-mode banner */}
      {isEditMode && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg border border-amber-200 bg-amber-50 text-amber-800 text-sm">
          <Edit2 className="h-4 w-4 shrink-0" />
          <span>
            You are editing grades. Change any score or feedback below, then click{' '}
            <strong>Save Changes</strong>. The submission will be marked as{' '}
            <em>awaiting approval</em> until you approve it.
          </span>
        </div>
      )}

      {/* ── Score overview ── */}
      {isGradedOrBeyond && (
        <Card className="animate-fade-up">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Overall Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-3 mb-4">
              <span className="text-5xl font-bold">
                {submission.totalScore?.toFixed?.(1) ?? submission.totalScore}
              </span>
              <span className="text-2xl text-muted-foreground mb-1">/ {submission.maxScore}</span>
              <span
                className={cn(
                  'text-lg font-semibold ml-auto',
                  scorePercentage >= 70
                    ? 'text-emerald-600'
                    : scorePercentage >= 50
                    ? 'text-amber-600'
                    : 'text-destructive'
                )}
              >
                {scorePercentage}%
              </span>
            </div>
            <Progress value={scorePercentage} className="h-3" />
            {submission.status === 'approved' && (
              <p className="text-xs text-emerald-600 mt-2">
                Approved — these results are visible to the student.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── Per-question results ── */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Detailed Results</h2>

        {submission.answers && submission.answers.length > 0 ? (
          submission.answers.map((answer: any, index: number) => {
            const question = exam?.questions?.find((q: any) => q.id === answer.questionId);
            const result = answer.gradingResult;
            const gid = result?.id ?? answer.gradingResultId;

            return (
              <Card
                key={answer.questionId}
                className="animate-fade-up"
                style={{ animationDelay: `${index * 80}ms` }}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle className="text-base">
                        Question {answer.questionNumber}
                      </CardTitle>
                      {question && (
                        <p className="text-sm text-muted-foreground mt-0.5">
                          {question.text}
                        </p>
                      )}
                    </div>

                    {/* Score badge / editable score */}
                    {result && (
                      isEditMode ? (
                        <div className="flex items-center gap-1.5 shrink-0">
                          <Label className="text-xs text-muted-foreground whitespace-nowrap">Score:</Label>
                          <Input
                            type="number"
                            min={0}
                            max={result.maxScore}
                            step={0.5}
                            className="w-20 h-8 text-sm"
                            defaultValue={result.score}
                            onChange={(e) =>
                              setEditingGrades((prev) => ({
                                ...prev,
                                [gid]: { ...prev[gid], score: parseFloat(e.target.value) },
                              }))
                            }
                          />
                          <span className="text-sm text-muted-foreground shrink-0">
                            / {result.maxScore} pts
                          </span>
                        </div>
                      ) : (
                        <Badge
                          variant="outline"
                          className={cn(
                            'shrink-0',
                            result.isCorrect
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : 'bg-red-50 text-red-700 border-red-200'
                          )}
                        >
                          {result.score} / {result.maxScore} pts
                        </Badge>
                      )
                    )}
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  {/* Student's answer */}
                  <div className="p-3 rounded-lg bg-muted/40">
                    <p className="text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wide">
                      Student's Answer
                    </p>
                    {answer.extractedText ? (
                      <div
                        className="prose prose-sm max-w-none"
                        dangerouslySetInnerHTML={{ __html: answer.extractedText }}
                      />
                    ) : (
                      <p className="font-mono text-sm text-muted-foreground">
                        {answer.extractedLatex ?? 'No answer provided'}
                      </p>
                    )}
                  </div>

                  {/* Step-by-step results */}
                  {result?.stepResults && result.stepResults.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        Step Analysis
                      </p>
                      {result.stepResults.map((step: any) => (
                        <div
                          key={step.stepNumber}
                          className={cn(
                            'flex items-start gap-3 p-3 rounded-lg border',
                            step.isCorrect
                              ? 'bg-emerald-50/50 border-emerald-200'
                              : 'bg-red-50/50 border-red-200'
                          )}
                        >
                          {step.isCorrect ? (
                            <CheckCircle2 className="h-5 w-5 text-emerald-600 mt-0.5 shrink-0" />
                          ) : (
                            <XCircle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
                          )}

                          <div className="flex-1 space-y-1.5">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm">Step {step.stepNumber}</span>

                              {isEditMode ? (
                                <div className="flex items-center gap-1">
                                  <Input
                                    type="number"
                                    min={0}
                                    max={step.maxScore}
                                    step={0.5}
                                    className="w-16 h-6 text-xs"
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
                                  <span className="text-xs text-muted-foreground">
                                    / {step.maxScore} pts
                                  </span>
                                </div>
                              ) : (
                                <Badge variant="secondary" className="text-xs">
                                  {step.score} / {step.maxScore} pts
                                </Badge>
                              )}
                            </div>

                            {isEditMode ? (
                              <Textarea
                                className="text-sm min-h-[60px]"
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
                                <p className="text-sm text-muted-foreground">{step.feedback}</p>
                              )
                            )}

                            {!step.isCorrect && step.expected && (
                              <div className="text-xs space-y-0.5 pt-1">
                                <p>
                                  <span className="text-muted-foreground">Expected: </span>
                                  <span className="font-mono">{step.expected}</span>
                                </p>
                                <p>
                                  <span className="text-muted-foreground">Received: </span>
                                  <span className="font-mono">{step.received}</span>
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Overall question feedback */}
                  {isEditMode ? (
                    <div className="space-y-1.5">
                      <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        Overall Feedback
                      </Label>
                      <Textarea
                        className="min-h-[80px]"
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
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-primary/5 border border-primary/20">
                      <AlertCircle className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                      <div>
                        <p className="font-medium text-sm">Feedback</p>
                        <p className="text-sm text-muted-foreground">{result.feedback}</p>
                      </div>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            );
          })
        ) : (
          <Card>
            <CardContent className="py-8 text-center">
              <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">
                {submission.status === 'pending'
                  ? 'This submission is awaiting grading'
                  : 'Grading in progress…'}
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* ── Bottom action bar (save / approve from bottom of long page) ── */}
      {isProfessor && isGradedOrBeyond && (
        <>
          <Separator />
          <div className="flex items-center justify-between pb-4">
            <p className="text-sm text-muted-foreground">
              {isEditMode
                ? 'Review your changes above, then save.'
                : submission.status === 'approved'
                ? 'This submission has been approved and is visible to the student.'
                : 'You can edit marks or approve/reject this submission.'}
            </p>
            <div className="flex items-center gap-2">
              {isEditMode ? (
                <>
                  <Button variant="outline" size="sm" onClick={cancelEditMode} disabled={adjustGradesMutation.isPending}>
                    <X className="h-4 w-4 mr-1.5" />
                    Cancel
                  </Button>
                  <Button size="sm" onClick={handleSaveGrades} disabled={adjustGradesMutation.isPending}>
                    {adjustGradesMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4 mr-1.5" />
                    )}
                    Save Changes
                  </Button>
                </>
              ) : (
                <>
                  {canEdit && (
                    <Button variant="outline" size="sm" onClick={enterEditMode}>
                      <Edit2 className="h-4 w-4 mr-1.5" />
                      Edit Grades
                    </Button>
                  )}
                  {canApprove && (
                    <Button
                      size="sm"
                      className="bg-emerald-600 hover:bg-emerald-700 text-white"
                      onClick={() => approveMutation.mutate()}
                      disabled={approveMutation.isPending}
                    >
                      {approveMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                      ) : (
                        <CheckCircle className="h-4 w-4 mr-1.5" />
                      )}
                      Approve Grades
                    </Button>
                  )}
                  {canReject && (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => rejectMutation.mutate()}
                      disabled={rejectMutation.isPending}
                    >
                      {rejectMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                      ) : (
                        <ThumbsDown className="h-4 w-4 mr-1.5" />
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
    </div>
  );
}
