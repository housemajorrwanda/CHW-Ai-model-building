import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { coursesAPI, examsAPI } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Save,
  ArrowLeft,
  Upload,
  FileText,
  ListChecks,
  Loader2,
  ClipboardList,
  Eye,
  Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';
import { QuestionBuilder, Question } from '@/components/exam-builder/QuestionBuilder';
import { PreviewPanel } from '@/components/exam-builder/PreviewPanel';
import { AnswerKeyUpload } from '@/components/exam-builder/AnswerKeyUpload';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

type WorkspaceTab = 'build' | 'details' | 'preview';

function mapGoldStepsForSave(steps: Question['goldSolutionSteps']) {
  return (steps ?? []).map((step, stepIdx) => ({
    stepNumber: stepIdx + 1,
    description: step.description,
    expression: step.expression,
    latex: step.latex,
    points: step.points,
    required: step.required,
  }));
}

function mapSubQuestionsForSave(subs: Question[], parentId: string): any[] {
  return (subs ?? []).map((sub, subIdx) => ({
    number: sub.number ?? subIdx + 1,
    text: sub.text,
    points: sub.points,
    questionType: sub.questionType || 'standard',
    richContent: sub.richContent,
    outlineLevel: sub.outlineLevel || 2,
    outlineTitle: (sub.outlineTitle || '').trim() || undefined,
    parentQuestionId: sub.parentQuestionId || parentId,
    subQuestions: mapSubQuestionsForSave(sub.subQuestions ?? [], sub.id),
    goldSolutionSteps: mapGoldStepsForSave(sub.goldSolutionSteps),
    finalAnswer: sub.finalAnswer,
    finalAnswerLatex: sub.finalAnswerLatex,
  }));
}

/** Convert API ISO datetime to `datetime-local` value in the user's timezone. */
function isoToDatetimeLocal(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function CreateExam() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const [searchParams] = useSearchParams();
  const { id: examIdFromRoute } = useParams<{ id: string }>();
  const examIdFromQuery = searchParams.get('examId');
  const courseIdFromQuery = searchParams.get('courseId');
  const examId = examIdFromRoute || examIdFromQuery || '';
  const isEditMode = !!examId;

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [courseId, setCourseId] = useState('');
  const [duration, setDuration] = useState(120);
  const [durationInput, setDurationInput] = useState('120');
  const [questions, setQuestions] = useState<Question[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [creationMode, setCreationMode] = useState<'manual' | 'upload'>('manual');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [dueDate, setDueDate] = useState<string>('');
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>('build');
  const [initialExpandedQuestionIds, setInitialExpandedQuestionIds] = useState<string[]>([]);

  // Fetch courses
  const { data: courses = [], isLoading: coursesLoading, error: coursesError } = useQuery({
    queryKey: ['courses'],
    queryFn: async () => {
      try {
        const data = await coursesAPI.getAll();
        return data;
      } catch (error) {
        console.error('Error loading courses:', error);
        toast.error('Failed to load courses: ' + (error as Error).message);
        throw error;
      }
    },
    enabled: isAuthenticated,
  });

  // Fetch exam data if editing
  const { data: examData, isLoading: examLoading } = useQuery({
    queryKey: ['exam', examId],
    queryFn: async () => {
      try {
        const data = await examsAPI.getById(examId!);
        return data;
      } catch (error) {
        console.error('Error loading exam:', error);
        toast.error('Failed to load exam: ' + (error as Error).message);
        throw error;
      }
    },
    enabled: !!examId && isAuthenticated,
  });

  // Transform API question format to Question format
  const transformApiQuestionToQuestion = (apiQ: any, number: number, parentId?: string): Question => {
    const subQuestions = (apiQ.subQuestions || []).map((sub: any, idx: number) =>
      transformApiQuestionToQuestion(sub, sub.number ?? idx + 1, apiQ.id)
    );
    return {
      id: apiQ.id || crypto.randomUUID(),
      number: number,
      text: apiQ.text || '',
      richContent: apiQ.richContent || null,
      questionType: subQuestions.length > 0 ? 'multi-part' : (apiQ.questionType || 'standard'),
      points: apiQ.points || 10,
      subQuestions,
      attachments: apiQ.attachments || [],
      embeddedContent: apiQ.embeddedContent || [],
      theories: apiQ.theories || [],
      goldSolutionSteps: (apiQ.goldSolutionSteps || []).map((step: any) => ({
        stepNumber: step.stepNumber || 0,
        description: step.description || '',
        expression: step.expression || '',
        latex: step.latex || '',
        points: step.points || 5,
        required: step.required !== false,
      })),
      finalAnswer: apiQ.finalAnswer || '',
      finalAnswerLatex: apiQ.finalAnswerLatex || '',
      outlineLevel: apiQ.outlineLevel || 1,
      outlineTitle: apiQ.outlineTitle ?? '',
      parentQuestionId: parentId,
    };
  };

  // Load exam data when editing
  useEffect(() => {
    if (examData && isEditMode) {
      setIsLoading(true);
      setTitle(examData.title || '');
      setDescription(examData.description || '');
      setCourseId(examData.courseId || '');
      setDuration(120);
      setDurationInput(String(examData.duration ?? 120));

      const transformedQuestions = (examData.questions || []).map((q: any, idx: number) =>
        transformApiQuestionToQuestion(q, q.number ?? idx + 1)
      );
      setQuestions(transformedQuestions);
      const expandWithSubs: string[] = [];
      const collectExpand = (qs: Question[]) => {
        for (const q of qs) {
          if (q.subQuestions?.length) {
            expandWithSubs.push(q.id);
            collectExpand(q.subQuestions);
          }
        }
      };
      collectExpand(transformedQuestions);
      if (expandWithSubs.length > 0) {
        setInitialExpandedQuestionIds(expandWithSubs);
      }
      setDueDate(isoToDatetimeLocal(examData.dueDate));
      setIsLoading(false);
    }
  }, [examData, isEditMode]);

  useEffect(() => {
    if (!isEditMode && courseIdFromQuery) {
      setCourseId(courseIdFromQuery);
    }
  }, [courseIdFromQuery, isEditMode]);

  const handleUploadExam = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!uploadFile || !courseId) {
      toast.error('Please select a course and upload a file');
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('course_id', courseId);
      if (dueDate) {
        formData.append('due_date', dueDate);
      }

      const result = await examsAPI.upload(formData);
      toast.success(`Exam uploaded successfully! ${result.questions_found} questions found.`);
      if (result.exam_id) {
        navigate(`/exams/${result.exam_id}/edit`);
      } else {
        navigate('/exams');
      }
    } catch (error: any) {
      toast.error(error.message || 'Failed to upload exam');
    } finally {
      setIsUploading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!title || !courseId || questions.length === 0) {
      toast.error('Please fill in all required fields and add at least one question');
      return;
    }

    setIsSaving(true);
    try {
      const examData = {
        title,
        description,
        courseId,
        duration: parseInt(durationInput, 10) || duration,
        dueDate: dueDate.trim() ? new Date(dueDate).toISOString() : null,
        questions: questions.map((q) => ({
          number: q.number,
          text: q.text,
          points: q.points,
          questionType: q.questionType,
          richContent: q.richContent,
          outlineLevel: q.outlineLevel,
          outlineTitle: (q.outlineTitle || '').trim() || undefined,
          parentQuestionId: q.parentQuestionId,
          subQuestions: mapSubQuestionsForSave(q.subQuestions ?? [], q.id),
          attachments: q.attachments,
          embeddedContent: q.embeddedContent,
          theories: q.theories,
          goldSolutionSteps: mapGoldStepsForSave(q.goldSolutionSteps),
          finalAnswer: q.finalAnswer,
          finalAnswerLatex: q.finalAnswerLatex,
        })),
      };

      if (isEditMode && examId) {
        await examsAPI.update(examId, examData);
        toast.success('Exam updated successfully!');
      } else {
        await examsAPI.create(examData);
        toast.success('Exam created successfully!');
      }
      navigate('/exams');
    } catch (error: any) {
      toast.error(error.message || 'Failed to create exam');
    } finally {
      setIsSaving(false);
    }
  };

  const totalPoints = questions.reduce((sum, q) => {
    const subPoints = q.subQuestions?.reduce((subSum, sub) => subSum + sub.points, 0) || 0;
    return sum + q.points + subPoints;
  }, 0);

  const selectedCourse = courses.find((c: { id: string }) => c.id === courseId) as
    | { code: string; name: string }
    | undefined;

  if ((isLoading || examLoading) && isEditMode) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-muted-foreground">
        <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
        <p className="text-sm font-medium">Loading exam…</p>
      </div>
    );
  }

  const isManualUi = isEditMode || creationMode === 'manual';

  const courseSelectBlock = (selectId: string) =>
    coursesLoading ? (
      <p className="text-sm text-muted-foreground">Loading courses…</p>
    ) : coursesError ? (
      <div className="space-y-2">
        <p className="text-sm text-red-600 dark:text-red-400">
          Error loading courses. Please refresh the page.
        </p>
        <Button type="button" variant="outline" size="sm" onClick={() => window.location.reload()}>
          Refresh
        </Button>
      </div>
    ) : courses.length === 0 ? (
      <div className="space-y-2">
        <p className="text-sm text-red-600 dark:text-red-400">No courses available. Create a course first.</p>
        <Button type="button" variant="outline" size="sm" onClick={() => navigate('/courses/new')}>
          Create course
        </Button>
      </div>
    ) : (
      <Select value={courseId} onValueChange={setCourseId}>
        <SelectTrigger id={selectId} className="h-11 bg-background">
          <SelectValue placeholder="Select a course" />
        </SelectTrigger>
        <SelectContent className="z-50">
          {courses.map((course: { id: string; code: string; name: string }) => (
            <SelectItem key={course.id} value={course.id}>
              {course.code} — {course.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );

  const examDetailsFields = (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white shadow-sm">
          <ListChecks className="h-5 w-5" />
        </span>
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Exam details</h2>
          <p className="text-sm text-muted-foreground">
            Title, course, duration, and due date are shown to students where relevant (e.g. My exams).
          </p>
        </div>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="title">Exam title</Label>
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Midterm — Mechanics"
            className="h-11 bg-background"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="course">Course</Label>
          {courseSelectBlock('course')}
        </div>
      </div>

      <div className="grid gap-5 sm:grid-cols-[1fr_140px]">
        <div className="space-y-2">
          <Label htmlFor="description">Description (optional)</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What students should know before starting…"
            rows={3}
            className="min-h-[88px] resize-y bg-background"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="duration">Duration (min)</Label>
          <Input
            id="duration"
            type="text"
            inputMode="numeric"
            placeholder="120"
            value={durationInput}
            onChange={(e) => setDurationInput(e.target.value.replace(/\D/g, '').slice(0, 4))}
            onBlur={() => {
              const n = parseInt(durationInput, 10);
              if (!Number.isNaN(n) && n >= 1) {
                setDuration(n);
                setDurationInput(String(n));
              } else {
                setDurationInput(String(duration));
              }
            }}
            className="h-11 bg-background"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="due-date-details">Due date and time (optional)</Label>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Input
            id="due-date-details"
            type="datetime-local"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            className="h-11 max-w-md bg-background"
          />
          {dueDate ? (
            <Button type="button" variant="ghost" size="sm" className="shrink-0 self-start sm:self-center" onClick={() => setDueDate('')}>
              Clear due date
            </Button>
          ) : null}
        </div>
        <p className="text-xs text-muted-foreground">
          Shown on student My exams. Leave empty so the exam has no deadline (overdue rules only apply when a date is set).
        </p>
      </div>

      {isEditMode && examId ? (
        <AnswerKeyUpload
          examId={examId}
          examTitle={title}
          onApplied={() => {
            queryClient.invalidateQueries({ queryKey: ['exam', examId] });
          }}
        />
      ) : null}
    </div>
  );

  return (
    <div className="flex min-h-[calc(100vh-4.5rem)] w-full flex-col bg-muted/30 dark:bg-muted/10">
      {/* Hidden form so Save works from any workspace tab (fields are controlled in React state). */}
      {isManualUi && <form id="exam-manual-form" hidden onSubmit={handleSubmit} aria-hidden="true" />}

      <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 pb-10 pt-3 sm:px-6">
        {/* Workspace chrome */}
        <div
          className={cn(
            'sticky top-0 z-20 -mx-4 mb-4 border-b border-border/70 bg-background/90 px-4 py-3 backdrop-blur-md sm:-mx-6 sm:px-6',
            'supports-[backdrop-filter]:bg-background/75'
          )}
        >
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="mt-0.5 shrink-0"
                onClick={() => navigate('/exams')}
                aria-label="Back to exams"
              >
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <div className="min-w-0 space-y-0.5">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {isEditMode ? 'Editing exam' : 'New exam'}
                </p>
                <h1 className="truncate text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
                  {title.trim() || 'Untitled exam'}
                </h1>
                {selectedCourse && (
                  <p className="truncate text-xs text-muted-foreground">
                    {selectedCourse.code} · {selectedCourse.name}
                  </p>
                )}
              </div>
            </div>

            {isManualUi && (
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
                <Tabs
                  value={workspaceTab}
                  onValueChange={(v) => setWorkspaceTab(v as WorkspaceTab)}
                  className="w-full sm:w-auto"
                >
                  <TabsList className="grid h-10 w-full grid-cols-3 rounded-xl border border-stone-200/90 bg-stone-100/80 p-1 dark:border-stone-800 dark:bg-stone-900/70 sm:inline-flex sm:w-auto">
                    <TabsTrigger
                      value="build"
                      className="gap-1.5 rounded-lg px-3 text-xs font-medium sm:text-sm data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm"
                    >
                      <Sparkles className="h-3.5 w-3.5 shrink-0 opacity-80" />
                      Build
                    </TabsTrigger>
                    <TabsTrigger
                      value="details"
                      className="gap-1.5 rounded-lg px-3 text-xs font-medium sm:text-sm data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm"
                    >
                      <ClipboardList className="h-3.5 w-3.5 shrink-0 opacity-80" />
                      Details
                    </TabsTrigger>
                    <TabsTrigger
                      value="preview"
                      className="gap-1.5 rounded-lg px-3 text-xs font-medium sm:text-sm data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm"
                    >
                      <Eye className="h-3.5 w-3.5 shrink-0 opacity-80" />
                      Preview
                    </TabsTrigger>
                  </TabsList>
                </Tabs>

                <div className="flex flex-wrap items-center justify-end gap-3">
                  <div className="flex items-center gap-4 rounded-xl border border-stone-200/90 bg-card/90 px-4 py-2 shadow-sm dark:border-stone-800">
                    <div className="text-center">
                      <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Points</p>
                      <p className="text-lg font-bold tabular-nums text-emerald-700 dark:text-emerald-400">
                        {totalPoints}
                      </p>
                    </div>
                    <Separator orientation="vertical" className="h-9 bg-stone-200 dark:bg-stone-700" />
                    <div className="text-center">
                      <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Questions</p>
                      <p className="text-lg font-bold tabular-nums">{questions.length}</p>
                    </div>
                  </div>
                  <Button
                    type="submit"
                    form="exam-manual-form"
                    size="lg"
                    className="shrink-0 px-6 shadow-md"
                    disabled={isSaving || isLoading}
                  >
                    <Save className="mr-2 h-4 w-4" />
                    {isSaving ? (isEditMode ? 'Updating…' : 'Saving…') : isEditMode ? 'Update exam' : 'Save exam'}
                  </Button>
                </div>
              </div>
            )}
          </div>

          {!isEditMode && (
            <div className="mt-4 max-w-lg">
              <Tabs
                value={creationMode}
                onValueChange={(v) => setCreationMode(v as 'manual' | 'upload')}
              >
                <TabsList className="grid h-10 w-full grid-cols-2 rounded-xl border border-stone-200/80 bg-stone-100/70 p-1 dark:border-stone-800 dark:bg-stone-900/60">
                  <TabsTrigger
                    value="manual"
                    className="gap-2 rounded-lg text-sm data-[state=active]:bg-card data-[state=active]:shadow-sm"
                  >
                    <FileText className="h-4 w-4 shrink-0" />
                    Manual
                  </TabsTrigger>
                  <TabsTrigger
                    value="upload"
                    className="gap-2 rounded-lg text-sm data-[state=active]:bg-card data-[state=active]:shadow-sm"
                  >
                    <Upload className="h-4 w-4 shrink-0" />
                    Upload file
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          )}
        </div>

        {creationMode === 'upload' && !isEditMode ? (
          <form onSubmit={handleUploadExam}>
            <section
              className={cn(
                'rounded-2xl border border-emerald-200/50 bg-gradient-to-br from-emerald-50/40 via-card to-stone-50/30 p-6 shadow-sm',
                'dark:border-emerald-900/35 dark:from-emerald-950/20 dark:via-card dark:to-stone-950/20 sm:p-8'
              )}
            >
              <div className="mb-6 flex items-start gap-3">
                <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm">
                  <Upload className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="text-lg font-semibold tracking-tight">Upload from file</h2>
                  <p className="text-sm text-muted-foreground">
                    We parse questions from text or PDF. Gold answers can stay in the same file, or you can upload a
                    separate answer key later from the exam page.
                  </p>
                </div>
              </div>

              <div className="grid gap-8 lg:grid-cols-[1fr_minmax(240px,280px)]">
                <div className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="upload-course">Course</Label>
                    {coursesLoading ? (
                      <p className="text-sm text-muted-foreground">Loading courses…</p>
                    ) : coursesError ? (
                      <div className="space-y-2">
                        <p className="text-sm text-red-600 dark:text-red-400">
                          Error loading courses. Please refresh the page.
                        </p>
                        <Button type="button" variant="outline" size="sm" onClick={() => window.location.reload()}>
                          Refresh
                        </Button>
                      </div>
                    ) : courses.length === 0 ? (
                      <div className="space-y-2">
                        <p className="text-sm text-red-600 dark:text-red-400">
                          No courses available. Create a course first.
                        </p>
                        <Button type="button" variant="outline" size="sm" onClick={() => navigate('/courses/new')}>
                          Create course
                        </Button>
                      </div>
                    ) : (
                      <Select value={courseId} onValueChange={setCourseId}>
                        <SelectTrigger id="upload-course" className="h-11 bg-background">
                          <SelectValue placeholder="Select a course" />
                        </SelectTrigger>
                        <SelectContent className="z-50">
                          {courses.map((course: { id: string; code: string; name: string }) => (
                            <SelectItem key={course.id} value={course.id}>
                              {course.code} — {course.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="exam-file">Exam file</Label>
                    <Input
                      id="exam-file"
                      type="file"
                      accept=".txt,.pdf,.jpg,.jpeg,.png"
                      onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                      className="h-11 cursor-pointer bg-background file:mr-3 file:rounded-md file:border-0 file:bg-violet-100 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-violet-900 hover:file:bg-violet-200/80 dark:file:bg-violet-950 dark:file:text-violet-100"
                    />
                    <p className="text-xs text-muted-foreground">.txt works best; .pdf and images are supported.</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="due-date">Due date (optional)</Label>
                    <Input
                      id="due-date"
                      type="datetime-local"
                      value={dueDate}
                      onChange={(e) => setDueDate(e.target.value)}
                      className="h-11 bg-background"
                    />
                  </div>

                  <div className="rounded-xl border border-stone-200/80 bg-stone-50/50 p-4 dark:border-stone-800 dark:bg-stone-950/40">
                    <h3 className="mb-2 text-sm font-semibold text-stone-900 dark:text-stone-100">Format tips</h3>
                    <ul className="space-y-1.5 text-sm text-muted-foreground">
                      <li>Label questions with &quot;Question 1:&quot; or &quot;Q1:&quot;</li>
                      <li>Add points with [5 points]</li>
                      <li>Gold solutions are optional here—you can upload them separately later</li>
                      <li>If included: use &quot;Gold Solution:&quot; or &quot;Expected Answer:&quot;</li>
                    </ul>
                    <a
                      href="/exam-template.txt"
                      download
                      className="mt-3 inline-block text-sm font-medium text-violet-700 hover:underline dark:text-violet-400"
                    >
                      Download template file
                    </a>
                  </div>
                </div>

                <Card className="flex flex-col border-stone-200/90 shadow-sm dark:border-stone-800">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Import</CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-1 flex-col gap-4">
                    <Button
                      type="submit"
                      size="lg"
                      className="w-full shadow-sm"
                      disabled={isUploading || !uploadFile || !courseId}
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      {isUploading ? 'Uploading…' : 'Upload & parse'}
                    </Button>
                    {uploadFile ? (
                      <p className="text-center text-xs text-muted-foreground">
                        Selected: <span className="font-medium text-foreground">{uploadFile.name}</span>
                      </p>
                    ) : (
                      <p className="text-center text-xs text-muted-foreground">No file selected yet</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </section>
          </form>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-stone-200/80 bg-card shadow-sm dark:border-stone-800">
            {workspaceTab === 'details' && (
              <div className="flex-1 overflow-y-auto p-6 sm:p-8">{examDetailsFields}</div>
            )}

            {workspaceTab === 'build' && (
              <div className="flex min-h-[min(78vh,880px)] flex-1 flex-col overflow-hidden">
                <div className="border-b border-stone-200/80 bg-stone-50/80 px-4 py-3 dark:border-stone-800 dark:bg-stone-950/40 sm:px-6">
                  <p className="text-sm font-medium text-foreground">Question editor</p>
                  <p className="text-xs text-muted-foreground">
                    Outline on the left, full editor on the right. Open <span className="font-medium">Preview</span> to
                    see the student-facing view.
                  </p>
                </div>
                <div className="min-h-0 flex-1">
                  <QuestionBuilder
                    questions={questions}
                    onQuestionsChange={setQuestions}
                    enableInlinePreview={false}
                    initialExpandedIds={initialExpandedQuestionIds}
                  />
                </div>
              </div>
            )}

            {workspaceTab === 'preview' && (
              <div className="flex flex-1 flex-col overflow-hidden">
                <div className="border-b border-stone-200/80 bg-stone-50/80 px-4 py-3 dark:border-stone-800 dark:bg-stone-950/40 sm:px-6">
                  <p className="text-sm font-medium text-foreground">Student preview</p>
                  <p className="text-xs text-muted-foreground">
                    Approximate layout of prompts and resources—grading fields are hidden.
                  </p>
                </div>
                <div className="flex-1 overflow-y-auto p-4 sm:p-6">
                  {questions.length === 0 ? (
                    <div className="flex min-h-[240px] flex-col items-center justify-center rounded-xl border border-dashed border-stone-300/90 bg-muted/20 px-6 py-12 text-center dark:border-stone-700">
                      <Eye className="mb-3 h-10 w-10 text-muted-foreground/60" />
                      <p className="font-medium text-foreground">Nothing to preview yet</p>
                      <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                        Add questions in the Build tab, then return here to review how they read for students.
                      </p>
                      <Button type="button" variant="secondary" className="mt-6" onClick={() => setWorkspaceTab('build')}>
                        Go to Build
                      </Button>
                    </div>
                  ) : (
                    <div className="mx-auto max-w-3xl rounded-xl border border-stone-200/70 bg-background p-4 shadow-sm dark:border-stone-800 sm:p-6">
                      <PreviewPanel questions={questions} activeQuestionId={null} />
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
