import { useAuth } from '@/contexts/AuthContext';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { RecentSubmissions } from '@/components/dashboard/RecentSubmissions';
import { BookOpen, FileText, ClipboardList, Clock, TrendingUp, Users, GraduationCap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';

export default function Dashboard() {
  const { user } = useAuth();

  // Fetch dashboard stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => api.dashboard.getStats(),
    enabled: !!user,
  });

  // Fetch recent submissions
  const { data: submissionsData, isLoading: submissionsLoading } = useQuery({
    queryKey: ['submissions'],
    queryFn: () => api.submissions.getAll(),
    enabled: !!user,
  });

  // Fetch courses
  const { data: coursesData, isLoading: coursesLoading } = useQuery({
    queryKey: ['courses'],
    queryFn: () => api.courses.getAll(),
    enabled: !!user && user.role === 'professor',
  });

  const recentSubmissions = submissionsData?.slice(0, 5) || [];
  const courses = coursesData || [];

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Welcome back, {user?.name?.split(' ')[0]}
          </h1>
          <p className="text-muted-foreground mt-1">
            Here's what's happening with your {user?.role === 'professor' ? 'courses' : user?.role === 'student' ? 'exams' : 'system'} today.
          </p>
        </div>

        {/* Stats Grid */}
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

        {/* Main Content Grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Recent Submissions - Takes 2 columns */}
          <div className="lg:col-span-2">
            {submissionsLoading ? (
              <Card>
                <CardContent className="p-6">
                  <p className="text-muted-foreground">Loading submissions...</p>
                </CardContent>
              </Card>
            ) : (
              <RecentSubmissions submissions={recentSubmissions} />
            )}
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Average Score Card */}
            {stats?.averageScore && (
              <Card className="animate-fade-up">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-medium flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-accent" />
                    Average Score
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-end gap-2 mb-3">
                    <span className="text-4xl font-bold">{stats.averageScore.toFixed(1)}</span>
                    <span className="text-muted-foreground mb-1">%</span>
                  </div>
                  <Progress value={stats.averageScore} className="h-2" />
                </CardContent>
              </Card>
            )}

            {/* Quick Actions */}
            <Card className="animate-fade-up">
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-medium">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {user?.role === 'professor' && (
                  <>
                    <Button variant="outline" className="w-full justify-start" asChild>
                      <Link to="/exams/new">
                        <FileText className="h-4 w-4 mr-2" />
                        Create New Exam
                      </Link>
                    </Button>
                    <Button variant="outline" className="w-full justify-start" asChild>
                      <Link to="/courses/new">
                        <BookOpen className="h-4 w-4 mr-2" />
                        Add Course
                      </Link>
                    </Button>
                  </>
                )}
                {user?.role === 'student' && (
                  <>
                    <Button variant="outline" className="w-full justify-start" asChild>
                      <Link to="/submit">
                        <ClipboardList className="h-4 w-4 mr-2" />
                        Submit Exam
                      </Link>
                    </Button>
                    <Button variant="outline" className="w-full justify-start" asChild>
                      <Link to="/my-results">
                        <TrendingUp className="h-4 w-4 mr-2" />
                        View Results
                      </Link>
                    </Button>
                  </>
                )}
                {user?.role === 'admin' && (
                  <>
                    <Button variant="outline" className="w-full justify-start" asChild>
                      <Link to="/users">
                        <Users className="h-4 w-4 mr-2" />
                        Manage Users
                      </Link>
                    </Button>
                    <Button variant="outline" className="w-full justify-start" asChild>
                      <Link to="/analytics">
                        <TrendingUp className="h-4 w-4 mr-2" />
                        View Analytics
                      </Link>
                    </Button>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Active Courses Preview */}
            {user?.role === 'professor' && (
              <Card className="animate-fade-up">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-medium flex items-center gap-2">
                    <GraduationCap className="h-4 w-4 text-primary" />
                    Your Courses
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {coursesLoading ? (
                    <p className="text-sm text-muted-foreground">Loading courses...</p>
                  ) : courses.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No courses yet. Create your first course!</p>
                  ) : (
                    courses.slice(0, 3).map((course: any) => (
                      <Link
                        key={course.id}
                        to={`/courses/${course.id}`}
                        className="block p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                      >
                        <p className="font-medium text-sm">{course.name}</p>
                        <p className="text-xs text-muted-foreground">{course.code} • {course.students?.length || 0} students</p>
                      </Link>
                    ))
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}