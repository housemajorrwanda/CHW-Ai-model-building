import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/api/client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Megaphone, BookOpen, Loader2, ArrowRight, GraduationCap } from 'lucide-react';
import { cn } from '@/lib/utils';

type CourseRow = {
  id: string;
  name: string;
  code: string;
  professorName?: string;
};

export default function AnnouncementsHub() {
  const { user } = useAuth();

  const { data: courses = [], isLoading } = useQuery({
    queryKey: ['announcements-hub-courses', user?.role],
    queryFn: async () => {
      if (user?.role === 'student') {
        return api.courses.getEnrolled() as Promise<CourseRow[]>;
      }
      return api.courses.getAll() as Promise<CourseRow[]>;
    },
    enabled: !!user && ['student', 'professor', 'admin'].includes(user.role),
  });

  const headerClass =
    user?.role === 'student'
      ? 'rounded-2xl border border-violet-200/60 bg-gradient-to-br from-violet-50/90 via-white to-fuchsia-50/35 p-6 shadow-sm dark:from-violet-950/30 dark:via-card dark:to-fuchsia-950/15 dark:border-violet-900/45 sm:p-8'
      : 'rounded-2xl border border-amber-200/60 bg-gradient-to-br from-amber-50/90 via-white to-orange-50/35 p-6 shadow-sm dark:from-amber-950/25 dark:via-card dark:to-orange-950/15 dark:border-amber-900/40 sm:p-8';

  return (
    <div className="mx-auto max-w-4xl space-y-8 pb-10">
      <header className={cn(headerClass)}>
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Course updates
        </p>
        <h1 className="mt-2 flex items-center gap-3 text-3xl font-bold tracking-tight sm:text-4xl">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Megaphone className="h-6 w-6" aria-hidden />
          </span>
          Announcements
        </h1>
        <p className="mt-3 max-w-2xl text-[1.05rem] leading-relaxed text-muted-foreground">
          {user?.role === 'student'
            ? 'Open a course you are enrolled in to read posts from your instructors and respond with reactions or comments.'
            : 'Pick one of your courses to post updates for students or review engagement on existing threads.'}
        </p>
      </header>

      <Card className="overflow-hidden rounded-2xl border border-border/80 shadow-sm">
        <CardHeader className="border-b border-border/60 pb-4">
          <CardTitle className="text-lg">Your courses</CardTitle>
          <CardDescription>
            {user?.role === 'student'
              ? 'Approved enrollments only'
              : 'Courses you teach (or all courses, if you are an admin)'}
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          {isLoading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : courses.length === 0 ? (
            <div className="rounded-xl border border-dashed py-14 text-center">
              <BookOpen className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
              <p className="font-medium">No courses yet</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {user?.role === 'student'
                  ? 'Join a course from Browse courses, then come back here.'
                  : 'Create a course from the Courses page first.'}
              </p>
              {user?.role === 'student' && (
                <Button asChild className="mt-6 rounded-xl">
                  <Link to="/browse-courses">Browse courses</Link>
                </Button>
              )}
              {(user?.role === 'professor' || user?.role === 'admin') && (
                <Button asChild className="mt-6 rounded-xl">
                  <Link to="/courses">Go to courses</Link>
                </Button>
              )}
            </div>
          ) : (
            <ul className="divide-y divide-border/60 rounded-xl border border-border/50">
              {courses.map((c) => (
                <li key={c.id}>
                  <Link
                    to={`/courses/${c.id}/announcements`}
                    className="flex items-center gap-4 px-4 py-4 transition-colors hover:bg-muted/40 sm:px-5"
                  >
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/8 text-primary">
                      <GraduationCap className="h-6 w-6" aria-hidden />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold leading-snug">{c.name}</p>
                      <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-sm text-muted-foreground">
                        <span className="font-mono text-xs">{c.code}</span>
                        {c.professorName && (
                          <>
                            <span className="text-border">·</span>
                            <span className="truncate">{c.professorName}</span>
                          </>
                        )}
                      </p>
                    </div>
                    <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
