import { useParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Clock, CheckCircle2, XCircle, AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { useQuery } from '@tanstack/react-query';
import { submissionsAPI, examsAPI } from '@/lib/api';

export default function SubmissionDetail() {
  const { id } = useParams();

  // Fetch submission details
  const { data: submission, isLoading, error } = useQuery({
    queryKey: ['submission', id],
    queryFn: () => submissionsAPI.getById(id!),
    enabled: !!id,
  });

  // Fetch exam details
  const { data: exam } = useQuery({
    queryKey: ['exam', submission?.examId],
    queryFn: () => examsAPI.getById(submission!.examId),
    enabled: !!submission?.examId,
  });

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

  return (
    <div className="space-y-6 max-w-4xl">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{exam?.title || 'Exam'}</h1>
            <p className="text-muted-foreground mt-1">
              Submitted by {submission.studentName} on {format(new Date(submission.submittedAt), 'MMMM d, yyyy')}
            </p>
          </div>
          <Badge
            variant="outline"
            className={cn(
              'text-sm px-3 py-1',
              submission.status === 'graded' && 'bg-success/10 text-success border-success/20',
              submission.status === 'pending' && 'bg-warning/10 text-warning border-warning/20',
              submission.status === 'grading' && 'bg-primary/10 text-primary border-primary/20'
            )}
          >
            {submission.status.charAt(0).toUpperCase() + submission.status.slice(1)}
          </Badge>
        </div>

        {/* Score Overview */}
        {submission.status === 'graded' && (
          <Card className="animate-fade-up">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Overall Score</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-3 mb-4">
                <span className="text-5xl font-bold">{submission.totalScore}</span>
                <span className="text-2xl text-muted-foreground mb-1">/ {submission.maxScore}</span>
                <span className={cn(
                  'text-lg font-semibold ml-auto',
                  scorePercentage >= 70 ? 'text-success' : scorePercentage >= 50 ? 'text-warning' : 'text-destructive'
                )}>
                  {scorePercentage}%
                </span>
              </div>
              <Progress value={scorePercentage} className="h-3" />
            </CardContent>
          </Card>
        )}

        {/* Questions and Answers */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Detailed Results</h2>
          
          {submission.answers && submission.answers.length > 0 ? (
            submission.answers.map((answer, index) => {
              const question = exam?.questions?.find((q: any) => q.id === answer.questionId);
              const result = answer.gradingResult;

              return (
                <Card key={answer.questionId} className="animate-fade-up" style={{ animationDelay: `${index * 100}ms` }}>
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-base">
                        Question {answer.questionNumber}
                      </CardTitle>
                      {result && (
                        <Badge
                          variant="outline"
                          className={cn(
                            result.isCorrect
                              ? 'bg-success/10 text-success border-success/20'
                              : 'bg-destructive/10 text-destructive border-destructive/20'
                          )}
                        >
                          {result.score}/{result.maxScore} pts
                        </Badge>
                      )}
                    </div>
                    {question && (
                      <p className="text-sm text-muted-foreground">{question.text}</p>
                    )}
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Student's Answer */}
                    <div className="p-4 rounded-lg bg-muted/50">
                      <p className="text-sm font-medium text-muted-foreground mb-2">Student's Answer</p>
                      {answer.extractedText ? (
                        <div 
                          className="prose prose-sm max-w-none"
                          dangerouslySetInnerHTML={{ __html: answer.extractedText }}
                        />
                      ) : (
                        <p className="font-mono text-muted-foreground">{answer.extractedLatex || 'No answer provided'}</p>
                      )}
                    </div>

                    {/* Step-by-Step Results */}
                    {result?.stepResults && result.stepResults.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-sm font-medium text-muted-foreground">Step Analysis</p>
                        {result.stepResults.map((step) => (
                          <div
                            key={step.stepNumber}
                            className={cn(
                              'flex items-start gap-3 p-3 rounded-lg border',
                              step.isCorrect ? 'bg-success/5 border-success/20' : 'bg-destructive/5 border-destructive/20'
                            )}
                          >
                            {step.isCorrect ? (
                              <CheckCircle2 className="h-5 w-5 text-success mt-0.5" />
                            ) : (
                              <XCircle className="h-5 w-5 text-destructive mt-0.5" />
                            )}
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-medium text-sm">Step {step.stepNumber}</span>
                                <Badge variant="secondary" className="text-xs">
                                  {step.score}/{step.maxScore} pts
                                </Badge>
                              </div>
                              <p className="text-sm text-muted-foreground">{step.feedback}</p>
                              {!step.isCorrect && step.expected && (
                                <div className="mt-2 text-xs space-y-1">
                                  <p><span className="text-muted-foreground">Expected:</span> <span className="font-mono">{step.expected}</span></p>
                                  <p><span className="text-muted-foreground">Received:</span> <span className="font-mono">{step.received}</span></p>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Overall Feedback */}
                    {result?.feedback && result.feedback.trim() !== '' && (
                      <div className="flex items-start gap-3 p-3 rounded-lg bg-primary/5 border border-primary/20">
                        <AlertCircle className="h-5 w-5 text-primary mt-0.5" />
                        <div>
                          <p className="font-medium text-sm">Feedback</p>
                          <p className="text-sm text-muted-foreground">{result.feedback}</p>
                        </div>
                      </div>
                    )}
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
                    : 'Grading in progress...'}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
  );
}