import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My results</h1>
          <p className="mt-1 text-sm text-muted-foreground">Scores appear after your instructor releases them</p>
        </div>

        {/* Stats Overview */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="animate-fade-up border-border/80 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <BarChart3 className="h-4 w-4" />
                Attempts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold tabular-nums">{studentSubmissions.length}</p>
            </CardContent>
          </Card>

          <Card className="animate-fade-up border-border/80 shadow-sm" style={{ animationDelay: '50ms' }}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <CheckCircle2 className="h-4 w-4" />
                Released
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold tabular-nums">{gradedSubmissions.length}</p>
            </CardContent>
          </Card>

          <Card className="animate-fade-up border-border/80 shadow-sm" style={{ animationDelay: '100ms' }}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
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

        {/* Submissions List */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold tracking-tight">History</h2>
          
          {studentSubmissions.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">No submissions yet</p>
                <Button asChild className="mt-4">
                  <Link to="/my-exams">View Available Exams</Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {studentSubmissions.map((submission: any, index: number) => {
                const exam = exams?.find((e: any) => e.id === submission.examId);
                const scorePercentage = submission.totalScore
                  ? Math.round((submission.totalScore / submission.maxScore) * 100)
                  : null;

                return (
                  <Card
                    key={submission.id}
                    className="animate-fade-up hover:shadow-md transition-shadow"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold">{exam?.title || 'Exam'}</h3>
                          </div>
                          <p className="text-sm text-muted-foreground tabular-nums">
                            {format(new Date(submission.submittedAt), 'MMM d, yyyy')}
                          </p>
                        </div>

                        <div className="flex items-center gap-4">
                          {submission.status === 'approved' && scorePercentage !== null ? (
                            <div className="text-right">
                              <p className="text-2xl font-bold">
                                {submission.totalScore?.toFixed(1)}/{submission.maxScore}
                              </p>
                              <p className={cn(
                                'text-sm font-medium',
                                scorePercentage >= 70 ? 'text-success' : scorePercentage >= 50 ? 'text-warning' : 'text-destructive'
                              )}>
                                {scorePercentage}%
                              </p>
                            </div>
                          ) : (
                            <Badge
                              variant="outline"
                              className={cn(
                                'gap-1',
                                submission.status === 'pending'
                                  ? 'bg-warning/10 text-warning border-warning/20'
                                  : submission.status === 'approved'
                                  ? 'bg-muted/50 text-muted-foreground'
                                  : 'bg-primary/10 text-primary border-primary/20'
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

                          <Button variant="outline" size="sm" asChild>
                            <Link to={`/submissions/${submission.id}`}>
                              <Eye className="h-4 w-4 mr-1" />
                              View
                            </Link>
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </div>
  );
}