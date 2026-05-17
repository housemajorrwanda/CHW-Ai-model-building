import { useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { RecentSubmissions } from '@/components/dashboard/RecentSubmissions';
import { StudentRecentActivity } from '@/components/dashboard/StudentRecentActivity';
import { partitionStudentExams } from '@/lib/studentExamBuckets';
import { coursesAPI, examsAPI } from '@/lib/api';
import {
  BookOpen,
  FileText,
  ClipboardList,
  Clock,
  TrendingUp,
  Users,
  GraduationCap,
  Sparkles,
  PlusCircle,
  CheckCircle2,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Course, DashboardStats, Submission } from '@/types';

export default function Dashboard() {
  const { user } = useAuth();

  // Fetch dashboard stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => api.dashboard.getStats() as Promise<DashboardStats>,
    enabled: !!user,
  });

  // Fetch recent submissions
  const { data: submissionsData, isLoading: submissionsLoading } = useQuery({
    queryKey: ['submissions'],
    queryFn: () => api.submissions.getAll() as Promise<Submission[]>,
    enabled: !!user,
  });

  // Fetch courses
  const { data: coursesData, isLoading: coursesLoading } = useQuery({
    queryKey: ['courses'],
    queryFn: () => api.courses.getAll() as Promise<Course[]>,
    enabled: !!user && user.role === 'professor',
  });

  const { data: enrolledCourses = [], isLoading: enrolledLoading } = useQuery({
    queryKey: ['courses', 'enrolled'],
    queryFn: () => coursesAPI.getEnrolled() as Promise<Course[]>,
    enabled: !!user && user.role === 'student',
  });

  const { data: studentExams = [], isLoading: studentExamsLoading } = useQuery({
    queryKey: ['exams', 'student-portal'],
    queryFn: () => examsAPI.getAll() as Promise<any[]>,
    enabled: !!user && user.role === 'student',
  });

  const recentSubmissions = submissionsData?.slice(0, 5) || [];
  const courses = coursesData || [];

  const studentBuckets = useMemo(() => {
    if (user?.role !== 'student' || !submissionsData) {
      return { available: [] as any[], submitted: [] as any[], graded: [] as any[] };
    }
    return partitionStudentExams(studentExams, submissionsData as any[]);
  }, [user?.role, studentExams, submissionsData]);

  const examTitleById = useMemo(() => {
    const m = new Map<string, string>();
    for (const e of studentExams) {
      if (e?.id && e?.title) m.set(e.id, e.title as string);
    }
    return m;
  }, [studentExams]);

  const studentReleasedAvg = useMemo(() => {
    if (user?.role !== 'student' || !submissionsData) return null;
    const approved = (submissionsData as any[]).filter(
      (s) => s.status === 'approved' && s.totalScore != null && s.maxScore > 0
    );
    if (approved.length === 0) return null;
    return Math.round(
      approved.reduce((sum, s) => sum + (s.totalScore / s.maxScore) * 100, 0) / approved.length
    );
  }, [user?.role, submissionsData]);

  return (
      <div className="mx-auto max-w-7xl space-y-8 pb-8">
        {/* Header */}
        <header
          className={cn(
            'rounded-2xl border p-6 shadow-sm sm:p-8',
            user?.role === 'student'
              ? 'border-teal-200/60 bg-gradient-to-br from-teal-50/80 via-white to-cyan-50/40 dark:border-teal-900/40 dark:from-teal-950/30 dark:via-card dark:to-cyan-950/20'
              : 'border-violet-200/70 bg-gradient-to-br from-violet-50/90 via-white to-indigo-50/40 dark:from-violet-950/40 dark:via-card dark:to-indigo-950/20 dark:border-violet-900/50'
          )}
        >
          <p
            className={cn(
              'text-xs font-semibold uppercase tracking-wider',
              user?.role === 'student'
                ? 'text-teal-800 dark:text-teal-300'
                : 'text-violet-700 dark:text-violet-400'
            )}
          >
            {user?.role === 'professor' ? 'Instructor workspace' : user?.role === 'student' ? 'Student home' : 'Admin'}
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
            Welcome back{user?.name ? `, ${user.name.split(' ')[0]}` : ''}
          </h1>
          <p className="mt-2 max-w-2xl text-[1.05rem] text-muted-foreground leading-relaxed">
            {user?.role === 'professor'
              ? 'Track courses, submissions, and grading at a glance.'
              : user?.role === 'student'
              ? 'See what needs your attention, what is being graded, and scores your instructors have released.'
              : 'System overview and quick access to tools.'}
          </p>
        </header>

        {/* Stats Grid */}
        {user?.role === 'student' ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatsCard
              title="My courses"
              value={enrolledLoading ? '…' : enrolledCourses.length}
              icon={BookOpen}
              variant="softRose"
            />
            <StatsCard
              title="Exams to complete"
              value={studentExamsLoading ? '…' : studentBuckets.available.length}
              icon={FileText}
              variant="softApricot"
            />
            <StatsCard
              title="Under review"
              value={studentExamsLoading ? '…' : studentBuckets.submitted.length}
              icon={Clock}
              variant="softLilac"
            />
            <StatsCard
              title="Released results"
              value={studentExamsLoading ? '…' : studentBuckets.graded.length}
              icon={CheckCircle2}
              variant="softSky"
            />
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatsCard
              title="Total Courses"
              value={statsLoading ? '...' : stats?.totalCourses || 0}
              icon={BookOpen}
              variant="primary"
            />
            <StatsCard
              title="Total Exams"
              value={statsLoading ? '...' : stats?.totalExams || 0}
              icon={FileText}
              variant="accent"
            />
            <StatsCard
              title="Submissions"
              value={statsLoading ? '...' : stats?.totalSubmissions || 0}
              icon={ClipboardList}
            />
            <StatsCard
              title="Pending Grading"
              value={statsLoading ? '...' : stats?.pendingGrading || 0}
              icon={Clock}
              variant="warning"
            />
          </div>
        )}

        {/* Main Content Grid */}
        <div className="grid gap-8 lg:grid-cols-3">
          {/* Recent Submissions - Takes 2 columns */}
          <div className="lg:col-span-2">
            {user?.role === 'student' ? (
              submissionsLoading ? (
                <div className="flex min-h-[200px] items-center justify-center rounded-2xl border border-dashed border-teal-200/80 bg-teal-50/20 dark:border-teal-900/50 dark:bg-teal-950/20">
                  <p className="text-sm font-medium text-muted-foreground">Loading activity…</p>
                </div>
              ) : (
                <StudentRecentActivity submissions={recentSubmissions} examTitleById={examTitleById} />
              )
            ) : submissionsLoading ? (
              <div className="flex min-h-[200px] items-center justify-center rounded-2xl border-2 border-dashed border-violet-200 bg-violet-50/30 dark:border-violet-900 dark:bg-violet-950/20">
                <p className="text-sm font-medium text-muted-foreground">Loading submissions…</p>
              </div>
            ) : (
              <RecentSubmissions submissions={recentSubmissions} />
            )}
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Average Score Card */}
            {(user?.role === 'student' ? studentReleasedAvg != null : stats?.averageScore != null) && (
              <Card className="animate-fade-up overflow-hidden rounded-2xl border-emerald-200/70 bg-gradient-to-br from-emerald-50/80 to-teal-50/30 shadow-sm dark:border-emerald-900/50 dark:from-emerald-950/30">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base font-semibold text-emerald-900 dark:text-emerald-100">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-600 text-white shadow-sm">
                      <TrendingUp className="h-4 w-4" />
                    </span>
                    {user?.role === 'student' ? 'Average (released)' : 'Average score'}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="mb-3 flex items-end gap-2">
                    <span className="text-4xl font-bold tabular-nums tracking-tight">
                      {user?.role === 'student'
                        ? studentReleasedAvg!.toFixed(0)
                        : stats!.averageScore!.toFixed(1)}
                    </span>
                    <span className="mb-1 text-muted-foreground">%</span>
                  </div>
                  <Progress
                    value={user?.role === 'student' ? studentReleasedAvg! : stats!.averageScore!}
                    className="h-3 border border-emerald-200/50 bg-white/70 dark:border-emerald-900/50 dark:bg-emerald-950/40"
                  />
                </CardContent>
              </Card>
            )}

            {/* Quick Actions */}
            <Card className="animate-fade-up rounded-2xl border-2 border-violet-200/60 shadow-sm dark:border-violet-900/50">
              <CardHeader className="border-b border-violet-100 pb-3 dark:border-violet-900/40">
                <CardTitle className="text-base font-bold">Quick actions</CardTitle>
                <p className="text-xs font-normal text-muted-foreground">Shortcuts to common tasks</p>
              </CardHeader>
              <CardContent className="space-y-3 pt-4">
                {user?.role === 'professor' && (
                  <>
                    <Button
                      className="h-12 w-full justify-start gap-2 bg-violet-600 font-semibold shadow-md hover:bg-violet-700"
                      asChild
                    >
                      <Link to="/exams/new">
                        <Sparkles className="h-4 w-4" />
                        Create new exam
                      </Link>
                    </Button>
                    <Button
                      variant="outline"
                      className="h-12 w-full justify-start gap-2 border-2 border-violet-200 font-semibold hover:bg-violet-50 dark:border-violet-800 dark:hover:bg-violet-950/50"
                      asChild
                    >
                      <Link to="/courses/new">
                        <PlusCircle className="h-4 w-4 text-violet-600" />
                        Add course
                      </Link>
                    </Button>
                  </>
                )}
                {user?.role === 'student' && (
                  <>
                    <Button
                      className="h-12 w-full justify-start gap-2 rounded-xl bg-teal-600 font-semibold shadow-md hover:bg-teal-700"
                      asChild
                    >
                      <Link to="/my-exams">
                        <ClipboardList className="h-4 w-4" />
                        My exams
                      </Link>
                    </Button>
                    <Button
                      variant="outline"
                      className="h-12 w-full justify-start gap-2 rounded-xl border-2 border-teal-200 font-semibold hover:bg-teal-50 dark:border-teal-800 dark:hover:bg-teal-950/40"
                      asChild
                    >
                      <Link to="/my-results">
                        <TrendingUp className="h-4 w-4 text-teal-700 dark:text-teal-400" />
                        View results
                      </Link>
                    </Button>
                    <Button
                      variant="outline"
                      className="h-12 w-full justify-start gap-2 rounded-xl border border-border font-medium"
                      asChild
                    >
                      <Link to="/browse-courses">
                        <BookOpen className="h-4 w-4 text-muted-foreground" />
                        Browse courses
                      </Link>
                    </Button>
                  </>
                )}
                {user?.role === 'admin' && (
                  <>
                    <Button className="h-12 w-full justify-start font-semibold" asChild>
                      <Link to="/users">
                        <Users className="mr-2 h-4 w-4" />
                        Manage users
                      </Link>
                    </Button>
                    <Button variant="outline" className="h-12 w-full justify-start font-semibold" asChild>
                      <Link to="/analytics">
                        <TrendingUp className="mr-2 h-4 w-4" />
                        Analytics
                      </Link>
                    </Button>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Active Courses Preview */}
            {user?.role === 'professor' && (
              <Card className="animate-fade-up rounded-2xl border-2 border-slate-200/80 shadow-sm dark:border-slate-800">
                <CardHeader className="border-b border-border/60 pb-3">
                  <CardTitle className="flex items-center gap-2 text-base font-bold">
                    <GraduationCap className="h-5 w-5 text-violet-600" />
                    Your courses
                  </CardTitle>
                  <p className="text-xs font-normal text-muted-foreground">Recently active — tap to open</p>
                </CardHeader>
                <CardContent className="space-y-2 pt-4">
                  {coursesLoading ? (
                    <p className="text-sm text-muted-foreground">Loading courses…</p>
                  ) : courses.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-violet-200 bg-violet-50/40 p-4 text-center dark:border-violet-900 dark:bg-violet-950/20">
                      <p className="text-sm font-medium">No courses yet</p>
                      <Button variant="link" className="mt-1 h-auto p-0 text-violet-700" asChild>
                        <Link to="/courses/new">Create a course</Link>
                      </Button>
                    </div>
                  ) : (
                    courses.slice(0, 4).map((course) => {
                      const n = course.students?.length ?? 0;
                      return (
                        <Link
                          key={course.id}
                          to={`/courses/${course.id}`}
                          className="group flex items-center justify-between gap-3 rounded-xl border border-border/80 bg-muted/30 p-3 transition-all hover:border-violet-300 hover:bg-violet-50/50 hover:shadow-sm dark:hover:border-violet-800 dark:hover:bg-violet-950/30"
                        >
                          <div className="min-w-0">
                            <p className="truncate font-semibold text-foreground group-hover:text-violet-900 dark:group-hover:text-violet-100">
                              {course.name}
                            </p>
                            <p className="text-xs font-medium text-muted-foreground">{course.code}</p>
                          </div>
                          <span className="shrink-0 rounded-full bg-background px-2.5 py-1 text-xs font-semibold tabular-nums text-muted-foreground ring-1 ring-border">
                            {n} student{n === 1 ? '' : 's'}
                          </span>
                        </Link>
                      );
                    })
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
  );
}
