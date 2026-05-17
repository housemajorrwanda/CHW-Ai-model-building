import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { examsAPI, submissionsAPI } from '@/lib/api';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileText, Clock, CheckCircle2, Calendar, Award, Loader2, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { getStudentExamUiStatus, partitionStudentExams } from '@/lib/studentExamBuckets';

const examCardShell =
  'relative overflow-hidden rounded-2xl border border-border/70 bg-card shadow-sm transition-all hover:border-border hover:shadow-md dark:bg-card';

function examAccentClass(status: ReturnType<typeof getStudentExamUiStatus>['status']) {
  switch (status) {
    case 'available':
      return 'border-l-teal-500';
    case 'overdue':
      return 'border-l-rose-500';
    case 'pending':
    case 'grading':
      return 'border-l-amber-500';
    case 'graded':
      return 'border-l-emerald-500';
    default:
      return 'border-l-muted-foreground/30';
  }
}

const tabListClass =
  'grid h-auto w-full grid-cols-3 gap-0 rounded-none border-0 border-b border-border/70 bg-transparent p-0 dark:border-border/50';
const tabTriggerClass =
  'rounded-none border-b-2 border-transparent py-3 text-sm font-medium text-muted-foreground shadow-none transition-colors data-[state=active]:border-teal-600 data-[state=active]:bg-transparent data-[state=active]:text-teal-800 data-[state=active]:shadow-none dark:data-[state=active]:border-teal-400 dark:data-[state=active]:text-teal-200';

interface Exam {
  id: string;
  courseId: string;
  title: string;
  description: string;
  totalPoints: number;
  dueDate: string | null;
  isPublished: boolean;
  publishedAt: string | null;
  createdAt: string;
  questions: any[];
}

interface Submission {
  id: string;
  examId: string;
  status: string;
  submittedAt: string;
  totalScore: number | null;
  maxScore: number;
}

export default function StudentExams() {
  const navigate = useNavigate();
  const [exams, setExams] = useState<Exam[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [examsData, submissionsData] = await Promise.all([
        examsAPI.getAll(),
        submissionsAPI.getAll()
      ]);
      setExams(examsData);
      setSubmissions(submissionsData);
    } catch (error: any) {
      toast.error('Failed to load exams: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const getExamStatus = (exam: Exam) => {
    const { status, submission } = getStudentExamUiStatus(exam, submissions);
    if (status === 'overdue') return { status: 'overdue' as const, label: 'Overdue', color: 'destructive' as const };
    if (status === 'available') return { status: 'available' as const, label: 'Open', color: 'default' as const };
    if (status === 'graded')
      return { status: 'graded' as const, label: 'Released', color: 'default' as const, submission };
    if (status === 'grading')
      return { status: 'grading' as const, label: 'Under review', color: 'secondary' as const, submission };
    return { status: 'pending' as const, label: 'Submitted', color: 'secondary' as const, submission };
  };

  const { available: availableExams, submitted: submittedExams, graded: gradedExams } = partitionStudentExams(
    exams,
    submissions
  );

  const ExamCard = ({ exam }: { exam: Exam }) => {
    const examStatus = getExamStatus(exam);
    const dueDate = exam.dueDate ? new Date(exam.dueDate) : null;
    const isOverdue = dueDate && dueDate < new Date();

    return (
      <Card className={cn(examCardShell, 'border-l-4', examAccentClass(getStudentExamUiStatus(exam, submissions).status))}>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="rounded-full border-teal-200/80 bg-teal-50/80 text-xs font-medium text-teal-900 dark:border-teal-900/60 dark:bg-teal-950/40 dark:text-teal-100">
                  Exam
                </Badge>
                <span className="font-mono text-[11px] text-muted-foreground tabular-nums">ID {exam.id.slice(0, 8)}</span>
              </div>
              <CardTitle className="text-lg leading-snug">{exam.title}</CardTitle>
              <CardDescription className="line-clamp-2">
                {exam.description || 'No description'}
              </CardDescription>
            </div>
            <Badge variant={examStatus.color as 'default' | 'destructive' | 'secondary'} className="shrink-0 rounded-full">
              {examStatus.label}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <Award className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">
                Total Points: <strong className="text-foreground">{exam.totalPoints}</strong>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">
                Questions: <strong className="text-foreground">{exam.questions.length}</strong>
              </span>
            </div>
            {dueDate && (
              <div className="flex items-center gap-2">
                <Calendar className={`h-4 w-4 ${isOverdue ? 'text-destructive' : 'text-muted-foreground'}`} />
                <span className={isOverdue ? 'text-destructive' : 'text-muted-foreground'}>
                  Due: <strong>{format(dueDate, 'MMM d, yyyy h:mm a')}</strong>
                </span>
              </div>
            )}
            {examStatus.submission &&
              examStatus.status === 'graded' &&
              examStatus.submission.totalScore != null && (
                <div className="flex items-center gap-2 mt-3 p-3 bg-primary/10 rounded-lg">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span className="font-medium">
                    Score: {examStatus.submission.totalScore?.toFixed(1)} / {examStatus.submission.maxScore}
                    <span className="text-muted-foreground ml-2">
                      ({((examStatus.submission.totalScore! / examStatus.submission.maxScore) * 100).toFixed(1)}%)
                    </span>
                  </span>
                </div>
              )}
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-2 border-t border-border/50 bg-muted/20 pt-4 dark:border-border/40">
          {examStatus.status === 'available' && (
            <Button className="w-full rounded-xl" onClick={() => navigate(`/take-exam/${exam.id}`)}>
              Start exam
            </Button>
          )}
          {examStatus.status === 'overdue' && (
            <Button variant="outline" className="w-full rounded-xl" disabled>
              <XCircle className="mr-2 h-4 w-4 text-destructive" />
              Overdue
            </Button>
          )}
          {(examStatus.status === 'pending' || examStatus.status === 'grading') && (
            <Button
              variant="outline"
              className="w-full rounded-xl"
              onClick={() => navigate(`/submissions/${examStatus.submission!.id}`)}
            >
              <Clock className="mr-2 h-4 w-4" />
              View submission
            </Button>
          )}
          {examStatus.status === 'graded' && (
            <Button className="w-full rounded-xl" onClick={() => navigate(`/submissions/${examStatus.submission!.id}`)}>
              <CheckCircle2 className="mr-2 h-4 w-4" />
              View published results
            </Button>
          )}
        </CardFooter>
      </Card>
    );
  };

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
          'rounded-2xl border border-teal-200/60 bg-gradient-to-br from-teal-50/80 via-white to-cyan-50/35 p-6 shadow-sm dark:from-teal-950/30 dark:via-card dark:to-cyan-950/20 dark:border-teal-900/45 sm:p-8'
        )}
      >
        <p className="text-xs font-semibold uppercase tracking-wider text-teal-800 dark:text-teal-300">Exams</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">My exams</h1>
        <p className="mt-2 max-w-2xl text-[1.05rem] leading-relaxed text-muted-foreground">
          Start attempts, track work under review, and open results your instructor has released.
        </p>
      </header>

      <Card className="overflow-hidden rounded-2xl border border-border/80 shadow-sm dark:border-border/60">
        <CardHeader className="border-b border-border/60 pb-4 dark:border-border/50">
          <CardTitle className="text-base font-bold">Your exam list</CardTitle>
          <CardDescription>Open attempts, submissions in review, and released grades</CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          <Tabs defaultValue="available" className="w-full">
            <TabsList className={tabListClass}>
              <TabsTrigger value="available" className={tabTriggerClass}>
                To do ({availableExams.length})
              </TabsTrigger>
              <TabsTrigger value="submitted" className={tabTriggerClass}>
                In review ({submittedExams.length})
              </TabsTrigger>
              <TabsTrigger value="graded" className={tabTriggerClass}>
                Released ({gradedExams.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="available" className="mt-6 space-y-4 focus-visible:outline-none">
              {availableExams.length === 0 ? (
                <div className="rounded-xl border border-dashed border-violet-200/80 bg-violet-50/30 py-14 text-center dark:border-violet-900/50 dark:bg-violet-950/20">
                  <FileText className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
                  <p className="font-medium text-foreground">No exams available right now</p>
                  <p className="mt-1 text-sm text-muted-foreground">Check back later or confirm you&apos;re enrolled in a course</p>
                </div>
              ) : (
                <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                  {availableExams.map((exam) => (
                    <ExamCard key={exam.id} exam={exam} />
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="submitted" className="mt-6 space-y-4 focus-visible:outline-none">
              {submittedExams.length === 0 ? (
                <div className="rounded-xl border border-dashed border-violet-200/80 bg-violet-50/30 py-14 text-center dark:border-violet-900/50 dark:bg-violet-950/20">
                  <Clock className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
                  <p className="font-medium text-foreground">No submissions in review</p>
                  <p className="mt-1 text-sm text-muted-foreground">Submitted work will appear here while it&apos;s being graded</p>
                </div>
              ) : (
                <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                  {submittedExams.map((exam) => (
                    <ExamCard key={exam.id} exam={exam} />
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="graded" className="mt-6 space-y-4 focus-visible:outline-none">
              {gradedExams.length === 0 ? (
                <div className="rounded-xl border border-dashed border-violet-200/80 bg-violet-50/30 py-14 text-center dark:border-violet-900/50 dark:bg-violet-950/20">
                  <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
                  <p className="font-medium text-foreground">No graded exams yet</p>
                  <p className="mt-1 text-sm text-muted-foreground">Released scores show up here after your instructor approves them</p>
                </div>
              ) : (
                <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                  {gradedExams.map((exam) => (
                    <ExamCard key={exam.id} exam={exam} />
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}

