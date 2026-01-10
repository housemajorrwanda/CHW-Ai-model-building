import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { coursesAPI } from '@/lib/api';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { BookOpen, GraduationCap, Search, CheckCircle2, Clock, XCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

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
      <Card className="hover:shadow-lg transition-shadow">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-1 flex-1">
              <CardTitle className="text-lg flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-primary" />
                {course.name}
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
            <p className="text-sm text-muted-foreground line-clamp-2">
              {course.description || 'No description available'}
            </p>
            
            <div className="flex items-center gap-4 text-sm">
              <span className="text-muted-foreground">
                <strong className="text-foreground">{course.code}</strong>
              </span>
              <span className="text-muted-foreground">
                {course.examCount} {course.examCount === 1 ? 'exam' : 'exams'}
              </span>
              <span className="text-muted-foreground">
                {course.enrolledStudents.length} students
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
        <CardFooter>
          {status === 'enrolled' && (
            <Button variant="outline" className="w-full" disabled>
              <CheckCircle2 className="mr-2 h-4 w-4 text-green-600" />
              Enrolled
            </Button>
          )}
          {status === 'pending' && (
            <Button variant="outline" className="w-full" disabled>
              <Clock className="mr-2 h-4 w-4 text-yellow-600" />
              Pending Approval
            </Button>
          )}
          {status === null && (
            <Button
              className="w-full"
              onClick={() => handleEnroll(course.id)}
              disabled={isEnrolling}
            >
              {isEnrolling ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Enrolling...
                </>
              ) : (
                'Request Enrollment'
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
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Browse Courses</h1>
        <p className="text-muted-foreground">
          Discover and enroll in courses to start your learning journey
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search courses by name, code, or professor..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="all" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="all">
            All Courses ({filteredCourses.length})
          </TabsTrigger>
          <TabsTrigger value="enrolled">
            My Courses ({enrolledCourses.length})
          </TabsTrigger>
          <TabsTrigger value="available">
            Available ({availableCourses.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4 mt-6">
          {filteredCourses.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <BookOpen className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No courses found</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredCourses.map(course => (
                <CourseCard key={course.id} course={course} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="enrolled" className="space-y-4 mt-6">
          {enrolledCourses.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <BookOpen className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-2">You're not enrolled in any courses yet</p>
                <p className="text-sm text-muted-foreground">Browse available courses to get started</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {enrolledCourses.map(course => (
                <CourseCard key={course.id} course={course} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="available" className="space-y-4 mt-6">
          {availableCourses.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <CheckCircle2 className="h-12 w-12 text-green-600 mb-4" />
                <p className="text-muted-foreground">
                  You've enrolled or requested enrollment in all available courses
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {availableCourses.map(course => (
                <CourseCard key={course.id} course={course} />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

