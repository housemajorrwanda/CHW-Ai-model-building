import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/api/client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

const CHART_FILLS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
];

interface CountItem {
  label: string;
  key: string;
  count: number;
}

interface InstructorCourseRow {
  courseId: string;
  courseName: string;
  courseCode: string;
  submissionCount: number;
  gradedCount: number;
  avgPercent?: number | null;
}

interface WeekRow {
  weekStart: string;
  count: number;
}

interface EnrollmentRow {
  courseId: string;
  courseName: string;
  approvedStudents: number;
}

interface InstructorAnalytics {
  submissionStatus: CountItem[];
  courseBreakdown: InstructorCourseRow[];
  weeklySubmissions: WeekRow[];
  enrollmentsByCourse: EnrollmentRow[];
}

interface StudentExamScore {
  examId: string;
  examTitle: string;
  courseName: string;
  percent: number;
  submittedAt: string;
}

interface StudentCoursePerf {
  courseId: string;
  courseName: string;
  avgPercent: number;
  gradedCount: number;
}

interface StudentAnalytics {
  submissionStatus: CountItem[];
  releasedExamScores: StudentExamScore[];
  coursePerformance: StudentCoursePerf[];
}

interface DashboardAnalyticsResponse {
  role: string;
  instructor?: InstructorAnalytics | null;
  student?: StudentAnalytics | null;
}

function formatWeekTick(iso: string) {
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function truncate(s: string, n: number) {
  if (s.length <= n) return s;
  return `${s.slice(0, n - 1)}…`;
}

export default function Analytics() {
  const { user } = useAuth();

  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', 'analytics'],
    queryFn: () => api.dashboard.getAnalytics() as Promise<DashboardAnalyticsResponse>,
    enabled: !!user,
  });

  const instructor = data?.instructor;
  const student = data?.student;

  const instructorStatusPie = useMemo(() => {
    if (!instructor?.submissionStatus?.length) return [];
    return instructor.submissionStatus
      .filter((s) => s.count > 0)
      .map((s) => ({ name: s.label, value: s.count, key: s.key }));
  }, [instructor]);

  const studentStatusPie = useMemo(() => {
    if (!student?.submissionStatus?.length) return [];
    return student.submissionStatus
      .filter((s) => s.count > 0)
      .map((s) => ({ name: s.label, value: s.count, key: s.key }));
  }, [student]);

  const courseBarData = useMemo(() => {
    if (!instructor?.courseBreakdown?.length) return [];
    return instructor.courseBreakdown.map((c) => ({
      name: truncate(c.courseName, 14),
      full: `${c.courseCode} — ${c.courseName}`,
      avg: c.avgPercent ?? null,
      hasAvg: c.avgPercent != null,
      subs: c.submissionCount,
    }));
  }, [instructor]);

  const weeklyLineData = useMemo(() => {
    if (!instructor?.weeklySubmissions?.length) return [];
    return instructor.weeklySubmissions.map((w) => ({
      ...w,
      label: formatWeekTick(w.weekStart),
    }));
  }, [instructor]);

  const enrollmentBarData = useMemo(() => {
    if (!instructor?.enrollmentsByCourse?.length) return [];
    return instructor.enrollmentsByCourse.map((e) => ({
      name: truncate(e.courseName, 12),
      full: e.courseName,
      students: e.approvedStudents,
    }));
  }, [instructor]);

  const studentCourseBar = useMemo(() => {
    if (!student?.coursePerformance?.length) return [];
    return student.coursePerformance.map((c) => ({
      name: truncate(c.courseName, 16),
      full: c.courseName,
      avg: c.avgPercent,
      n: c.gradedCount,
    }));
  }, [student]);

  const studentExamBar = useMemo(() => {
    if (!student?.releasedExamScores?.length) return [];
    return student.releasedExamScores.map((r) => ({
      name: truncate(r.examTitle, 20),
      full: `${r.courseName}: ${r.examTitle}`,
      percent: r.percent,
    }));
  }, [student]);

  const isInstructorView = user?.role === 'professor' || user?.role === 'admin';

  return (
    <div className="mx-auto max-w-7xl space-y-8 pb-8">
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
            user?.role === 'student' ? 'text-teal-800 dark:text-teal-300' : 'text-violet-700 dark:text-violet-400'
          )}
        >
          Analytics
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          {isInstructorView ? 'Class insights' : 'Your progress'}
        </h1>
        <p className="mt-2 max-w-2xl text-muted-foreground leading-relaxed">
          {isInstructorView
            ? 'Submission flow, course averages, enrollments, and weekly activity across your teaching.'
            : 'How your attempts are distributed, averages by course, and scores on released exams.'}
        </p>
      </header>

      {isLoading && (
        <div className="flex min-h-[280px] items-center justify-center rounded-2xl border border-dashed">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {error && !isLoading && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardHeader>
            <CardTitle className="text-destructive">Could not load analytics</CardTitle>
            <CardDescription>{(error as Error).message}</CardDescription>
          </CardHeader>
        </Card>
      )}

      {!isLoading && !error && isInstructorView && instructor && (
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartCard
            title="Submissions by status"
            description="All attempts linked to your courses"
            empty={instructorStatusPie.length === 0}
            emptyMessage="No submissions yet."
          >
            <div className="h-[280px] w-full min-h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={instructorStatusPie}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={56}
                    outerRadius={96}
                    paddingAngle={2}
                  >
                    {instructorStatusPie.map((entry, i) => (
                      <Cell key={entry.key} fill={CHART_FILLS[i % CHART_FILLS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => [v, 'Submissions']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <ChartCard
            title="Average score by course"
            description="Among attempts with recorded scores"
            empty={courseBarData.length === 0}
            emptyMessage="Create a course and collect submissions to see averages."
          >
            <div className="h-[280px] w-full min-h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={courseBarData} margin={{ left: 4, right: 8, top: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted/50" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} height={48} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} width={32} />
                  <Tooltip
                    formatter={(v: number, _n, p) => [(p?.payload as { hasAvg?: boolean })?.hasAvg ? `${v}%` : '—', 'Avg']}
                    labelFormatter={(_, p) => (p?.[0]?.payload as { full?: string })?.full ?? ''}
                  />
                  <Bar dataKey="avg" radius={[4, 4, 0, 0]} fill="hsl(var(--chart-1))" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <ChartCard
            title="Submissions per week"
            description="Last 10 weeks (UTC)"
            empty={weeklyLineData.every((w) => w.count === 0)}
            emptyMessage="No submissions in this window."
          >
            <div className="h-[280px] w-full min-h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={weeklyLineData} margin={{ left: 4, right: 8, top: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted/50" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={32} />
                  <Tooltip formatter={(v: number) => [v, 'Count']} />
                  <Line type="monotone" dataKey="count" stroke="hsl(var(--chart-2))" strokeWidth={2} dot />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <ChartCard
            title="Enrolled students"
            description="Approved enrollments per course"
            empty={enrollmentBarData.length === 0}
            emptyMessage="No approved enrollments yet."
          >
            <div className="h-[280px] w-full min-h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={enrollmentBarData} layout="vertical" margin={{ left: 8, right: 8, top: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted/50" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" width={88} tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(v: number) => [v, 'Students']}
                    labelFormatter={(_, p) => (p?.[0]?.payload as { full?: string })?.full ?? ''}
                  />
                  <Bar dataKey="students" radius={[0, 4, 4, 0]} fill="hsl(var(--chart-3))" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        </div>
      )}

      {!isLoading && !error && user?.role === 'student' && student && (
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartCard
            title="Your submissions by status"
            description="Across all your exams"
            empty={studentStatusPie.length === 0}
            emptyMessage="No submissions yet."
          >
            <div className="h-[280px] w-full min-h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={studentStatusPie}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={56}
                    outerRadius={96}
                    paddingAngle={2}
                  >
                    {studentStatusPie.map((entry, i) => (
                      <Cell key={entry.key} fill={CHART_FILLS[i % CHART_FILLS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => [v, 'Count']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <ChartCard
            title="Released results by course"
            description="Average percent where grades are published"
            empty={studentCourseBar.length === 0}
            emptyMessage="Join a course and complete exams to see averages here."
          >
            <div className="h-[280px] w-full min-h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={studentCourseBar} margin={{ left: 4, right: 8, top: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted/50" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} height={48} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} width={32} />
                  <Tooltip
                    formatter={(v: number, _n, p) => {
                      const n = (p?.[0]?.payload as { n?: number })?.n;
                      return [`${v}% (${n} graded)`, 'Average'];
                    }}
                    labelFormatter={(_, p) => (p?.[0]?.payload as { full?: string })?.full ?? ''}
                  />
                  <Bar dataKey="avg" radius={[4, 4, 0, 0]} fill="hsl(var(--chart-1))" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>

          <ChartCard
            className="lg:col-span-2"
            title="Released exam scores"
            description="Trend across up to 20 most recent released grades (oldest to newest)"
            empty={studentExamBar.length === 0}
            emptyMessage="No released grades yet. Your instructor publishes scores when ready."
          >
            <div className="h-[320px] w-full min-h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={studentExamBar} margin={{ left: 4, right: 8, top: 8, bottom: 64 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted/50" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-28} textAnchor="end" height={70} interval={0} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} width={36} />
                  <Tooltip
                    formatter={(v: number) => [`${v}%`, 'Score']}
                    labelFormatter={(_, p) => (p?.[0]?.payload as { full?: string })?.full ?? ''}
                  />
                  <Line
                    type="monotone"
                    dataKey="percent"
                    stroke="hsl(var(--chart-2))"
                    strokeWidth={2}
                    dot={{ r: 4, fill: 'hsl(var(--chart-2))' }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        </div>
      )}
    </div>
  );
}

function ChartCard({
  title,
  description,
  children,
  empty,
  emptyMessage,
  className,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  empty?: boolean;
  emptyMessage?: string;
  className?: string;
}) {
  return (
    <Card className={cn('overflow-hidden rounded-2xl border shadow-sm', className)}>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {empty ? (
          <div className="flex min-h-[220px] items-center justify-center rounded-xl border border-dashed bg-muted/20 px-4 text-center text-sm text-muted-foreground">
            {emptyMessage}
          </div>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}
