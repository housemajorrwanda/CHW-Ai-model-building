import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { coursesAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Plus, Search, Users, FileText, Loader2, BookOpen, UserCheck, UserX, Clock } from 'lucide-react';
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
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">My Courses</h1>
            <p className="text-muted-foreground mt-1">Manage your courses and enrolled students</p>
          </div>
          <Button onClick={() => navigate('/courses/new')}>
            <Plus className="h-4 w-4 mr-2" />
            Create Course
          </Button>
        </div>

        {/* Search */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search courses..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Courses Grid */}
        {filteredCourses.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <BookOpen className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">No courses found</p>
              <Button onClick={() => navigate('/courses/new')}>
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Course
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredCourses.map((course) => (
              <Card
                key={course.id}
                className="group hover:shadow-lg transition-shadow"
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <Badge variant="secondary" className="mb-2">
                      {course.code}
                    </Badge>
                    <Badge variant="outline" className="capitalize">
                      {course.level.replace('_', ' ')}
                    </Badge>
                  </div>
                  <CardTitle className="text-lg">
                    {course.name}
                  </CardTitle>
                  {course.description && (
                    <CardDescription className="line-clamp-2">{course.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        <Users className="h-4 w-4" />
                        <span>{course.enrolledStudents.length} students</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <FileText className="h-4 w-4" />
                        <span>{course.examCount} exams</span>
                      </div>
                    </div>
                    {course.pendingEnrollments.length > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <Clock className="h-4 w-4 text-yellow-600" />
                        <span className="text-yellow-600 font-medium">
                          {course.pendingEnrollments.length} pending request{course.pendingEnrollments.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                    )}
                  </div>
                </CardContent>
                <CardFooter className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => navigate(`/exams?course=${course.id}`)}
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    View Exams
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => setManagingCourse(course)}
                  >
                    <Users className="h-4 w-4 mr-2" />
                    Manage Students
                  </Button>
                </CardFooter>
              </Card>
            ))}
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