import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ArrowLeft,
  BookOpen,
  Users,
  FileText,
  CheckCircle,
  XCircle,
  Trash2,
  UserPlus,
  Award,
  Clock,
  Eye,
  Calendar,
  Megaphone,
} from 'lucide-react';
import { toast } from 'sonner';
import { Separator } from '@/components/ui/separator';
import { format } from 'date-fns';

function CourseExamsList({ courseId }: { courseId: string }) {
  const { data: exams, isLoading } = useQuery({
    queryKey: ['exams', courseId],
    queryFn: () => api.exams.getAll(courseId),
    enabled: !!courseId,
  });

  if (isLoading) {
    return <p className="text-center text-muted-foreground py-8">Loading exams...</p>;
  }

  if (!exams || exams.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground mb-4">No exams created yet</p>
        <Button asChild>
          <Link to={`/exams/new?courseId=${courseId}`}>
            <FileText className="h-4 w-4 mr-2" />
            Create First Exam
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {exams.map((exam: any) => (
        <div
          key={exam.id}
          className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
        >
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-1">
              <h4 className="font-semibold">{exam.title}</h4>
              {exam.isPublished ? (
                <Badge variant="default">Published</Badge>
              ) : (
                <Badge variant="secondary">Draft</Badge>
              )}
            </div>
            {exam.description && (
              <p className="text-sm text-muted-foreground mb-2">{exam.description}</p>
            )}
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>{exam.totalPoints} points</span>
              {exam.dueDate && (
                <span>
                  <Calendar className="h-3 w-3 inline mr-1" />
                  Due: {format(new Date(exam.dueDate), 'MMM d, yyyy h:mm a')}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link to={`/submissions?exam=${exam.id}`}>
                <Eye className="h-4 w-4 mr-2" />
                Submissions
              </Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to={`/exams/${exam.id}/edit`}>
                <FileText className="h-4 w-4 mr-2" />
                Edit
              </Link>
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function CourseDetail() {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Fetch course details
  const { data: course, isLoading } = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => api.courses.getById(courseId!),
    enabled: !!courseId,
  });

  // Approve enrollment mutation
  const approveMutation = useMutation({
    mutationFn: ({ enrollmentId }: { enrollmentId: string }) =>
      api.courses.approveEnrollment(courseId!, enrollmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', courseId] });
      toast.success('Student approved!');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to approve student');
    },
  });

  // Reject enrollment mutation
  const rejectMutation = useMutation({
    mutationFn: ({ enrollmentId }: { enrollmentId: string }) =>
      api.courses.rejectEnrollment(courseId!, enrollmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', courseId] });
      toast.success('Student rejected');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to reject student');
    },
  });

  // Remove student mutation
  const removeMutation = useMutation({
    mutationFn: ({ enrollmentId }: { enrollmentId: string }) =>
      api.courses.removeStudent(courseId!, enrollmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['course', courseId] });
      toast.success('Student removed from course');
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to remove student');
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p>Loading course...</p>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <p className="text-muted-foreground mb-4">Course not found</p>
        <Button onClick={() => navigate('/courses')}>Back to Courses</Button>
      </div>
    );
  }

  const levelColors: Record<string, string> = {
    beginner: 'bg-green-100 text-green-800',
    intermediate: 'bg-blue-100 text-blue-800',
    advanced: 'bg-purple-100 text-purple-800',
    all_levels: 'bg-gray-100 text-gray-800',
  };

  return (
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/courses')}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold tracking-tight">{course.name}</h1>
                <Badge className={levelColors[course.level]}>
                  {course.level.replace('_', ' ').toUpperCase()}
                </Badge>
              </div>
              <p className="text-muted-foreground">
                <span className="font-mono font-semibold">{course.code}</span> • Professor:{' '}
                {course.professorName}
              </p>
              {course.description && (
                <p className="text-muted-foreground mt-2">{course.description}</p>
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" asChild className="rounded-xl">
              <Link to={`/courses/${courseId}/announcements`}>
                <Megaphone className="h-4 w-4 mr-2" />
                Announcements
              </Link>
            </Button>
            <Button onClick={() => navigate(`/exams/new?courseId=${courseId}`)} className="rounded-xl">
              <FileText className="h-4 w-4 mr-2" />
              Create Exam
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Users className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{course.enrolledStudents.length}</p>
                  <p className="text-xs text-muted-foreground">Enrolled Students</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 rounded-lg">
                  <Clock className="h-5 w-5 text-orange-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{course.pendingEnrollments.length}</p>
                  <p className="text-xs text-muted-foreground">Pending Requests</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <FileText className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{course.examCount}</p>
                  <p className="text-xs text-muted-foreground">Exams</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Award className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{course.submissionCount}</p>
                  <p className="text-xs text-muted-foreground">Submissions</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="exams">
              Exams ({course.examCount || 0})
            </TabsTrigger>
            <TabsTrigger value="students">
              Students ({course.enrolledStudents.length})
            </TabsTrigger>
            <TabsTrigger value="pending">
              Pending ({course.pendingEnrollments.length})
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Course Topics</CardTitle>
                <CardDescription>
                  Topics and subtopics covered in this course
                </CardDescription>
              </CardHeader>
              <CardContent>
                {course.topics.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">
                    No topics added yet
                  </p>
                ) : (
                  <div className="space-y-4">
                    {course.topics.map((topic, idx) => (
                      <div key={topic.id} className="border rounded-lg p-4">
                        <div className="flex items-start gap-3 mb-2">
                          <Badge variant="outline">{idx + 1}</Badge>
                          <div className="flex-1">
                            <h4 className="font-semibold">{topic.name}</h4>
                            {topic.description && (
                              <p className="text-sm text-muted-foreground mt-1">
                                {topic.description}
                              </p>
                            )}
                          </div>
                        </div>
                        {topic.subtopics.length > 0 && (
                          <div className="ml-10 mt-3 space-y-2">
                            {topic.subtopics.map((sub, subIdx) => (
                              <div
                                key={sub.id}
                                className="flex items-start gap-2 text-sm"
                              >
                                <span className="text-muted-foreground">
                                  {idx + 1}.{subIdx + 1}
                                </span>
                                <div>
                                  <span className="font-medium">{sub.name}</span>
                                  {sub.description && (
                                    <span className="text-muted-foreground ml-2">
                                      - {sub.description}
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Exams Tab */}
          <TabsContent value="exams" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Course Exams</CardTitle>
                <CardDescription>
                  All exams for this course
                </CardDescription>
              </CardHeader>
              <CardContent>
                <CourseExamsList courseId={courseId!} />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Students Tab */}
          <TabsContent value="students" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Enrolled Students</CardTitle>
                <CardDescription>
                  Students currently enrolled in this course
                </CardDescription>
              </CardHeader>
              <CardContent>
                {course.enrolledStudents.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">
                    No students enrolled yet
                  </p>
                ) : (
                  <div className="space-y-2">
                    {course.enrolledStudents.map((enrollment) => (
                      <div
                        key={enrollment.id}
                        className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                            <span className="text-sm font-semibold">
                              {enrollment.studentName.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div>
                            <p className="font-medium">{enrollment.studentName}</p>
                            <p className="text-sm text-muted-foreground">
                              {enrollment.studentEmail}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary">
                            Enrolled{' '}
                            {new Date(enrollment.enrolledAt!).toLocaleDateString()}
                          </Badge>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              if (
                                confirm(
                                  `Remove ${enrollment.studentName} from this course?`
                                )
                              ) {
                                removeMutation.mutate({
                                  enrollmentId: enrollment.id,
                                });
                              }
                            }}
                            className="text-destructive hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Pending Tab */}
          <TabsContent value="pending" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Pending Enrollment Requests</CardTitle>
                <CardDescription>
                  Students waiting for approval to join this course
                </CardDescription>
              </CardHeader>
              <CardContent>
                {course.pendingEnrollments.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">
                    No pending requests
                  </p>
                ) : (
                  <div className="space-y-2">
                    {course.pendingEnrollments.map((enrollment) => (
                      <div
                        key={enrollment.id}
                        className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-full bg-orange-100 flex items-center justify-center">
                            <UserPlus className="h-5 w-5 text-orange-600" />
                          </div>
                          <div>
                            <p className="font-medium">{enrollment.studentName}</p>
                            <p className="text-sm text-muted-foreground">
                              {enrollment.studentEmail}
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">
                              Requested{' '}
                              {new Date(enrollment.requestedAt).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="default"
                            size="sm"
                            onClick={() =>
                              approveMutation.mutate({ enrollmentId: enrollment.id })
                            }
                            disabled={approveMutation.isPending}
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Approve
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              rejectMutation.mutate({ enrollmentId: enrollment.id })
                            }
                            disabled={rejectMutation.isPending}
                            className="text-destructive hover:text-destructive"
                          >
                            <XCircle className="h-4 w-4 mr-1" />
                            Reject
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
  );
}

