import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { coursesAPI } from '@/lib/api';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Link } from 'react-router-dom';
import { BookOpen, GraduationCap, Search, CheckCircle2, Clock, Loader2, Megaphone } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

const courseCardShell =
  'relative overflow-hidden rounded-2xl border border-border/70 bg-card shadow-sm transition-all hover:border-border hover:shadow-md dark:bg-card border-l-4 border-l-sky-500 dark:border-l-sky-400';

const tabListClass =
  'grid h-auto w-full max-w-xl grid-cols-3 gap-0 rounded-none border-0 border-b border-border/70 bg-transparent p-0 dark:border-border/50';
const tabTriggerClass =
  'rounded-none border-b-2 border-transparent py-3 text-sm font-medium text-muted-foreground shadow-none transition-colors data-[state=active]:border-sky-600 data-[state=active]:bg-transparent data-[state=active]:text-sky-900 data-[state=active]:shadow-none dark:data-[state=active]:border-sky-400 dark:data-[state=active]:text-sky-100';

function formatCourseTitle(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

function isPlaceholderDescription(d: string | undefined) {
  const t = d?.trim() ?? '';
  return !t || /^test$/i.test(t);
}

interface Course {
  id: string;
  name: string;
  code: string;
  description: string;
  level: string;
  professorName: string;
  professorId: string;
  enrolledStudents: any[];
  pendingEnrollments: any[];
  examCount: number;
  topics: any[];
}

export default function BrowseCourses() {
  const { user } = useAuth();
  const [allCourses, setAllCourses] = useState<Course[]>([]);
  const [enrolledCourses, setEnrolledCourses] = useState<Course[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [enrollingCourseId, setEnrollingCourseId] = useState<string | null>(null);

  useEffect(() => {
    loadCourses();
  }, []);

  const loadCourses = async () => {
    try {
      setIsLoading(true);
      const [all, enrolled] = await Promise.all([
        coursesAPI.getAll(),
        user?.role === 'student' ? coursesAPI.getEnrolled() : Promise.resolve([])
      ]);
      setAllCourses(all);
      setEnrolledCourses(enrolled);
    } catch (error: any) {
      toast.error('Failed to load courses: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEnroll = async (courseId: string) => {
    try {
      setEnrollingCourseId(courseId);
      await coursesAPI.requestEnrollment(courseId);
      toast.success('Enrollment request submitted! Waiting for professor approval.');
      await loadCourses();
    } catch (error: any) {
      toast.error(error.message || 'Failed to enroll');
    } finally {
      setEnrollingCourseId(null);
    }
  };

  const getEnrollmentStatus = (course: Course) => {
    if (!user) return null;
    
    const isEnrolled = enrolledCourses.some(c => c.id === course.id);
    if (isEnrolled) return 'enrolled';
    
    const isPending = course.pendingEnrollments.some(e => e.studentId === user.id);
    if (isPending) return 'pending';
    
    return null;
  };

  const filteredCourses = allCourses.filter(course =>
    course.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    course.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
    course.professorName.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const availableCourses = filteredCourses.filter(course => {
    const status = getEnrollmentStatus(course);
    return status === null;
  });

  const CourseCard = ({ course }: { course: Course }) => {
    const status = getEnrollmentStatus(course);
    const isEnrolling = enrollingCourseId === course.id;

    return (
      <Card className={courseCardShell}>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="rounded-full border-sky-200/80 bg-sky-50/80 text-xs font-medium text-sky-900 dark:border-sky-900/60 dark:bg-sky-950/40 dark:text-sky-100">
                  Course
                </Badge>
                <span className="font-mono text-[11px] text-muted-foreground tabular-nums">{course.code}</span>
              </div>
              <CardTitle className="text-lg font-semibold leading-snug">
                <span className="line-clamp-2">{formatCourseTitle(course.name)}</span>
              </CardTitle>
              <CardDescription className="flex items-center gap-2">
                <GraduationCap className="h-4 w-4" />
                {course.professorName}
              </CardDescription>
            </div>
            <Badge variant="outline" className="capitalize">
              {course.level.replace('_', ' ')}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {!isPlaceholderDescription(course.description) && (
              <p className="text-sm text-muted-foreground line-clamp-2">{course.description}</p>
            )}

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
              <span>
                {course.examCount} {course.examCount === 1 ? 'exam' : 'exams'}
              </span>
              <span>
                {course.enrolledStudents.length}{' '}
                {course.enrolledStudents.length === 1 ? 'student' : 'students'}
              </span>
            </div>

            {course.topics.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {course.topics.slice(0, 3).map((topic) => (
                  <Badge key={topic.id} variant="secondary" className="text-xs">
                    {topic.name}
                  </Badge>
                ))}
                {course.topics.length > 3 && (
                  <Badge variant="secondary" className="text-xs">
                    +{course.topics.length - 3} more
                  </Badge>
                )}
              </div>
            )}
          </div>
        </CardContent>
        <CardFooter className="border-t border-border/50 bg-muted/20 pt-4 dark:border-border/40">
          {status === 'enrolled' && (
            <div className="flex w-full flex-col gap-2 sm:flex-row">
              <Button variant="secondary" size="sm" className="flex-1 rounded-xl" disabled>
                <CheckCircle2 className="mr-2 h-4 w-4 text-emerald-600" />
                Enrolled
              </Button>
              <Button size="sm" className="flex-1 rounded-xl shadow-sm" asChild>
                <Link to={`/courses/${course.id}/announcements`}>
                  <Megaphone className="mr-2 h-4 w-4" />
                  Announcements
                </Link>
              </Button>
            </div>
          )}
          {status === 'pending' && (
            <Button variant="outline" size="sm" className="w-full rounded-xl" disabled>
              <Clock className="mr-2 h-4 w-4 text-amber-600" />
              Pending
            </Button>
          )}
          {status === null && (
            <Button
              size="sm"
              className="w-full rounded-xl"
              onClick={() => handleEnroll(course.id)}
              disabled={isEnrolling}
            >
              {isEnrolling ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Sending…
                </>
              ) : (
                'Request access'
              )}
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
          'rounded-2xl border border-sky-200/60 bg-gradient-to-br from-sky-50/85 via-white to-cyan-50/30 p-6 shadow-sm dark:from-sky-950/25 dark:via-card dark:to-cyan-950/15 dark:border-sky-900/45 sm:p-8'
        )}
      >
        <p className="text-xs font-semibold uppercase tracking-wider text-sky-800 dark:text-sky-300">Courses</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Browse courses</h1>
        <p className="mt-2 max-w-2xl text-[1.05rem] leading-relaxed text-muted-foreground">
          Search by name, code, or instructor—then request access or review courses you already joined.
        </p>
      </header>

      <Card className="overflow-hidden rounded-2xl border border-border/80 shadow-sm dark:border-border/60">
        <CardHeader className="border-b border-border/60 pb-4 dark:border-border/50">
          <CardTitle className="text-base font-bold">Find a course</CardTitle>
          <CardDescription>Filter the catalog and switch between all listings, your enrollments, and open spots</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Name, code, or instructor…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-11 pl-10 shadow-sm"
            />
          </div>

          <Tabs defaultValue="all" className="w-full">
            <TabsList className={tabListClass}>
              <TabsTrigger value="all" className={tabTriggerClass}>
                All ({filteredCourses.length})
              </TabsTrigger>
              <TabsTrigger value="enrolled" className={tabTriggerClass}>
                Mine ({enrolledCourses.length})
              </TabsTrigger>
              <TabsTrigger value="available" className={tabTriggerClass}>
                Open ({availableCourses.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="mt-6 space-y-4 focus-visible:outline-none">
              {filteredCourses.length === 0 ? (
                <div className="rounded-xl border border-dashed border-violet-200/80 bg-violet-50/30 py-14 text-center dark:border-violet-900/50 dark:bg-violet-950/20">
                  <BookOpen className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
                  <p className="font-medium text-foreground">No courses match your search</p>
                  <p className="mt-1 text-sm text-muted-foreground">Try different keywords or clear the search box</p>
                </div>
              ) : (
                <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                  {filteredCourses.map((course) => (
                    <CourseCard key={course.id} course={course} />
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="enrolled" className="mt-6 space-y-4 focus-visible:outline-none">
              {enrolledCourses.length === 0 ? (
                <div className="rounded-xl border border-dashed border-violet-200/80 bg-violet-50/30 py-14 text-center dark:border-violet-900/50 dark:bg-violet-950/20">
                  <BookOpen className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
                  <p className="font-medium text-foreground">You&apos;re not enrolled in any courses yet</p>
                  <p className="mt-1 text-sm text-muted-foreground">Use the Open tab to request access</p>
                </div>
              ) : (
                <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                  {enrolledCourses.map((course) => (
                    <CourseCard key={course.id} course={course} />
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="available" className="mt-6 space-y-4 focus-visible:outline-none">
              {availableCourses.length === 0 ? (
                <div className="rounded-xl border border-dashed border-emerald-200/80 bg-emerald-50/30 py-14 text-center dark:border-emerald-900/50 dark:bg-emerald-950/20">
                  <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-emerald-600 dark:text-emerald-400" />
                  <p className="font-medium text-foreground">You&apos;re caught up</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    You&apos;ve enrolled or requested access to every course in the catalog
                  </p>
                </div>
              ) : (
                <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                  {availableCourses.map((course) => (
                    <CourseCard key={course.id} course={course} />
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

