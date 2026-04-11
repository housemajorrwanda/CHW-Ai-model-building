import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { examsAPI, submissionsAPI, coursesAPI } from '@/lib/api';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  FileText,
  Eye,
  EyeOff,
  Users,
  Plus,
  Loader2,
  Edit,
  Trash2,
  Download,
  BookOpenCheck,
  ListChecks,
  ClipboardList,
  Sparkles,
  GraduationCap,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';

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

interface Course {
  id: string;
  name: string;
  code: string;
}

export default function ProfessorExams() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [exams, setExams] = useState<Exam[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [publishingExamId, setPublishingExamId] = useState<string | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{ isOpen: boolean; exam: Exam | null; action: 'publish' | 'unpublish' | null }>({
    isOpen: false,
    exam: null,
    action: null
  });
  const [deleteDialog, setDeleteDialog] = useState<{ isOpen: boolean; exam: Exam | null }>({ isOpen: false, exam: null });
  const [deletingExamId, setDeletingExamId] = useState<string | null>(null);
  const [downloadDialog, setDownloadDialog] = useState<{ isOpen: boolean; exam: Exam | null }>({ isOpen: false, exam: null });
  const [isDownloading, setIsDownloading] = useState(false);
  const [pdfPaper, setPdfPaper] = useState<'a4' | 'letter' | 'legal'>('a4');

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    const courseId = searchParams.get('course');
    if (!courseId || courses.length === 0) return;
    if (courses.some((c) => c.id === courseId)) {
      setSelectedCourse(courseId);
    }
  }, [searchParams, courses]);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [examsData, coursesData, submissionsData] = await Promise.all([
        examsAPI.getAll(),
        coursesAPI.getAll(),
        submissionsAPI.getAll()
      ]);
      setExams(examsData);
      setCourses(coursesData);
      setSubmissions(submissionsData);
    } catch (error: any) {
      toast.error('Failed to load data: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePublishToggle = async () => {
    if (!confirmDialog.exam || !confirmDialog.action) return;

    try {
      setPublishingExamId(confirmDialog.exam.id);
      if (confirmDialog.action === 'publish') {
        await examsAPI.publish(confirmDialog.exam.id);
        toast.success('Exam published successfully! Students can now see and attempt it.');
      } else {
        await examsAPI.unpublish(confirmDialog.exam.id);
        toast.success('Exam unpublished. Students can no longer access it.');
      }
      await loadData();
    } catch (error: any) {
      toast.error(error.message || 'Failed to update exam');
    } finally {
      setPublishingExamId(null);
      setConfirmDialog({ isOpen: false, exam: null, action: null });
    }
  };

  const handleDeleteExam = async () => {
    if (!deleteDialog.exam) return;
    try {
      setDeletingExamId(deleteDialog.exam.id);
      await examsAPI.delete(deleteDialog.exam.id);
      toast.success('Exam deleted');
      setDeleteDialog({ isOpen: false, exam: null });
      await loadData();
    } catch (error: any) {
      toast.error((error as Error).message || 'Failed to delete exam');
    } finally {
      setDeletingExamId(null);
    }
  };

  const handleDownloadPDF = async (includeSolutions: boolean) => {
    if (!downloadDialog.exam) return;
    const exam = downloadDialog.exam;
    setIsDownloading(true);
    setDownloadDialog({ isOpen: false, exam: null });
    try {
      const blob = await examsAPI.downloadPDF(exam.id, includeSolutions, pdfPaper);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const suffix = includeSolutions ? '_with_solutions' : '_questions_only';
      a.download = `${exam.title.replace(/\s+/g, '_')}${suffix}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('PDF downloaded!');
    } catch (error: any) {
      toast.error('Failed to download PDF');
    } finally {
      setIsDownloading(false);
    }
  };

  const getExamSubmissions = (examId: string) => {
    return submissions.filter(s => s.examId === examId);
  };

  const getSubmissionStats = (examId: string) => {
    const examSubs = getExamSubmissions(examId);
    const approved = examSubs.filter((s) => s.status === 'approved').length;
    const awaitingYou = examSubs.filter((s) =>
      ['graded', 'awaiting_approval'].includes(s.status)
    ).length;
    const inProgress = examSubs.filter((s) =>
      ['pending', 'grading'].includes(s.status)
    ).length;
    return { total: examSubs.length, approved, awaitingYou, inProgress };
  };

  const filteredExams = selectedCourse === 'all'
    ? exams
    : exams.filter(exam => exam.courseId === selectedCourse);

  const publishedExams = filteredExams.filter(e => e.isPublished);
  const draftExams = filteredExams.filter(e => !e.isPublished);

  const ExamCard = ({ exam }: { exam: Exam }) => {
    const stats = getSubmissionStats(exam.id);
    const course = courses.find((c) => c.id === exam.courseId);
    const isPublishing = publishingExamId === exam.id;
    const published = exam.isPublished;

    return (
      <Card
        className={cn(
          'group overflow-hidden rounded-2xl border-2 shadow-md transition-all duration-200 hover:shadow-xl',
          published
            ? 'border-violet-200/90 bg-gradient-to-b from-violet-50/40 to-card dark:from-violet-950/20 dark:border-violet-900/50'
            : 'border-amber-200/70 bg-gradient-to-b from-amber-50/30 to-card dark:from-amber-950/15 dark:border-amber-900/40'
        )}
      >
        <div
          className={cn(
            'h-1.5 w-full',
            published ? 'bg-gradient-to-r from-violet-500 to-indigo-500' : 'bg-gradient-to-r from-amber-400 to-orange-400'
          )}
          aria-hidden
        />
        <CardHeader className="pb-3 pt-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1 space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <span className="truncate font-mono text-violet-700 dark:text-violet-300">{course?.code}</span>
                <span className="text-border">·</span>
                <span className="truncate">{course?.name}</span>
              </div>
              <CardTitle className="text-lg font-bold leading-snug sm:text-xl flex items-start gap-2">
                <span
                  className={cn(
                    'mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-white shadow-sm',
                    published ? 'bg-violet-600' : 'bg-amber-600'
                  )}
                >
                  <FileText className="h-4 w-4" />
                </span>
                <span className="min-w-0">{exam.title}</span>
              </CardTitle>
            </div>
            <Badge
              className={cn(
                'shrink-0 border px-2.5 py-1 text-xs font-semibold shadow-sm',
                published
                  ? 'border-violet-300 bg-violet-100 text-violet-900 hover:bg-violet-100 dark:border-violet-700 dark:bg-violet-950 dark:text-violet-100'
                  : 'border-amber-300 bg-amber-100 text-amber-950 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100'
              )}
            >
              {published ? (
                <>
                  <Eye className="h-3.5 w-3.5 mr-1" /> Live
                </>
              ) : (
                <>
                  <EyeOff className="h-3.5 w-3.5 mr-1" /> Draft
                </>
              )}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 pb-4">
          <p className="text-sm leading-relaxed text-foreground/85 line-clamp-3 min-h-[3.75rem]">
            {exam.description || (
              <span className="italic text-muted-foreground">No description — add one when editing.</span>
            )}
          </p>

          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-border/80 bg-background/80 px-2.5 py-1.5 text-sm font-medium shadow-sm">
              <ClipboardList className="h-4 w-4 text-violet-600" />
              {exam.questions.length} questions
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-border/80 bg-background/80 px-2.5 py-1.5 text-sm font-medium shadow-sm">
              <Users className="h-4 w-4 text-indigo-600" />
              {stats.total} submission{stats.total === 1 ? '' : 's'}
            </span>
          </div>

          {stats.total > 0 && (
            <div className="rounded-xl border border-border/70 bg-muted/40 p-3 dark:bg-muted/20">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Submission pipeline
              </p>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-lg bg-emerald-50 py-2 dark:bg-emerald-950/40">
                  <p className="text-lg font-bold tabular-nums text-emerald-800 dark:text-emerald-200">
                    {stats.approved}
                  </p>
                  <p className="text-[0.65rem] font-medium uppercase tracking-wide text-emerald-700/90 dark:text-emerald-300/90">
                    Published
                  </p>
                </div>
                <div className="rounded-lg bg-violet-50 py-2 dark:bg-violet-950/40">
                  <p className="text-lg font-bold tabular-nums text-violet-800 dark:text-violet-200">
                    {stats.awaitingYou}
                  </p>
                  <p className="text-[0.65rem] font-medium uppercase tracking-wide text-violet-700/90 dark:text-violet-300/90">
                    Review
                  </p>
                </div>
                <div className="rounded-lg bg-amber-50 py-2 dark:bg-amber-950/40">
                  <p className="text-lg font-bold tabular-nums text-amber-900 dark:text-amber-200">
                    {stats.inProgress}
                  </p>
                  <p className="text-[0.65rem] font-medium uppercase tracking-wide text-amber-800/90 dark:text-amber-300/90">
                    Active
                  </p>
                </div>
              </div>
            </div>
          )}

          {exam.dueDate && (
            <div className="flex items-center gap-2 rounded-lg border border-dashed border-violet-200/80 bg-violet-50/50 px-3 py-2 text-sm font-medium text-violet-950 dark:border-violet-900 dark:bg-violet-950/30 dark:text-violet-100">
              <span className="text-xs uppercase tracking-wide text-violet-700/80 dark:text-violet-300/80">
                Due
              </span>
              {format(new Date(exam.dueDate), 'MMM d, yyyy · h:mm a')}
            </div>
          )}
        </CardContent>
        <CardFooter className="flex flex-col gap-3 border-t bg-muted/30 pt-4 dark:bg-muted/10">
          {published ? (
            <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
              <Button
                className="h-11 w-full font-semibold shadow-sm bg-violet-600 text-white hover:bg-violet-700"
                onClick={() => navigate(`/submissions?exam=${exam.id}`)}
              >
                <Users className="mr-2 h-4 w-4" />
                Submissions
                {stats.total > 0 && (
                  <Badge variant="secondary" className="ml-2 bg-white/20 text-white hover:bg-white/20">
                    {stats.total}
                  </Badge>
                )}
              </Button>
              <Button
                variant="outline"
                className="h-11 w-full border-violet-300 bg-white font-semibold hover:bg-violet-50 dark:border-violet-700 dark:bg-violet-950/50 dark:hover:bg-violet-900/50"
                onClick={() => navigate(`/exams/${exam.id}/edit`)}
              >
                <Edit className="mr-2 h-4 w-4" />
                Edit exam
              </Button>
            </div>
          ) : (
            <Button
              className="h-11 w-full font-semibold shadow-sm bg-violet-600 text-white hover:bg-violet-700"
              onClick={() => navigate(`/exams/${exam.id}/edit`)}
            >
              <Edit className="mr-2 h-4 w-4" />
              Continue editing
            </Button>
          )}

          <div className="flex w-full flex-wrap items-center justify-between gap-2 border-t border-border/50 pt-3">
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-9 border-violet-200 font-medium"
                disabled={isDownloading}
                onClick={() => setDownloadDialog({ isOpen: true, exam })}
              >
                <Download className="mr-2 h-4 w-4" />
                PDF
              </Button>
              {published ? (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-9 font-medium"
                  title="Unpublish — students lose access"
                  onClick={() => setConfirmDialog({ isOpen: true, exam, action: 'unpublish' })}
                  disabled={isPublishing}
                >
                  {isPublishing ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <EyeOff className="mr-2 h-4 w-4" />
                      Unpublish
                    </>
                  )}
                </Button>
              ) : (
                <Button
                  size="sm"
                  className="h-9 font-semibold bg-emerald-600 text-white hover:bg-emerald-700"
                  onClick={() => setConfirmDialog({ isOpen: true, exam, action: 'publish' })}
                  disabled={isPublishing}
                >
                  {isPublishing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Publishing…
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Publish
                    </>
                  )}
                </Button>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-9 text-destructive hover:bg-destructive/10 hover:text-destructive"
              onClick={() => setDeleteDialog({ isOpen: true, exam })}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        </CardFooter>
      </Card>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px] px-4">
        <div className="flex flex-col items-center gap-4 rounded-2xl border-2 border-violet-200/60 bg-violet-50/50 px-10 py-12 dark:border-violet-900/50 dark:bg-violet-950/30">
          <Loader2 className="h-10 w-10 animate-spin text-violet-600" />
          <p className="text-sm font-medium text-muted-foreground">Loading exams…</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="mx-auto max-w-7xl space-y-8 pb-12">
        <header className="rounded-2xl border border-violet-200/70 bg-gradient-to-br from-violet-50/90 via-white to-indigo-50/40 p-6 shadow-md dark:from-violet-950/40 dark:via-card dark:to-indigo-950/20 dark:border-violet-900/50 sm:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-violet-700 dark:text-violet-400">
                Course assessments
              </p>
              <div className="flex items-center gap-3">
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-600 text-white shadow-md">
                  <GraduationCap className="h-6 w-6" />
                </span>
                <div>
                  <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">My exams</h1>
                  <p className="mt-1 text-muted-foreground text-[1.05rem]">
                    Create, publish, and track submissions in one place
                  </p>
                </div>
              </div>
            </div>
            <Button
              size="lg"
              className="h-12 shrink-0 px-6 font-semibold shadow-md bg-violet-600 hover:bg-violet-700"
              onClick={() => navigate('/exams/new')}
            >
              <Plus className="h-5 w-5 mr-2" />
              Create exam
            </Button>
          </div>
        </header>

        {/* Filter */}
        <div className="flex flex-wrap items-center gap-3">
          <Label htmlFor="course-filter" className="text-sm font-medium text-muted-foreground">
            Filter
          </Label>
          <Select value={selectedCourse} onValueChange={setSelectedCourse}>
            <SelectTrigger id="course-filter" className="w-full max-w-[min(100%,320px)] border-violet-200 bg-background/80 h-11">
              <SelectValue placeholder="Filter by course" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Courses</SelectItem>
              {courses.map(course => (
                <SelectItem key={course.id} value={course.id}>
                  {course.code} - {course.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Stats */}
        <div className="grid gap-4 sm:grid-cols-3">
          <Card className="border-violet-200/60 bg-gradient-to-br from-violet-50/50 to-card shadow-sm dark:border-violet-900/40">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-violet-800 dark:text-violet-200">
                Total exams
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tabular-nums">{filteredExams.length}</div>
            </CardContent>
          </Card>
          <Card className="border-emerald-200/60 bg-gradient-to-br from-emerald-50/50 to-card shadow-sm dark:border-emerald-900/40">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-emerald-800 dark:text-emerald-200">
                Live for students
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tabular-nums text-emerald-700 dark:text-emerald-300">
                {publishedExams.length}
              </div>
            </CardContent>
          </Card>
          <Card className="border-amber-200/60 bg-gradient-to-br from-amber-50/40 to-card shadow-sm dark:border-amber-900/40">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-amber-900 dark:text-amber-200">
                Drafts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold tabular-nums text-amber-800 dark:text-amber-200">
                {draftExams.length}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Published Exams */}
        {publishedExams.length > 0 && (
          <section className="space-y-4" aria-labelledby="published-exams-heading">
            <div className="flex flex-col gap-2 border-b border-violet-200/60 pb-4 dark:border-violet-900/50 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 id="published-exams-heading" className="text-2xl font-bold tracking-tight">
                  Published & live
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Students can see and submit these. Open submissions to review and approve grades.
                </p>
              </div>
              <Badge className="w-fit border-violet-300 bg-violet-100 text-violet-900 dark:border-violet-700 dark:bg-violet-950 dark:text-violet-100">
                {publishedExams.length} exam{publishedExams.length === 1 ? '' : 's'}
              </Badge>
            </div>
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {publishedExams.map((exam) => (
                <ExamCard key={exam.id} exam={exam} />
              ))}
            </div>
          </section>
        )}

        {/* Draft Exams */}
        {draftExams.length > 0 && (
          <section className="space-y-4" aria-labelledby="draft-exams-heading">
            <div className="flex flex-col gap-2 border-b border-amber-200/60 pb-4 dark:border-amber-900/50 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 id="draft-exams-heading" className="text-2xl font-bold tracking-tight">
                  Drafts
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Not visible to students until you publish. Finish editing, then publish when ready.
                </p>
              </div>
              <Badge className="w-fit border-amber-300 bg-amber-100 text-amber-950 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
                {draftExams.length} draft{draftExams.length === 1 ? '' : 's'}
              </Badge>
            </div>
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {draftExams.map((exam) => (
                <ExamCard key={exam.id} exam={exam} />
              ))}
            </div>
          </section>
        )}

        {filteredExams.length === 0 && (
          <Card className="rounded-2xl border-2 border-dashed border-violet-200 bg-violet-50/30 dark:border-violet-900 dark:bg-violet-950/20">
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <span className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-100 dark:bg-violet-950">
                <FileText className="h-8 w-8 text-violet-600" />
              </span>
              <p className="text-lg font-semibold">No exams in this filter</p>
              <p className="mt-2 max-w-md text-muted-foreground">
                Try another course or create a new exam to get started.
              </p>
              <Button
                className="mt-6 font-semibold bg-violet-600 hover:bg-violet-700"
                onClick={() => navigate('/exams/new')}
              >
                <Plus className="h-4 w-4 mr-2" />
                Create exam
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Confirmation Dialog */}
      <AlertDialog open={confirmDialog.isOpen} onOpenChange={(open) => setConfirmDialog({ ...confirmDialog, isOpen: open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmDialog.action === 'publish' ? 'Publish Exam?' : 'Unpublish Exam?'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmDialog.action === 'publish' ? (
                <>
                  Publishing this exam will make it visible to all enrolled students.
                  They will be able to view and submit their work for grading.
                  <br /><br />
                  <strong>Exam: {confirmDialog.exam?.title}</strong>
                </>
              ) : (
                <>
                  Unpublishing this exam will hide it from students. They will no longer
                  be able to access or submit it. Existing submissions will be preserved.
                  <br /><br />
                  <strong>Exam: {confirmDialog.exam?.title}</strong>
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handlePublishToggle}>
              {confirmDialog.action === 'publish' ? 'Publish' : 'Unpublish'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Exam Dialog */}
      <AlertDialog open={deleteDialog.isOpen} onOpenChange={(open) => !deletingExamId && setDeleteDialog({ isOpen: open, exam: open ? deleteDialog.exam : null })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete exam?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete <strong>{deleteDialog.exam?.title}</strong> and all its questions.
              All submissions for this exam will also be removed. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={!!deletingExamId}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteExam}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={!!deletingExamId}
            >
              {deletingExamId ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Download PDF Dialog */}
      <Dialog open={downloadDialog.isOpen} onOpenChange={(open) => setDownloadDialog({ isOpen: open, exam: open ? downloadDialog.exam : null })}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Download className="h-5 w-5" />
              Download PDF — {downloadDialog.exam?.title}
            </DialogTitle>
            <DialogDescription>
              Choose paper size and what to include in the downloaded PDF.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2 pt-2">
            <Label htmlFor="pdf-paper-exams" className="text-xs text-muted-foreground">
              Paper size
            </Label>
            <Select value={pdfPaper} onValueChange={(v) => setPdfPaper(v as 'a4' | 'letter' | 'legal')}>
              <SelectTrigger id="pdf-paper-exams" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="a4">A4 (210 × 297 mm)</SelectItem>
                <SelectItem value="letter">US Letter (8.5 × 11 in)</SelectItem>
                <SelectItem value="legal">US Legal (8.5 × 14 in)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-1 gap-3 pt-2">
            <button
              onClick={() => handleDownloadPDF(false)}
              className="flex items-start gap-4 rounded-lg border p-4 text-left hover:bg-muted/50 transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <ListChecks className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-sm">Questions only</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Export the exam questions and answer spaces — suitable for printing and distributing to students.
                </p>
              </div>
            </button>

            <button
              onClick={() => handleDownloadPDF(true)}
              className="flex items-start gap-4 rounded-lg border p-4 text-left hover:bg-muted/50 transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-green-100 text-green-700">
                <BookOpenCheck className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-sm">Questions + Golden Answers</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Include the reference solution steps and final answers — suitable for your own records or marking guides.
                </p>
              </div>
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

