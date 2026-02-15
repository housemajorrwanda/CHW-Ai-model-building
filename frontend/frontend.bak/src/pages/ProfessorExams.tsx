import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { examsAPI, submissionsAPI, coursesAPI } from '@/lib/api';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FileText, Eye, EyeOff, Users, CheckCircle, Clock, Plus, Loader2, Edit, ExternalLink } from 'lucide-react';
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

  useEffect(() => {
    loadData();
  }, []);

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

  const getExamSubmissions = (examId: string) => {
    return submissions.filter(s => s.examId === examId);
  };

  const getSubmissionStats = (examId: string) => {
    const examSubs = getExamSubmissions(examId);
    const graded = examSubs.filter(s => s.status === 'graded').length;
    const pending = examSubs.filter(s => s.status === 'pending').length;
    return { total: examSubs.length, graded, pending };
  };

  const filteredExams = selectedCourse === 'all'
    ? exams
    : exams.filter(exam => exam.courseId === selectedCourse);

  const publishedExams = filteredExams.filter(e => e.isPublished);
  const draftExams = filteredExams.filter(e => !e.isPublished);

  const ExamCard = ({ exam }: { exam: Exam }) => {
    const stats = getSubmissionStats(exam.id);
    const course = courses.find(c => c.id === exam.courseId);
    const isPublishing = publishingExamId === exam.id;

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
                {course?.code} - {course?.name}
              </CardDescription>
            </div>
            <Badge variant={exam.isPublished ? 'default' : 'secondary'}>
              {exam.isPublished ? (
                <><Eye className="h-3 w-3 mr-1" /> Published</>
              ) : (
                <><EyeOff className="h-3 w-3 mr-1" /> Draft</>
              )}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground line-clamp-2">
              {exam.description || 'No description'}
            </p>
            
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span>{exam.questions.length} questions</span>
              </div>
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span>{stats.total} submissions</span>
              </div>
            </div>

            {stats.total > 0 && (
              <div className="p-3 bg-muted rounded-lg space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Graded</span>
                  <span className="font-medium text-green-600">{stats.graded}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Pending</span>
                  <span className="font-medium text-yellow-600">{stats.pending}</span>
                </div>
              </div>
            )}

            {exam.dueDate && (
              <div className="text-sm text-muted-foreground">
                Due: {format(new Date(exam.dueDate), 'MMM d, yyyy h:mm a')}
              </div>
            )}
          </div>
        </CardContent>
        <CardFooter className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/exams/${exam.id}`)}
            title="Preview Exam"
          >
            <Eye className="h-4 w-4 mr-2" />
            Preview
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              try {
                const html = await examsAPI.downloadPDF(exam.id);
                const printWindow = window.open('', '_blank');
                if (printWindow) {
                  printWindow.document.write(html);
                  printWindow.document.close();
                  printWindow.onload = () => {
                    printWindow.print();
                  };
                  toast.success('Opening PDF for printing...');
                } else {
                  toast.error('Please allow popups to download PDF');
                }
              } catch (error: any) {
                toast.error('Failed to download PDF: ' + error.message);
              }
            }}
            title="Download/Print PDF"
          >
            <FileText className="h-4 w-4 mr-2" />
            PDF
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/exams/${exam.id}/edit`)}
          >
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          {exam.isPublished ? (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate(`/submissions?exam=${exam.id}`)}
              >
                <Users className="h-4 w-4 mr-2" />
                Submissions ({stats.total})
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setConfirmDialog({ isOpen: true, exam, action: 'unpublish' })}
                disabled={isPublishing}
                title="Unpublish Exam"
              >
                {isPublishing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <EyeOff className="h-4 w-4" />
                )}
              </Button>
            </>
          ) : (
            <Button
              size="sm"
              onClick={() => setConfirmDialog({ isOpen: true, exam, action: 'publish' })}
              disabled={isPublishing}
            >
              {isPublishing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Publishing...
                </>
              ) : (
                <>
                  <Eye className="h-4 w-4 mr-2" />
                  Publish
                </>
              )}
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
    <>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">My Exams</h1>
            <p className="text-muted-foreground">
              Create, publish, and manage your course exams
            </p>
          </div>
          <Button onClick={() => navigate('/exams/new')}>
            <Plus className="h-4 w-4 mr-2" />
            Create Exam
          </Button>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-4">
          <Select value={selectedCourse} onValueChange={setSelectedCourse}>
            <SelectTrigger className="w-[250px]">
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
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Exams
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{filteredExams.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Published
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{publishedExams.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Drafts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">{draftExams.length}</div>
            </CardContent>
          </Card>
        </div>

        {/* Published Exams */}
        {publishedExams.length > 0 && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Published Exams</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {publishedExams.map(exam => (
                <ExamCard key={exam.id} exam={exam} />
              ))}
            </div>
          </div>
        )}

        {/* Draft Exams */}
        {draftExams.length > 0 && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Draft Exams</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {draftExams.map(exam => (
                <ExamCard key={exam.id} exam={exam} />
              ))}
            </div>
          </div>
        )}

        {filteredExams.length === 0 && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <FileText className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">No exams found</p>
              <Button onClick={() => navigate('/exams/new')}>
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Exam
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
    </>
  );
}

