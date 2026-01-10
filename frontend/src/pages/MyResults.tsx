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
  
  const gradedSubmissions = studentSubmissions.filter((s: any) => s.status === 'graded');
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
          <h1 className="text-3xl font-bold tracking-tight">My Results</h1>
          <p className="text-muted-foreground mt-1">View your exam submissions and grades</p>
        </div>

        {/* Stats Overview */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="animate-fade-up">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                Total Submissions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{studentSubmissions.length}</p>
            </CardContent>
          </Card>

          <Card className="animate-fade-up" style={{ animationDelay: '50ms' }}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4" />
                Graded
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{gradedSubmissions.length}</p>
            </CardContent>
          </Card>

          <Card className="animate-fade-up" style={{ animationDelay: '100ms' }}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Average Score
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-2">
                <p className="text-3xl font-bold">{averageScore}%</p>
              </div>
              <Progress value={averageScore} className="h-2 mt-2" />
            </CardContent>
          </Card>
        </div>

        {/* Submissions List */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">All Submissions</h2>
          
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
                          <p className="text-sm text-muted-foreground">
                            Submitted {format(new Date(submission.submittedAt), 'MMMM d, yyyy')}
                          </p>
                        </div>

                        <div className="flex items-center gap-4">
                          {submission.status === 'graded' && scorePercentage !== null ? (
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
                                  : 'bg-primary/10 text-primary border-primary/20'
                              )}
                            >
                              <Clock className="h-3 w-3" />
                              {submission.status === 'pending' ? 'Pending' : 'Grading'}
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