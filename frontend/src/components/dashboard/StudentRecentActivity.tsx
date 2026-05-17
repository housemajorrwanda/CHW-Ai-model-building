import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { Submission } from '@/types';
import { ArrowRight, ClipboardList, Clock, CheckCircle2, Loader2 } from 'lucide-react';
import { cn, formatScoreDisplay } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';

interface StudentRecentActivityProps {
  submissions: Submission[];
  examTitleById: Map<string, string>;
}

const statusRow: Record<
  string,
  { label: string; icon: typeof Clock; badgeClass: string }
> = {
  pending: {
    label: 'Pending',
    icon: Clock,
    badgeClass:
      'border-amber-200/80 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-100',
  },
  grading: {
    label: 'Grading',
    icon: Loader2,
    badgeClass:
      'border-violet-200/80 bg-violet-50 text-violet-900 dark:border-violet-800 dark:bg-violet-950/50 dark:text-violet-100',
  },
  graded: {
    label: 'Graded',
    icon: CheckCircle2,
    badgeClass:
      'border-sky-200/80 bg-sky-50 text-sky-900 dark:border-sky-800 dark:bg-sky-950/50 dark:text-sky-100',
  },
  awaiting_approval: {
    label: 'In review',
    icon: Clock,
    badgeClass:
      'border-indigo-200/80 bg-indigo-50 text-indigo-900 dark:border-indigo-800 dark:bg-indigo-950/50 dark:text-indigo-100',
  },
  approved: {
    label: 'Released',
    icon: CheckCircle2,
    badgeClass:
      'border-emerald-200/80 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-100',
  },
};

export function StudentRecentActivity({ submissions, examTitleById }: StudentRecentActivityProps) {
  const scoreEligible = (s: Submission) =>
    ['graded', 'awaiting_approval', 'approved'].includes(s.status) && s.totalScore != null;

  return (
    <div className="overflow-hidden rounded-2xl border border-border/70 bg-card shadow-sm dark:border-border/60">
      <div className="flex flex-col gap-3 border-b border-border/60 px-5 py-4 sm:flex-row sm:items-center sm:justify-between dark:border-border/50">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-500/15 text-teal-700 dark:bg-teal-500/20 dark:text-teal-300">
            <ClipboardList className="h-5 w-5" />
          </span>
          <div>
            <h2 className="text-lg font-semibold tracking-tight">Recent activity</h2>
            <p className="text-sm text-muted-foreground">Your latest attempts and grading updates</p>
          </div>
        </div>
        <Button variant="outline" size="sm" className="shrink-0 rounded-full border-teal-200/80 font-medium dark:border-teal-900/60" asChild>
          <Link to="/my-results">
            All results
            <ArrowRight className="ml-1.5 h-4 w-4" />
          </Link>
        </Button>
      </div>

      <div className="p-4 sm:p-5">
        {submissions.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/80 bg-muted/20 py-12 text-center">
            <ClipboardList className="mb-3 h-10 w-10 text-muted-foreground/70" />
            <p className="font-medium text-foreground">No attempts yet</p>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">
              When you submit an exam, it will show up here with status updates.
            </p>
            <Button className="mt-4 rounded-full" size="sm" asChild>
              <Link to="/my-exams">Go to my exams</Link>
            </Button>
          </div>
        ) : (
          <ul className="space-y-3">
            {submissions.map((submission) => {
              const cfg = statusRow[submission.status] || statusRow.pending;
              const StatusIcon = cfg.icon;
              const title = examTitleById.get(submission.examId) || 'Exam';
              const pts = scoreEligible(submission) ? formatScoreDisplay(submission.totalScore) : null;

              return (
                <li key={submission.id}>
                  <Link
                    to={`/submissions/${submission.id}`}
                    className="group flex flex-col gap-3 rounded-xl border border-border/60 bg-muted/10 p-4 transition-all hover:border-teal-300/60 hover:bg-teal-50/25 hover:shadow-sm dark:hover:border-teal-800/50 dark:hover:bg-teal-950/20 sm:flex-row sm:items-stretch sm:justify-between sm:gap-4"
                  >
                    <div className="flex min-w-0 flex-1 gap-3">
                      <span
                        className="hidden w-1 shrink-0 rounded-full bg-teal-500/80 sm:block dark:bg-teal-400/70"
                        aria-hidden
                      />
                      <div className="min-w-0 flex-1 space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="outline" className={cn('rounded-full border px-2.5 py-0.5 text-xs font-medium', cfg.badgeClass)}>
                            <StatusIcon className={cn('mr-1 h-3 w-3', submission.status === 'grading' && 'animate-spin')} />
                            {cfg.label}
                          </Badge>
                          <span className="font-mono text-[11px] text-muted-foreground tabular-nums">ID {submission.id.slice(0, 8)}…</span>
                        </div>
                        <p className="font-semibold leading-snug text-foreground group-hover:text-teal-900 dark:group-hover:text-teal-100">
                          {title}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Submitted {formatDistanceToNow(new Date(submission.submittedAt), { addSuffix: true })}
                        </p>
                      </div>
                    </div>

                    <div className="flex shrink-0 flex-row items-center justify-between gap-3 border-t border-border/50 pt-3 sm:flex-col sm:items-end sm:justify-center sm:border-l sm:border-t-0 sm:pl-4 sm:pt-0 dark:border-border/40">
                      {pts != null ? (
                        <p className="font-mono text-lg font-bold tabular-nums text-foreground">
                          {pts}
                          <span className="font-sans text-sm font-medium text-muted-foreground"> / {submission.maxScore}</span>
                        </p>
                      ) : (
                        <span className="text-sm text-muted-foreground">Score pending</span>
                      )}
                      <span className="inline-flex items-center text-sm font-medium text-teal-700 dark:text-teal-400">
                        View
                        <ArrowRight className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                      </span>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
