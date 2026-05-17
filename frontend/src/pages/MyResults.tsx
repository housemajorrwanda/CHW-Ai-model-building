import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { TrendingUp, Clock, CheckCircle2, Eye, BarChart3, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { useQuery } from '@tanstack/react-query';
import { submissionsAPI, examsAPI } from '@/lib/api';

export default function MyResults() {
  // Fetch submissions
  const { data: submissions, isLoading } = useQuery({
    queryKey: ['submissions'],
    queryFn: () => submissionsAPI.getAll(),
  });

  // Fetch exams to get exam details
  const { data: exams } = useQuery({
    queryKey: ['exams'],
    queryFn: () => examsAPI.getAll(),
  });

  const studentSubmissions = submissions || [];
  
  const gradedSubmissions = studentSubmissions.filter((s: any) => s.status === 'approved');
  const averageScore = gradedSubmissions.length > 0
    ? Math.round(gradedSubmissions.reduce((sum: number, s: any) => sum + ((s.totalScore || 0) / s.maxScore) * 100, 0) / gradedSubmissions.length)
    : 0;

  if (isLoading) {
    return (
      <div className="mx-auto flex max-w-7xl min-h-[400px] items-center justify-center pb-8">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 pb-8">
      <header
        className={cn(
          'rounded-2xl border border-emerald-200/55 bg-gradient-to-br from-emerald-50/75 via-white to-teal-50/30 p-6 shadow-sm dark:from-emerald-950/25 dark:via-card dark:to-teal-950/15 dark:border-emerald-900/45 sm:p-8'
        )}
      >
        <p className="text-xs font-semibold uppercase tracking-wider text-emerald-800 dark:text-emerald-300">Results</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">My results</h1>
        <p className="mt-2 max-w-2xl text-[1.05rem] leading-relaxed text-muted-foreground">
          Scores and feedback appear here after your instructor releases them.
        </p>
      </header>

      <Card className="overflow-hidden rounded-2xl border border-border/80 shadow-sm dark:border-border/60">
        <CardHeader className="border-b border-border/60 pb-4 dark:border-border/50">
          <CardTitle className="text-base font-bold">Overview</CardTitle>
          <CardDescription>Attempts, released grades, and your running average across scored work</CardDescription>
        </CardHeader>
        <CardContent className="space-y-8 pt-6">
          <div className="grid gap-5 md:grid-cols-3">
            <Card className="animate-fade-up rounded-2xl border border-rose-200/70 bg-gradient-to-br from-rose-50/90 to-white shadow-sm dark:border-rose-900/45 dark:from-rose-950/30">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-rose-900/80 dark:text-rose-200/90">
                  <BarChart3 className="h-4 w-4" />
                  Attempts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold tabular-nums">{studentSubmissions.length}</p>
              </CardContent>
            </Card>

            <Card
              className="animate-fade-up rounded-2xl border border-violet-200/70 bg-gradient-to-br from-violet-50/80 to-white shadow-sm dark:border-violet-900/45 dark:from-violet-950/30"
              style={{ animationDelay: '50ms' }}
            >
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-violet-900/80 dark:text-violet-200/90">
                  <CheckCircle2 className="h-4 w-4" />
                  Released
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold tabular-nums">{gradedSubmissions.length}</p>
              </CardContent>
            </Card>

            <Card
              className="animate-fade-up rounded-2xl border border-sky-200/70 bg-gradient-to-br from-sky-50/85 to-white shadow-sm dark:border-sky-900/45 dark:from-sky-950/30"
              style={{ animationDelay: '100ms' }}
            >
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-sky-900/80 dark:text-sky-200/90">
                  <TrendingUp className="h-4 w-4" />
                  Average
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-end gap-2">
                  <p
                    className={cn(
                      'text-3xl font-bold tabular-nums',
                      averageScore < 40 && 'text-amber-700 dark:text-amber-400',
                      averageScore >= 70 && 'text-emerald-700 dark:text-emerald-400'
                    )}
                  >
                    {averageScore}%
                  </p>
                </div>
                <Progress
                  value={averageScore}
                  className={cn(
                    'mt-2 h-2',
                    averageScore >= 70 && '[&>div]:bg-emerald-600',
                    averageScore >= 40 && averageScore < 70 && '[&>div]:bg-amber-500',
                    averageScore < 40 && '[&>div]:bg-amber-600'
                  )}
                />
              </CardContent>
            </Card>
          </div>

          <div className="border-t border-border/60 pt-8 dark:border-border/40">
            <h2 className="mb-1 text-lg font-semibold tracking-tight">History</h2>
            <p className="mb-4 text-sm text-muted-foreground">Each attempt is shown below as its own card</p>
            {studentSubmissions.length === 0 ? (
              <div className="rounded-xl border border-dashed border-violet-200/80 bg-violet-50/30 py-12 text-center dark:border-violet-900/50 dark:bg-violet-950/20">
                <p className="text-muted-foreground">No submissions yet</p>
                <Button asChild className="mt-4">
                  <Link to="/my-exams">View available exams</Link>
                </Button>
              </div>
            ) : (
              <ul className="space-y-4" aria-label="Submission history">
                {studentSubmissions.map((submission: any, index: number) => {
                  const exam = exams?.find((e: any) => e.id === submission.examId);
                  const scorePercentage = submission.totalScore
                    ? Math.round((submission.totalScore / submission.maxScore) * 100)
                    : null;

                  return (
                    <li key={submission.id}>
                      <Card
                        className={cn(
                          'animate-fade-up overflow-hidden rounded-2xl border border-border/70 bg-card shadow-sm transition-all hover:shadow-md border-l-4 border-l-emerald-500 dark:border-l-emerald-400'
                        )}
                        style={{ animationDelay: `${index * 50}ms` }}
                      >
                        <CardContent className="p-4 sm:p-5">
                          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                            <div className="min-w-0 space-y-1">
                              <h3 className="font-semibold leading-snug">{exam?.title || 'Exam'}</h3>
                              <p className="text-sm text-muted-foreground tabular-nums">
                                {format(new Date(submission.submittedAt), 'MMM d, yyyy')}
                              </p>
                            </div>

                            <div className="flex shrink-0 flex-wrap items-center gap-3 sm:justify-end">
                              {submission.status === 'approved' && scorePercentage !== null ? (
                                <div className="text-left sm:text-right">
                                  <p className="text-2xl font-bold tabular-nums">
                                    {submission.totalScore?.toFixed(1)}/{submission.maxScore}
                                  </p>
                                  <p
                                    className={cn(
                                      'text-sm font-medium tabular-nums',
                                      scorePercentage >= 70
                                        ? 'text-success'
                                        : scorePercentage >= 50
                                          ? 'text-warning'
                                          : 'text-destructive'
                                    )}
                                  >
                                    {scorePercentage}%
                                  </p>
                                </div>
                              ) : (
                                <Badge
                                  variant="outline"
                                  className={cn(
                                    'gap-1',
                                    submission.status === 'pending'
                                      ? 'border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-200'
                                      : submission.status === 'approved'
                                        ? 'bg-muted/60 text-muted-foreground'
                                        : 'border-primary/25 bg-primary/10 text-primary'
                                  )}
                                >
                                  <Clock className="h-3 w-3" />
                                  {submission.status === 'pending'
                                    ? 'Pending'
                                    : submission.status === 'approved'
                                      ? 'Released'
                                      : submission.status === 'graded' || submission.status === 'awaiting_approval'
                                        ? 'In review'
                                        : 'In progress'}
                                </Badge>
                              )}

                              <Button variant="outline" size="sm" asChild className="shadow-sm">
                                <Link to={`/submissions/${submission.id}`}>
                                  <Eye className="mr-1 h-4 w-4" />
                                  View
                                </Link>
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}