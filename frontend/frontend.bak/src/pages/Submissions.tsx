import { useState } from 'react';
import { Link } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Search, Clock, CheckCircle2, Loader2, Eye, Play } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';

export default function Submissions() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Fetch submissions
  const { data: submissions, isLoading, refetch } = useQuery({
    queryKey: ['submissions', statusFilter],
    queryFn: () => api.submissions.getAll({ status: statusFilter !== 'all' ? statusFilter : undefined }),
  });

  // Fetch exams
  const { data: exams } = useQuery({
    queryKey: ['exams'],
    queryFn: () => api.exams.getAll(),
  });

  const filteredSubmissions = (submissions || []).filter((submission: any) => {
    const matchesSearch = submission.studentName.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  const getExam = (examId: string) => (exams || []).find((e: any) => e.id === examId);

  const statusConfig = {
    pending: { label: 'Pending', icon: Clock, className: 'bg-warning/10 text-warning border-warning/20' },
    grading: { label: 'Grading', icon: Loader2, className: 'bg-primary/10 text-primary border-primary/20' },
    graded: { label: 'Graded', icon: CheckCircle2, className: 'bg-success/10 text-success border-success/20' },
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Submissions</h1>
          <p className="text-muted-foreground mt-1">Review and grade student submissions</p>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by student name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="grading">Grading</SelectItem>
              <SelectItem value="graded">Graded</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Submissions Table */}
        {isLoading ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">Loading submissions...</p>
          </div>
        ) : filteredSubmissions.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">
              {searchQuery ? 'No submissions found matching your search' : 'No submissions yet'}
            </p>
          </div>
        ) : (
          <div className="rounded-xl border bg-card overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Student</TableHead>
                  <TableHead>Exam</TableHead>
                  <TableHead>Submitted</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSubmissions.map((submission: any) => {
                const exam = getExam(submission.examId);
                const status = statusConfig[submission.status];
                const StatusIcon = status.icon;

                return (
                  <TableRow key={submission.id} className="group">
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary font-medium text-sm">
                          {submission.studentName.charAt(0)}
                        </div>
                        <span className="font-medium">{submission.studentName}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm">{exam?.title}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {format(new Date(submission.submittedAt), 'MMM d, yyyy h:mm a')}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn('gap-1', status.className)}>
                        <StatusIcon className={cn('h-3 w-3', submission.status === 'grading' && 'animate-spin')} />
                        {status.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {submission.status === 'graded' && submission.totalScore !== undefined ? (
                        <span className="font-mono font-semibold">
                          {submission.totalScore}/{submission.maxScore}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Button variant="ghost" size="sm" asChild>
                          <Link to={`/submissions/${submission.id}`}>
                            <Eye className="h-4 w-4 mr-1" />
                            View
                          </Link>
                        </Button>
                        {submission.status === 'pending' && (
                          <Button variant="default" size="sm" asChild>
                            <Link to={`/submissions/${submission.id}/grade`}>
                              <Play className="h-4 w-4 mr-1" />
                              Grade
                            </Link>
                          </Button>
                        )}
                      </div>
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