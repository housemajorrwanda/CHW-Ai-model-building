import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { api } from '@/api/client';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  ArrowLeft,
  FileText,
  Calendar,
  Clock,
  Award,
  BookOpen,
  CheckCircle2,
  Image,
  Atom,
} from 'lucide-react';
import { format } from 'date-fns';
import { useAuth } from '@/contexts/AuthContext';

export default function ExamDetail() {
  const { examId } = useParams<{ examId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  // Fetch exam details
  const { data: exam, isLoading } = useQuery({
    queryKey: ['exam', examId],
    queryFn: () => api.exams.getById(examId!),
    enabled: !!examId,
  });

  // Fetch course info
  const { data: course } = useQuery({
    queryKey: ['course', exam?.courseId],
    queryFn: () => api.courses.getById(exam!.courseId),
    enabled: !!exam?.courseId,
  });

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <p>Loading exam...</p>
        </div>
      </DashboardLayout>
    );
  }

  if (!exam) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-64">
          <p className="text-muted-foreground mb-4">Exam not found</p>
          <Button onClick={() => navigate('/exams')}>Back to Exams</Button>
        </div>
      </DashboardLayout>
    );
  }

  const renderQuestion = (question: any, parentNumber: string = '', level: number = 0) => {
    const questionNumber = parentNumber ? `${parentNumber}.${question.number}` : question.number.toString();

    return (
      <Card key={question.id} className={level > 0 ? 'ml-8 border-l-2' : ''}>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <Badge variant={level === 0 ? 'default' : 'secondary'}>
                Q{questionNumber}
              </Badge>
              <div>
                <CardTitle className="text-base">
                  {question.text || '(No question text)'}
                </CardTitle>
                {question.richContent && (
                  <div className="mt-2 prose prose-sm max-w-none">
                    {/* Render rich content if available */}
                    <p className="text-sm text-muted-foreground">
                      (Rich content available)
                    </p>
                  </div>
                )}
              </div>
            </div>
            <Badge variant="outline">{question.points} pts</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Attachments */}
          {question.attachments && question.attachments.length > 0 && (
            <div>
              <p className="text-sm font-semibold mb-2">Attachments:</p>
              <div className="flex flex-wrap gap-2">
                {question.attachments.map((att: any, idx: number) => (
                  <Badge key={idx} variant="secondary" className="gap-1">
                    <Image className="h-3 w-3" />
                    {att.filename}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Embedded Content */}
          {question.embeddedContent && question.embeddedContent.length > 0 && (
            <div>
              <p className="text-sm font-semibold mb-2">Embedded Content:</p>
              <div className="flex flex-wrap gap-2">
                {question.embeddedContent.map((content: any, idx: number) => (
                  <Badge key={idx} variant="secondary" className="gap-1">
                    <Atom className="h-3 w-3" />
                    {content.contentType}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Gold Solution Steps */}
          {question.goldSolutionSteps && question.goldSolutionSteps.length > 0 && (
            <div className="border-t pt-4">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <p className="text-sm font-semibold">Gold Solution Steps:</p>
              </div>
              <div className="space-y-2">
                {question.goldSolutionSteps.map((step: any, idx: number) => (
                  <div key={idx} className="p-3 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-green-900">
                        Step {step.stepNumber}
                      </span>
                      <span className="text-xs text-green-700">
                        {step.points} pts
                        {step.required && (
                          <Badge variant="secondary" className="ml-2 text-xs">
                            Required
                          </Badge>
                        )}
                      </span>
                    </div>
                    {step.description && (
                      <p className="text-sm text-green-800 mb-1">{step.description}</p>
                    )}
                    <p className="text-sm font-mono bg-white px-2 py-1 rounded">
                      {step.expression}
                    </p>
                    {step.latex && (
                      <p className="text-xs text-green-700 mt-1">LaTeX: {step.latex}</p>
                    )}
                  </div>
                ))}
              </div>
              {question.finalAnswer && (
                <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm font-semibold text-blue-900 mb-1">Final Answer:</p>
                  <p className="text-sm font-mono text-blue-800">{question.finalAnswer}</p>
                  {question.finalAnswerLatex && (
                    <p className="text-xs text-blue-700 mt-1">
                      LaTeX: {question.finalAnswerLatex}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Sub-questions */}
          {question.subQuestions && question.subQuestions.length > 0 && (
            <div className="border-t pt-4 space-y-3">
              <p className="text-sm font-semibold">Sub-questions:</p>
              {question.subQuestions.map((subQ: any) =>
                renderQuestion(subQ, questionNumber, level + 1)
              )}
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const totalPoints = exam.questions?.reduce((sum: number, q: any) => {
    const subPoints = q.subQuestions?.reduce((subSum: number, sub: any) => subSum + sub.points, 0) || 0;
    return sum + q.points + subPoints;
  }, 0) || 0;

  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/exams')}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold tracking-tight">{exam.title}</h1>
                <Badge variant="secondary">{course?.code}</Badge>
              </div>
              {exam.description && (
                <p className="text-muted-foreground">{exam.description}</p>
              )}
              <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
                {exam.dueDate && (
                  <div className="flex items-center gap-1.5">
                    <Calendar className="h-4 w-4" />
                    Due: {format(new Date(exam.dueDate), 'MMM d, yyyy')}
                  </div>
                )}
                {exam.duration && (
                  <div className="flex items-center gap-1.5">
                    <Clock className="h-4 w-4" />
                    {exam.duration} minutes
                  </div>
                )}
                <div className="flex items-center gap-1.5">
                  <Award className="h-4 w-4" />
                  {totalPoints} total points
                </div>
                <div className="flex items-center gap-1.5">
                  <FileText className="h-4 w-4" />
                  {exam.questions?.length || 0} questions
                </div>
              </div>
            </div>
          </div>
          {user?.role === 'professor' && (
            <Button variant="outline" onClick={() => navigate(`/exams/new?examId=${examId}`)}>
              Edit Exam
            </Button>
          )}
        </div>

        {/* Exam Preview */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Exam Preview
            </CardTitle>
            <CardDescription>
              Complete exam preview with all questions and solutions
            </CardDescription>
          </CardHeader>
          <CardContent>
            {exam.questions && exam.questions.length > 0 ? (
              <div className="space-y-6">
                {exam.questions.map((question: any, idx: number) => (
                  <div key={question.id || idx}>
                    {renderQuestion(question)}
                    {idx < exam.questions.length - 1 && (
                      <Separator className="my-6" />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <FileText className="h-12 w-12 mx-auto mb-3 opacity-20" />
                <p>No questions in this exam</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

