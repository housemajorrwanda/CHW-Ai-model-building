import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Submission } from '@/types';
import { ArrowRight, Clock, CheckCircle2, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';

interface RecentSubmissionsProps {
  submissions: Submission[];
  showStudent?: boolean;
}

export function RecentSubmissions({ submissions, showStudent = true }: RecentSubmissionsProps) {
  const statusConfig = {
    pending: { label: 'Pending', icon: Clock, className: 'bg-warning/10 text-warning border-warning/20' },
    grading: { label: 'Grading', icon: Loader2, className: 'bg-primary/10 text-primary border-primary/20' },
    graded: { label: 'Graded', icon: CheckCircle2, className: 'bg-success/10 text-success border-success/20' },
  };

  return (
    <div className="rounded-xl border bg-card p-6 animate-fade-up">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold">Recent Submissions</h3>
        <Button variant="ghost" size="sm" asChild>
          <Link to="/submissions" className="text-muted-foreground hover:text-foreground">
            View all <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </Button>
      </div>

      <div className="space-y-4">
        {submissions.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">No submissions yet</p>
        ) : (
          submissions.map((submission) => {
            const status = statusConfig[submission.status];
            const StatusIcon = status.icon;

            return (
              <div
                key={submission.id}
                className="flex items-center justify-between p-4 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary font-medium">
                    {submission.studentName.charAt(0)}
                  </div>
                  <div>
                    {showStudent && (
                      <p className="font-medium">{submission.studentName}</p>
                    )}
                    <p className="text-sm text-muted-foreground">
                      {formatDistanceToNow(submission.submittedAt, { addSuffix: true })}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {submission.status === 'graded' && submission.totalScore !== undefined && (
                    <span className="font-mono font-semibold">
                      {submission.totalScore}/{submission.maxScore}
                    </span>
                  )}
                  <Badge variant="outline" className={cn('gap-1', status.className)}>
                    <StatusIcon className={cn('h-3 w-3', submission.status === 'grading' && 'animate-spin')} />
                    {status.label}
                  </Badge>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}