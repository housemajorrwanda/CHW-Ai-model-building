import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { submissionsAPI, examsAPI } from '@/lib/api';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ClipboardList, Eye, Sparkles, Clock, CheckCircle, Loader2, AlertCircle, Filter } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface Submission {
  id: string;
  examId: string;
  studentId: string;
  studentName: string;
  submittedAt: string;
  status: string;
  totalScore: number | null;
  maxScore: number;
}

export default function ProfessorSubmissions() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExam, setSelectedExam] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [gradingSubmissionId, setGradingSubmissionId] = useState<string | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{ isOpen: boolean; submission: Submission | null }>({
    isOpen: false,
    submission: null
  });

  useEffect(() => {
    const examParam = searchParams.get('exam');
    if (examParam) {
      setSelectedExam(examParam);
    }
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [submissionsData, examsData] = await Promise.all([
        submissionsAPI.getAll(),
        examsAPI.getAll()
      ]);
      setSubmissions(submissionsData);
      setExams(examsData);
    } catch (error: any) {
      toast.error('Failed to load submissions: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGrade = async () => {
    if (!confirmDialog.submission) return;

    try {
      setGradingSubmissionId(confirmDialog.submission.id);
      await submissionsAPI.grade(confirmDialog.submission.id);
      toast.success('Submission graded successfully with AI!', {
        description: 'The student will be notified of their results.'
      });
      await loadData();
    } catch (error: any) {
      toast.error('Failed to grade submission: ' + error.message);
    } finally {
      setGradingSubmissionId(null);
      setConfirmDialog({ isOpen: false, submission: null });
    }
  };

  const filteredSubmissions = submissions.filter(sub => {
    if (selectedExam !== 'all' && sub.examId !== selectedExam) return false;
    if (selectedStatus !== 'all' && sub.status !== selectedStatus) return false;
    return true;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'graded':
        return 'default';
      case 'grading':
        return 'secondary';
      case 'pending':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'graded':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'grading':
        return <Loader2 className="h-4 w-4 animate-spin text-yellow-600" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-600" />;
      default:
        return <AlertCircle className="h-4 w-4" />;
    }
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase();
  };

  const pendingCount = filteredSubmissions.filter(s => s.status === 'pending').length;
  const gradingCount = filteredSubmissions.filter(s => s.status === 'grading').length;
  const gradedCount = filteredSubmissions.filter(s => s.status === 'graded').length;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Student Submissions</h1>
          <p className="text-muted-foreground">
            Review and grade student submissions with AI assistance
          </p>
        </div>

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Submissions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{filteredSubmissions.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Pending Review
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">{pendingCount}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Grading
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{gradingCount}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Graded
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{gradedCount}</div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-muted-foreground" />
              <CardTitle className="text-base">Filters</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="flex gap-4">
            <div className="flex-1">
              <Select value={selectedExam} onValueChange={setSelectedExam}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by exam" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Exams</SelectItem>
                  {exams.map(exam => (
                    <SelectItem key={exam.id} value={exam.id}>
                      {exam.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex-1">
              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="grading">Grading</SelectItem>
                  <SelectItem value="graded">Graded</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Submissions Table */}
        <Card>
          <CardHeader>
            <CardTitle>Submissions</CardTitle>
            <CardDescription>
              Click on a submission to view details or grade with AI
            </CardDescription>
          </CardHeader>
          <CardContent>
            {filteredSubmissions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <ClipboardList className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No submissions found</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Student</TableHead>
                    <TableHead>Exam</TableHead>
                    <TableHead>Submitted</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredSubmissions.map((submission) => {
                    const exam = exams.find(e => e.id === submission.examId);
                    const isGrading = gradingSubmissionId === submission.id;
                    
                    return (
                      <TableRow key={submission.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Avatar className="h-8 w-8">
                              <AvatarFallback className="text-xs">
                                {getInitials(submission.studentName)}
                              </AvatarFallback>
                            </Avatar>
                            <span className="font-medium">{submission.studentName}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm">{exam?.title || 'Unknown'}</span>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-muted-foreground">
                            {format(new Date(submission.submittedAt), 'MMM d, yyyy h:mm a')}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getStatusColor(submission.status) as any} className="flex items-center gap-1 w-fit">
                            {getStatusIcon(submission.status)}
                            {submission.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {submission.status === 'graded' && submission.totalScore !== null ? (
                            <span className="font-medium">
                              {submission.totalScore.toFixed(1)} / {submission.maxScore}
                              <span className="text-xs text-muted-foreground ml-1">
                                ({((submission.totalScore / submission.maxScore) * 100).toFixed(0)}%)
                              </span>
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => navigate(`/submissions/${submission.id}`)}
                            >
                              <Eye className="h-4 w-4 mr-2" />
                              View
                            </Button>
                            {submission.status === 'pending' && (
                              <Button
                                size="sm"
                                onClick={() => setConfirmDialog({ isOpen: true, submission })}
                                disabled={isGrading}
                              >
                                {isGrading ? (
                                  <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Grading...
                                  </>
                                ) : (
                                  <>
                                    <Sparkles className="h-4 w-4 mr-2" />
                                    Grade with AI
                                  </>
                                )}
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Confirmation Dialog */}
      <AlertDialog open={confirmDialog.isOpen} onOpenChange={(open) => setConfirmDialog({ ...confirmDialog, isOpen: open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Grade with AI
            </AlertDialogTitle>
            <AlertDialogDescription>
              The AI will automatically grade this submission using OCR to read the handwritten work
              and compare it against the gold solution steps.
              <br /><br />
              <strong>Student:</strong> {confirmDialog.submission?.studentName}
              <br />
              <strong>Submitted:</strong> {confirmDialog.submission && format(new Date(confirmDialog.submission.submittedAt), 'MMM d, yyyy h:mm a')}
              <br /><br />
              This process may take a few moments. The student will be notified once grading is complete.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleGrade}>
              <Sparkles className="h-4 w-4 mr-2" />
              Start AI Grading
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

