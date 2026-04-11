import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { submissionsAPI, examsAPI } from '@/lib/api';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ClipboardList, Eye, Sparkles, Clock, CheckCircle, Loader2, Filter, ThumbsDown } from 'lucide-react';
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
      toast.success('Submission graded successfully.', {
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

  const handleApprove = async (submissionId: string) => {
    try {
      await submissionsAPI.approve(submissionId);
      toast.success('Submission approved!');
      await loadData();
    } catch (error: any) {
      toast.error('Failed to approve: ' + error.message);
    }
  };

  const handleReject = async (submissionId: string) => {
    try {
      await submissionsAPI.reject(submissionId);
      toast.success(
        'Returned for review — the student no longer sees grades. Open the submission to view their work and edit scores.'
      );
      await loadData();
    } catch (error: any) {
      toast.error('Failed to reject: ' + error.message);
    }
  };

  const filteredSubmissions = submissions.filter(sub => {
    if (selectedExam !== 'all' && sub.examId !== selectedExam) return false;
    if (selectedStatus !== 'all' && sub.status !== selectedStatus) return false;
    return true;
  });

  const STATUS_STYLE: Record<string, string> = {
    approved:          'bg-emerald-50 text-emerald-700 border-emerald-200',
    graded:            'bg-blue-50 text-blue-700 border-blue-200',
    awaiting_approval: 'bg-amber-50 text-amber-700 border-amber-200',
    grading:           'bg-purple-50 text-purple-700 border-purple-200',
    pending:           'bg-yellow-50 text-yellow-700 border-yellow-200',
  };

  const STATUS_LABEL: Record<string, string> = {
    approved:          'Released',
    graded:            'Graded',
    awaiting_approval: 'Needs review',
    grading:           'Grading…',
    pending:           'Pending',
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':        return <CheckCircle className="h-3.5 w-3.5" />;
      case 'graded':          return <CheckCircle className="h-3.5 w-3.5" />;
      case 'awaiting_approval': return <Clock className="h-3.5 w-3.5" />;
      case 'grading':         return <Loader2 className="h-3.5 w-3.5 animate-spin" />;
      default:                return <Clock className="h-3.5 w-3.5" />;
    }
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase();
  };

  const pendingCount        = filteredSubmissions.filter(s => s.status === 'pending').length;
  const gradingCount        = filteredSubmissions.filter(s => s.status === 'grading').length;
  const gradedCount         = filteredSubmissions.filter(s => s.status === 'graded').length;
  const awaitingCount       = filteredSubmissions.filter(s => s.status === 'awaiting_approval').length;
  const approvedCount       = filteredSubmissions.filter(s => s.status === 'approved').length;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <>
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Submissions</h1>
          <p className="mt-1 text-sm text-muted-foreground">Open a row to review or adjust grades</p>
        </div>

        {/* Stats */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Card className="border-border/80 shadow-sm">
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Total</CardTitle>
            </CardHeader>
            <CardContent className="pb-4">
              <div className="text-2xl font-bold tabular-nums">{filteredSubmissions.length}</div>
            </CardContent>
          </Card>
          <Card className="border-border/80 shadow-sm">
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Pending</CardTitle>
            </CardHeader>
            <CardContent className="pb-4">
              <div className="text-2xl font-bold tabular-nums text-yellow-600">{pendingCount}</div>
            </CardContent>
          </Card>
          <Card className="border-border/80 shadow-sm">
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Graded</CardTitle>
            </CardHeader>
            <CardContent className="pb-4">
              <div className="text-2xl font-bold tabular-nums text-blue-600">{gradedCount}</div>
            </CardContent>
          </Card>
          <Card className="border-border/80 shadow-sm">
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Review</CardTitle>
            </CardHeader>
            <CardContent className="pb-4">
              <div className="text-2xl font-bold tabular-nums text-amber-600">{awaitingCount}</div>
            </CardContent>
          </Card>
          <Card className="border-border/80 shadow-sm">
            <CardHeader className="pb-2 pt-4">
              <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Released</CardTitle>
            </CardHeader>
            <CardContent className="pb-4">
              <div className="text-2xl font-bold tabular-nums text-emerald-600">{approvedCount}</div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <div className="flex flex-col gap-3 rounded-xl border border-border/80 bg-card/50 p-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2 text-muted-foreground shrink-0">
            <Filter className="h-4 w-4" />
            <span className="text-sm font-medium">Filter</span>
          </div>
          <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row">
            <Select value={selectedExam} onValueChange={setSelectedExam}>
              <SelectTrigger className="bg-background">
                <SelectValue placeholder="Exam" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All exams</SelectItem>
                {exams.map((exam) => (
                  <SelectItem key={exam.id} value={exam.id}>
                    {exam.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={selectedStatus} onValueChange={setSelectedStatus}>
              <SelectTrigger className="bg-background">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="grading">Grading</SelectItem>
                <SelectItem value="graded">Graded (auto)</SelectItem>
                <SelectItem value="awaiting_approval">Awaiting your review</SelectItem>
                <SelectItem value="approved">Released</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Submissions Table */}
        <Card className="border-border/80 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">List</CardTitle>
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
                          <Badge
                            variant="outline"
                            className={`flex items-center gap-1 w-fit text-xs ${STATUS_STYLE[submission.status] ?? ''}`}
                          >
                            {getStatusIcon(submission.status)}
                            {STATUS_LABEL[submission.status] ?? submission.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {submission.totalScore !== null && submission.totalScore !== undefined ? (
                            <div className="flex flex-col gap-0.5 tabular-nums">
                              <span className="text-sm font-semibold">
                                {((submission.totalScore / submission.maxScore) * 100).toFixed(0)}
                                <span className="text-muted-foreground font-normal">%</span>
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {submission.totalScore.toFixed(1)}/{submission.maxScore}
                              </span>
                            </div>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex flex-wrap justify-end gap-1.5">
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-8"
                              onClick={() => navigate(`/submissions/${submission.id}`)}
                            >
                              <Eye className="h-3.5 w-3.5 mr-1" />
                              View
                            </Button>

                            {submission.status === 'pending' && (
                              <Button
                                size="sm"
                                className="h-8"
                                onClick={() => setConfirmDialog({ isOpen: true, submission })}
                                disabled={isGrading}
                              >
                                {isGrading ? (
                                  <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                                ) : (
                                  <Sparkles className="h-3.5 w-3.5 mr-1" />
                                )}
                                {isGrading ? 'Grading…' : 'Auto-grade'}
                              </Button>
                            )}

                            {(submission.status === 'graded' || submission.status === 'awaiting_approval') && (
                              <Button
                                size="sm"
                                className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white"
                                onClick={() => handleApprove(submission.id)}
                              >
                                <CheckCircle className="h-3.5 w-3.5 mr-1" />
                                Release
                              </Button>
                            )}

                            {['graded', 'awaiting_approval', 'approved'].includes(submission.status) && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-8 border-rose-200/90 text-rose-800 hover:bg-rose-50 dark:border-rose-900 dark:text-rose-200 dark:hover:bg-rose-950/50"
                                onClick={() => handleReject(submission.id)}
                              >
                                <ThumbsDown className="h-3.5 w-3.5 mr-1" />
                                Return
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
              Automatic grading
            </AlertDialogTitle>
            <AlertDialogDescription>
              The system will grade this submission using OCR to read the handwritten work
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
              Start grading
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

