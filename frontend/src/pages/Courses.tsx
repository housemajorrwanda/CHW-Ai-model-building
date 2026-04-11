import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { coursesAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Plus,
  Search,
  Users,
  FileText,
  Loader2,
  BookOpen,
  UserCheck,
  UserX,
  Clock,
  ChevronRight,
  GraduationCap,
} from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

interface Course {
  id: string;
  name: string;
  code: string;
  description: string;
  level: string;
  professorName: string;
  enrolledStudents: any[];
  pendingEnrollments: any[];
  examCount: number;
  topics: any[];
}

export default function Courses() {
  const navigate = useNavigate();
  const [courses, setCourses] = useState<Course[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [managingCourse, setManagingCourse] = useState<Course | null>(null);

  useEffect(() => {
    loadCourses();
  }, []);

  const loadCourses = async () => {
    try {
      setIsLoading(true);
      const data = await coursesAPI.getAll();
      setCourses(data);
    } catch (error: any) {
      toast.error('Failed to load courses: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproveEnrollment = async (courseId: string, enrollmentId: string) => {
    try {
      await coursesAPI.approveEnrollment(courseId, enrollmentId);
      toast.success('Student enrollment approved!');
      await loadCourses();
      // Refresh the managing dialog
      if (managingCourse?.id === courseId) {
        const updatedCourse = courses.find(c => c.id === courseId);
        if (updatedCourse) setManagingCourse(updatedCourse);
      }
    } catch (error: any) {
      toast.error('Failed to approve enrollment: ' + error.message);
    }
  };

  const handleRejectEnrollment = async (courseId: string, enrollmentId: string) => {
    try {
      await coursesAPI.rejectEnrollment(courseId, enrollmentId);
      toast.success('Student enrollment rejected');
      await loadCourses();
      // Refresh the managing dialog
      if (managingCourse?.id === courseId) {
        const updatedCourse = courses.find(c => c.id === courseId);
        if (updatedCourse) setManagingCourse(updatedCourse);
      }
    } catch (error: any) {
      toast.error('Failed to reject enrollment: ' + error.message);
    }
  };

  const handleRemoveStudent = async (courseId: string, enrollmentId: string) => {
    try {
      await coursesAPI.removeStudent(courseId, enrollmentId);
      toast.success('Student removed from course');
      await loadCourses();
      // Refresh the managing dialog
      if (managingCourse?.id === courseId) {
        const updatedCourse = courses.find(c => c.id === courseId);
        if (updatedCourse) setManagingCourse(updatedCourse);
      }
    } catch (error: any) {
      toast.error('Failed to remove student: ' + error.message);
    }
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase();
  };

  const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

  const filteredCourses = courses.filter(
    (course) =>
      course.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      course.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <>
      <div className="mx-auto max-w-7xl space-y-8 pb-8">
        {/* Header */}
        <header
          className={cn(
            'rounded-2xl border border-violet-200/70 bg-gradient-to-br from-violet-50/90 via-white to-stone-50/40 p-6 shadow-sm',
            'dark:border-violet-900/45 dark:from-violet-950/35 dark:via-card dark:to-stone-950/25 sm:p-8'
          )}
        >
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-violet-700 dark:text-violet-400">
                Instructor
              </p>
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white shadow-sm">
                  <GraduationCap className="h-5 w-5" />
                </span>
                <div>
                  <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">My courses</h1>
                  <p className="mt-1 max-w-xl text-[1.05rem] leading-relaxed text-muted-foreground">
                    Open a course for exams, topics, and enrollment. Use search to find a course by name or code.
                  </p>
                </div>
              </div>
            </div>
            <Button
              size="lg"
              className="shrink-0 shadow-sm"
              onClick={() => navigate('/courses/new')}
            >
              <Plus className="h-4 w-4 mr-2" />
              Create course
            </Button>
          </div>

          <div className="relative mt-6 max-w-lg">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by name or code…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-11 border-violet-100 bg-white/80 pl-10 shadow-inner dark:border-violet-900/40 dark:bg-background/80"
            />
          </div>
        </header>

        {/* Courses Grid */}
        {filteredCourses.length === 0 ? (
          <Card className="overflow-hidden rounded-2xl border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-16">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
                <BookOpen className="h-7 w-7 text-muted-foreground" />
              </div>
              {courses.length === 0 ? (
                <>
                  <p className="text-lg font-medium">No courses yet</p>
                  <p className="mt-1 mb-6 max-w-sm text-center text-sm text-muted-foreground">
                    Create your first course to add exams and invite students.
                  </p>
                </>
              ) : (
                <>
                  <p className="text-lg font-medium">No courses match your search</p>
                  <p className="mt-1 mb-6 max-w-sm text-center text-sm text-muted-foreground">
                    Try another name or code, or clear the search box.
                  </p>
                </>
              )}
              <Button onClick={() => navigate('/courses/new')}>
                <Plus className="h-4 w-4 mr-2" />
                Create course
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {filteredCourses.map((course) => {
              const nStudents = course.enrolledStudents.length;
              const nExams = course.examCount;
              const nPending = course.pendingEnrollments.length;
              return (
                <Card
                  key={course.id}
                  className={cn(
                    'group relative flex flex-col overflow-hidden rounded-2xl border border-border/80 bg-card shadow-sm',
                    'transition-all duration-200 hover:border-violet-300/70 hover:shadow-md',
                    'dark:hover:border-violet-800/50'
                  )}
                >
                  <div
                    className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-violet-500 via-violet-400 to-indigo-400 opacity-90"
                    aria-hidden
                  />
                  <CardHeader className="space-y-3 pb-2 pt-5">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        variant="secondary"
                        className="font-mono text-xs font-semibold tracking-wide"
                      >
                        {course.code}
                      </Badge>
                      <Badge variant="outline" className="capitalize text-xs font-normal">
                        {course.level.replace('_', ' ')}
                      </Badge>
                    </div>
                    <div>
                      <CardTitle className="text-xl font-semibold leading-snug tracking-tight">
                        <Link
                          to={`/courses/${course.id}`}
                          className="text-foreground transition-colors hover:text-violet-700 dark:hover:text-violet-300"
                        >
                          {course.name}
                        </Link>
                      </CardTitle>
                      {course.description?.trim() ? (
                        <CardDescription className="mt-2 line-clamp-2 text-pretty">
                          {course.description}
                        </CardDescription>
                      ) : (
                        <p className="mt-2 text-sm italic text-muted-foreground/80">No description</p>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="pb-3 pt-0">
                    <div className="flex flex-wrap gap-2">
                      <div
                        className="inline-flex items-center gap-1.5 rounded-full bg-muted/70 px-2.5 py-1 text-xs tabular-nums text-muted-foreground"
                        title={`${nStudents} enrolled`}
                      >
                        <Users className="h-3.5 w-3.5 shrink-0 opacity-70" />
                        <span>
                          {nStudents} {plural(nStudents, 'student', 'students')}
                        </span>
                      </div>
                      <div
                        className="inline-flex items-center gap-1.5 rounded-full bg-muted/70 px-2.5 py-1 text-xs tabular-nums text-muted-foreground"
                        title={`${nExams} exam${nExams !== 1 ? 's' : ''}`}
                      >
                        <FileText className="h-3.5 w-3.5 shrink-0 opacity-70" />
                        <span>
                          {nExams === 0 ? (
                            <span className="text-muted-foreground/90">No exams yet</span>
                          ) : (
                            <>
                              {nExams} {plural(nExams, 'exam', 'exams')}
                            </>
                          )}
                        </span>
                      </div>
                      {nPending > 0 && (
                        <div className="inline-flex items-center gap-1.5 rounded-full border border-amber-200/80 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-200">
                          <Clock className="h-3.5 w-3.5 shrink-0 opacity-80" />
                          {nPending} pending {plural(nPending, 'request', 'requests')}
                        </div>
                      )}
                    </div>
                  </CardContent>
                  <CardFooter className="mt-auto flex flex-col gap-3 border-t border-border/60 bg-muted/15 px-4 py-4">
                    <Button className="w-full shadow-sm" size="default" asChild>
                      <Link to={`/courses/${course.id}`}>
                        Open course
                        <ChevronRight className="ml-1 h-4 w-4 opacity-80" />
                      </Link>
                    </Button>
                    <div className="flex items-center justify-center gap-2">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            className="h-9 w-9 shrink-0 border-border/80"
                            onClick={() => navigate(`/exams?course=${course.id}`)}
                            aria-label="View exams for this course"
                          >
                            <FileText className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent side="bottom">Exams for this course</TooltipContent>
                      </Tooltip>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            className="h-9 w-9 shrink-0 border-border/80"
                            onClick={() => setManagingCourse(course)}
                            aria-label="Manage students"
                          >
                            <Users className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent side="bottom">Enrollments & students</TooltipContent>
                      </Tooltip>
                    </div>
                  </CardFooter>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Manage Students Dialog */}
      <Dialog open={!!managingCourse} onOpenChange={(open) => !open && setManagingCourse(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Manage Students - {managingCourse?.name}</DialogTitle>
            <DialogDescription>
              Review enrollment requests and manage enrolled students
            </DialogDescription>
          </DialogHeader>

          <Tabs defaultValue="enrolled" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="enrolled">
                Enrolled ({managingCourse?.enrolledStudents.length || 0})
              </TabsTrigger>
              <TabsTrigger value="pending">
                Pending ({managingCourse?.pendingEnrollments.length || 0})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="enrolled" className="space-y-3 mt-4">
              {managingCourse?.enrolledStudents.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No enrolled students yet
                </div>
              ) : (
                managingCourse?.enrolledStudents.map((student) => (
                  <div
                    key={student.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <Avatar>
                        <AvatarFallback className="text-sm">
                          {getInitials(student.studentName)}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="font-medium">{student.studentName}</p>
                        <p className="text-sm text-muted-foreground">{student.studentEmail}</p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => managingCourse && handleRemoveStudent(managingCourse.id, student.id)}
                    >
                      <UserX className="h-4 w-4 mr-2" />
                      Remove
                    </Button>
                  </div>
                ))
              )}
            </TabsContent>

            <TabsContent value="pending" className="space-y-3 mt-4">
              {managingCourse?.pendingEnrollments.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No pending enrollment requests
                </div>
              ) : (
                managingCourse?.pendingEnrollments.map((enrollment) => (
                  <div
                    key={enrollment.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <Avatar>
                        <AvatarFallback className="text-sm">
                          {getInitials(enrollment.studentName)}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <p className="font-medium">{enrollment.studentName}</p>
                        <p className="text-sm text-muted-foreground">{enrollment.studentEmail}</p>
                        <p className="text-xs text-muted-foreground">
                          Requested: {new Date(enrollment.requestedAt).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => managingCourse && handleApproveEnrollment(managingCourse.id, enrollment.id)}
                      >
                        <UserCheck className="h-4 w-4 mr-2" />
                        Approve
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => managingCourse && handleRejectEnrollment(managingCourse.id, enrollment.id)}
                      >
                        <UserX className="h-4 w-4 mr-2" />
                        Reject
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>
    </>
  );
}