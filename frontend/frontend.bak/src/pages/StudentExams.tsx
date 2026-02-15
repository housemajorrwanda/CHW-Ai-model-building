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
    const submission = submissions.find(s => s.examId === exam.id);
    
    if (!submission) {
      // Check if past due date
      if (exam.dueDate && new Date(exam.dueDate) < new Date()) {
        return { status: 'overdue', label: 'Overdue', color: 'destructive' };
      }
      return { status: 'available', label: 'Available', color: 'default' };
    }

    if (submission.status === 'graded' || submission.status === 'approved') {
      return { status: 'graded', label: 'Graded', color: 'default', submission };
    }
    if (submission.status === 'grading' || submission.status === 'awaiting_approval') {
      return { status: 'grading', label: 'Grading', color: 'secondary', submission };
    }
    return { status: 'pending', label: 'Submitted', color: 'secondary', submission };
  };

  const availableExams = exams.filter(exam => {
    const { status } = getExamStatus(exam);
    return status === 'available' || status === 'overdue';
  });

  const submittedExams = exams.filter(exam => {
    const { status } = getExamStatus(exam);
    return status === 'pending' || status === 'grading';
  });

  const gradedExams = exams.filter(exam => {
    const { status } = getExamStatus(exam);
    return status === 'graded';
  });

  const ExamCard = ({ exam }: { exam: Exam }) => {
    const examStatus = getExamStatus(exam);
    const dueDate = exam.dueDate ? new Date(exam.dueDate) : null;
    const isOverdue = dueDate && dueDate < new Date();

    return (
      <Card className="hover:shadow-lg transition-shadow">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-1 flex-1">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                {exam.title}
              </CardTitle>
              <CardDescription>
                {exam.description || 'No description'}
              </CardDescription>
            </div>
            <Badge variant={examStatus.color as any}>
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
            {examStatus.submission && examStatus.status === 'graded' && (
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
        <CardFooter>
          {examStatus.status === 'available' && (
            <Button
              className="w-full"
              onClick={() => navigate(`/take-exam/${exam.id}`)}
            >
              Start Exam
            </Button>
          )}
          {examStatus.status === 'overdue' && (
            <Button
              variant="outline"
              className="w-full"
              disabled
            >
              <XCircle className="mr-2 h-4 w-4 text-destructive" />
              Overdue
            </Button>
          )}
          {(examStatus.status === 'pending' || examStatus.status === 'grading') && (
            <Button
              variant="outline"
              className="w-full"
              onClick={() => navigate(`/submissions/${examStatus.submission!.id}`)}
            >
              <Clock className="mr-2 h-4 w-4" />
              View Submission
            </Button>
          )}
          {examStatus.status === 'graded' && (
            <Button
              className="w-full"
              onClick={() => navigate(`/submissions/${examStatus.submission!.id}`)}
            >
              <CheckCircle2 className="mr-2 h-4 w-4" />
              View Results
            </Button>
          )}
        </CardFooter>
      </Card>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">My Exams</h1>
        <p className="text-muted-foreground">
          View and submit exams from your enrolled courses
        </p>
      </div>

      <Tabs defaultValue="available" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="available">
            Available ({availableExams.length})
          </TabsTrigger>
          <TabsTrigger value="submitted">
            Submitted ({submittedExams.length})
          </TabsTrigger>
          <TabsTrigger value="graded">
            Graded ({gradedExams.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="available" className="space-y-4 mt-6">
          {availableExams.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FileText className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No exams available</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Check back later for new exams
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {availableExams.map(exam => (
                <ExamCard key={exam.id} exam={exam} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="submitted" className="space-y-4 mt-6">
          {submittedExams.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Clock className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No submitted exams</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {submittedExams.map(exam => (
                <ExamCard key={exam.id} exam={exam} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="graded" className="space-y-4 mt-6">
          {gradedExams.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <CheckCircle2 className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No graded exams yet</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {gradedExams.map(exam => (
                <ExamCard key={exam.id} exam={exam} />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

