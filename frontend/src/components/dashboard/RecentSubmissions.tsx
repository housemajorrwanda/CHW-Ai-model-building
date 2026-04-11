import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Submission } from '@/types';
import { ArrowRight, Clock, CheckCircle2, Loader2, ClipboardList } from 'lucide-react';
import { cn, formatScoreDisplay } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';

interface RecentSubmissionsProps {
  submissions: Submission[];
  showStudent?: boolean;
}

export function RecentSubmissions({ submissions, showStudent = true }: RecentSubmissionsProps) {
  const statusConfig: Record<string, { label: string; icon: typeof Clock; className: string }> = {
    pending: { label: 'Pending', icon: Clock, className: 'bg-amber-50 text-amber-900 border-amber-200 dark:bg-amber-950/40 dark:text-amber-100 dark:border-amber-800' },
    grading: { label: 'Grading', icon: Loader2, className: 'bg-violet-50 text-violet-900 border-violet-200 dark:bg-violet-950/40 dark:text-violet-100 dark:border-violet-800' },
    graded: { label: 'Graded', icon: CheckCircle2, className: 'bg-sky-50 text-sky-900 border-sky-200 dark:bg-sky-950/40 dark:text-sky-100 dark:border-sky-800' },
    awaiting_approval: {
      label: 'Awaiting approval',
      icon: Clock,
      className: 'bg-indigo-50 text-indigo-900 border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-100 dark:border-indigo-800',
    },
    approved: { label: 'Approved', icon: CheckCircle2, className: 'bg-emerald-50 text-emerald-900 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-100 dark:border-emerald-800' },
  };

  const scoreEligible = (s: Submission) =>
    ['graded', 'awaiting_approval', 'approved'].includes(s.status) && s.totalScore != null;

  return (
    <div className="overflow-hidden rounded-2xl border-2 border-violet-200/70 bg-card shadow-md dark:border-violet-900/50 animate-fade-up">
      <div className="border-b border-violet-100 bg-gradient-to-r from-violet-50/90 to-transparent px-5 py-4 dark:border-violet-900/40 dark:from-violet-950/40">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 text-white shadow-sm">
              <ClipboardList className="h-4 w-4" />
            </span>
            <div>
              <h3 className="text-lg font-bold tracking-tight">Recent submissions</h3>
              <p className="text-xs text-muted-foreground sm:text-sm">Latest activity across your exams</p>
            </div>
          </div>
          <Button variant="outline" size="sm" className="shrink-0 border-violet-200 font-semibold" asChild>
            <Link to="/submissions">
              View all
              <ArrowRight className="ml-1.5 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>

      <div className="p-4 sm:p-5">
        {submissions.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-violet-200 bg-violet-50/40 py-12 text-center dark:border-violet-900 dark:bg-violet-950/20">
            <ClipboardList className="mb-3 h-10 w-10 text-violet-400" />
            <p className="font-medium text-foreground">No submissions yet</p>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">
              When students submit work, it will show up here for quick access.
            </p>
            <Button className="mt-4 bg-violet-600 hover:bg-violet-700" size="sm" asChild>
              <Link to="/exams">View exams</Link>
            </Button>
          </div>
        ) : (
          <ul className="space-y-3">
            {submissions.map((submission) => {
              const status = statusConfig[submission.status] || statusConfig.pending;
              const StatusIcon = status.icon;
              const pts = scoreEligible(submission) ? formatScoreDisplay(submission.totalScore) : null;

              return (
                <li key={submission.id}>
                  <Link
                    to={`/submissions/${submission.id}`}
                    className="flex flex-col gap-3 rounded-xl border border-border/80 bg-muted/20 p-4 transition-all hover:border-violet-300/80 hover:bg-violet-50/40 hover:shadow-sm dark:hover:border-violet-800 dark:hover:bg-violet-950/20 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-100 text-base font-bold text-violet-800 dark:bg-violet-950 dark:text-violet-200">
                        {submission.studentName.charAt(0)}
                      </div>
                      <div className="min-w-0">
                        {showStudent && (
                          <p className="truncate font-semibold text-foreground">{submission.studentName}</p>
                        )}
                        <p className="text-sm text-muted-foreground">
                          {formatDistanceToNow(new Date(submission.submittedAt), { addSuffix: true })}
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                      <div className="min-w-[7rem] text-right sm:text-right">
                        {pts != null ? (
                          <span className="font-mono text-base font-bold tabular-nums text-foreground">
                            {pts}
                            <span className="font-sans text-sm font-medium text-muted-foreground">
                              {' '}
                              / {submission.maxScore}
                            </span>
                          </span>
                        ) : (
                          <span className="text-sm text-muted-foreground">—</span>
                        )}
                      </div>
                      <Badge variant="outline" className={cn('gap-1 border-2 font-semibold', status.className)}>
                        <StatusIcon className={cn('h-3.5 w-3.5', submission.status === 'grading' && 'animate-spin')} />
                        {status.label}
                      </Badge>
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
