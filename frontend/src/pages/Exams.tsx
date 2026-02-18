import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Plus, Search, Calendar, ClipboardList, MoreVertical, Eye, Edit, Trash2, X } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { format } from 'date-fns';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';

export default function Exams() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();
  const courseId = searchParams.get('course');

  // Fetch exams - filter by course if courseId is provided
  const { data: exams, isLoading: examsLoading } = useQuery({
    queryKey: ['exams', courseId],
    queryFn: () => api.exams.getAll(courseId || undefined),
  });

  // Fetch courses
  const { data: courses } = useQuery({
    queryKey: ['courses'],
    queryFn: () => api.courses.getAll(),
  });

  // Fetch submissions
  const { data: submissions } = useQuery({
    queryKey: ['submissions'],
    queryFn: () => api.submissions.getAll(),
  });

  const filteredExams = (exams || []).filter(
    (exam: any) =>
      exam.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
      (!courseId || exam.courseId === courseId)
  );

  const getCourse = (courseId: string) => (courses || []).find((c: any) => c.id === courseId);
  const getSubmissionCount = (examId: string) => (submissions || []).filter((s: any) => s.examId === examId).length;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">Exams</h1>
              {courseId && courses && (
                <Badge variant="secondary" className="text-sm">
                  {courses.find((c: any) => c.id === courseId)?.name || 'Filtered by Course'}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-4 w-4 p-0 ml-2"
                    onClick={() => {
                      setSearchParams({});
                    }}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground mt-1">
              {courseId 
                ? `Exams for ${courses?.find((c: any) => c.id === courseId)?.name || 'this course'}`
                : 'Create and manage your exams with gold solutions'}
            </p>
          </div>
          <Button asChild>
            <Link to={courseId ? `/exams/new?courseId=${courseId}` : '/exams/new'}>
              <Plus className="h-4 w-4 mr-2" />
              Create Exam
            </Link>
          </Button>
        </div>

        {/* Search */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search exams..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Exams Table */}
        {examsLoading ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">Loading exams...</p>
          </div>
        ) : filteredExams.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">
              {searchQuery ? 'No exams found matching your search' : 'No exams yet. Create your first exam!'}
            </p>
          </div>
        ) : (
          <div className="rounded-xl border bg-card overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Exam</TableHead>
                  <TableHead>Course</TableHead>
                  <TableHead>Questions</TableHead>
                  <TableHead>Points</TableHead>
                  <TableHead>Submissions</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredExams.map((exam: any) => {
                const course = getCourse(exam.courseId);
                const submissionCount = getSubmissionCount(exam.id);
                return (
                  <TableRow key={exam.id} className="group">
                    <TableCell>
                      <div>
                        <Link
                          to={`/exams/${exam.id}`}
                          className="font-medium hover:text-primary transition-colors"
                        >
                          {exam.title}
                        </Link>
                        {exam.description && (
                          <p className="text-sm text-muted-foreground line-clamp-1">
                            {exam.description}
                          </p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{course?.code}</Badge>
                    </TableCell>
                    <TableCell className="font-mono">{exam.questions?.length || 0}</TableCell>
                    <TableCell className="font-mono">{exam.totalPoints}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <ClipboardList className="h-4 w-4 text-muted-foreground" />
                        <span>{submissionCount}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      {exam.dueDate ? (
                        <div className="flex items-center gap-1.5 text-sm">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          {format(new Date(exam.dueDate), 'MMM d, yyyy')}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <Link to={`/exams/${exam.id}`}>
                              <Eye className="h-4 w-4 mr-2" />
                              View Details
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Edit className="h-4 w-4 mr-2" />
                            Edit Exam
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-destructive">
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete Exam
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
        )}
      </div>
    </DashboardLayout>
  );
}