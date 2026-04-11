import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
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
import { Save, ArrowLeft, Upload, FileText, ListChecks, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { QuestionBuilder, Question } from '@/components/exam-builder/QuestionBuilder';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

export default function CreateExam() {
  const navigate = useNavigate();
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
    return {
      id: apiQ.id || crypto.randomUUID(),
      number: number,
      text: apiQ.text || '',
      richContent: apiQ.richContent || null,
      questionType: apiQ.questionType || 'standard',
      points: apiQ.points || 10,
      subQuestions: (apiQ.subQuestions || []).map((sub: any, idx: number) =>
        transformApiQuestionToQuestion(sub, idx + 1, apiQ.id)
      ),
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
      
      // Transform questions
      const transformedQuestions = (examData.questions || []).map((q: any, idx: number) =>
        transformApiQuestionToQuestion(q, idx + 1)
      );
      setQuestions(transformedQuestions);
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
      navigate('/exams');
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
      // Transform questions to API format
      const examData = {
        title,
        description,
        courseId,
        duration: parseInt(durationInput, 10) || duration,
        questions: questions.map((q, idx) => ({
          number: idx + 1,
          text: q.text,
          points: q.points,
          questionType: q.questionType,
          richContent: q.richContent,
          outlineLevel: q.outlineLevel,
          parentQuestionId: q.parentQuestionId,
          subQuestions: q.subQuestions.map((sub, subIdx) => ({
            number: subIdx + 1,
            text: sub.text,
            points: sub.points,
            questionType: sub.questionType || 'standard',
            richContent: sub.richContent,
            outlineLevel: sub.outlineLevel || 2,
            parentQuestionId: sub.parentQuestionId || q.id,
            goldSolutionSteps: sub.goldSolutionSteps.map((step, stepIdx) => ({
              stepNumber: stepIdx + 1,
              description: step.description,
              expression: step.expression,
              latex: step.latex,
              points: step.points,
              required: step.required,
            })),
            finalAnswer: sub.finalAnswer,
            finalAnswerLatex: sub.finalAnswerLatex,
          })),
          attachments: q.attachments,
          embeddedContent: q.embeddedContent,
          theories: q.theories,
          goldSolutionSteps: q.goldSolutionSteps.map((step, stepIdx) => ({
            stepNumber: stepIdx + 1,
            description: step.description,
            expression: step.expression,
            latex: step.latex,
            points: step.points,
            required: step.required,
          })),
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

  if ((isLoading || examLoading) && isEditMode) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-muted-foreground">
        <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
        <p className="text-sm font-medium">Loading exam…</p>
      </div>
    );
  }

  const isManualUi = isEditMode || creationMode === 'manual';

  return (
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-6xl flex-col gap-6 px-4 pb-12 pt-1 sm:px-6">
        {/* Hero */}
        <header
          className={cn(
            'rounded-2xl border border-violet-200/70 bg-gradient-to-br from-violet-50/90 via-white to-stone-50/50 p-6 shadow-sm',
            'dark:border-violet-900/40 dark:from-violet-950/35 dark:via-card dark:to-stone-950/25 sm:p-7'
          )}
        >
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
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
              <div className="min-w-0 space-y-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-violet-700 dark:text-violet-400">
                  {isEditMode ? 'Editing exam' : 'Exams'}
                </p>
                <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                  {isEditMode ? 'Edit exam' : 'Create exam'}
                </h1>
                <p className="max-w-2xl text-[1.02rem] leading-relaxed text-muted-foreground">
                  {isEditMode
                    ? 'Update details and questions, then save to publish changes.'
                    : 'Set up the exam shell, then build questions—or upload a file to import structure.'}
                </p>
              </div>
            </div>

            {isManualUi && (
              <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row sm:items-stretch sm:justify-end">
                <div className="flex items-center justify-center gap-6 rounded-xl border border-stone-200/90 bg-white/90 px-5 py-3 shadow-sm dark:border-stone-800 dark:bg-card/90">
                  <div className="text-center">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      Total points
                    </p>
                    <p className="text-2xl font-bold tabular-nums text-emerald-700 dark:text-emerald-400">
                      {totalPoints}
                    </p>
                  </div>
                  <Separator orientation="vertical" className="h-10 bg-stone-200 dark:bg-stone-700" />
                  <div className="text-center">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      Questions
                    </p>
                    <p className="text-2xl font-bold tabular-nums text-stone-900 dark:text-stone-100">
                      {questions.length}
                    </p>
                  </div>
                </div>
                <Button
                  type="submit"
                  form="exam-manual-form"
                  size="lg"
                  className="h-[52px] shrink-0 px-8 shadow-md sm:min-w-[160px]"
                  disabled={isSaving || isLoading}
                >
                  <Save className="mr-2 h-4 w-4" />
                  {isSaving
                    ? isEditMode
                      ? 'Updating…'
                      : 'Saving…'
                    : isEditMode
                      ? 'Update exam'
                      : 'Save exam'}
                </Button>
              </div>
            )}
          </div>

          {!isEditMode && (
            <div className="mt-6">
              <Tabs
                value={creationMode}
                onValueChange={(v) => setCreationMode(v as 'manual' | 'upload')}
              >
                <TabsList className="grid h-11 w-full max-w-lg grid-cols-2 rounded-xl border border-stone-200/80 bg-stone-100/70 p-1 dark:border-stone-800 dark:bg-stone-900/60">
                  <TabsTrigger
                    value="manual"
                    className="gap-2 rounded-lg data-[state=active]:bg-white data-[state=active]:text-violet-900 data-[state=active]:shadow-sm dark:data-[state=active]:bg-stone-950 dark:data-[state=active]:text-violet-100"
                  >
                    <FileText className="h-4 w-4 shrink-0" />
                    Manual
                  </TabsTrigger>
                  <TabsTrigger
                    value="upload"
                    className="gap-2 rounded-lg data-[state=active]:bg-white data-[state=active]:text-violet-900 data-[state=active]:shadow-sm dark:data-[state=active]:bg-stone-950 dark:data-[state=active]:text-violet-100"
                  >
                    <Upload className="h-4 w-4 shrink-0" />
                    Upload file
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          )}
        </header>

        {creationMode === 'upload' && !isEditMode ? (
          <form onSubmit={handleUploadExam}>
            <section
              className={cn(
                'rounded-2xl border border-emerald-200/50 bg-gradient-to-br from-emerald-50/40 via-white to-stone-50/30 p-6 shadow-sm',
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
                    We parse questions and solution hints from text or PDF. You can edit everything after import.
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
                    <p className="text-xs text-muted-foreground">
                      .txt works best; .pdf and images are supported.
                    </p>
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
                    <h3 className="mb-2 text-sm font-semibold text-stone-900 dark:text-stone-100">
                      Format tips
                    </h3>
                    <ul className="space-y-1.5 text-sm text-muted-foreground">
                      <li>Label questions with &quot;Question 1:&quot; or &quot;Q1:&quot;</li>
                      <li>Add points with [5 points]</li>
                      <li>Use &quot;Gold Solution:&quot; or &quot;Expected Answer:&quot; for model answers</li>
                      <li>Number steps as &quot;Step 1:&quot; or &quot;1.&quot;</li>
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
          <>
            <form id="exam-manual-form" onSubmit={handleSubmit} className="space-y-6">
              <section
                className={cn(
                  'rounded-2xl border border-stone-200/80 bg-gradient-to-br from-stone-50/60 via-white to-violet-50/20 p-6 shadow-sm',
                  'dark:border-stone-800 dark:from-stone-950/40 dark:via-card dark:to-violet-950/15 sm:p-8'
                )}
              >
                <div className="mb-6 flex items-start gap-3">
                  <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white shadow-sm">
                    <ListChecks className="h-5 w-5" />
                  </span>
                  <div>
                    <h2 className="text-lg font-semibold tracking-tight">Exam details</h2>
                    <p className="text-sm text-muted-foreground">
                      Title, course, and timing appear to students before they start.
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
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="course">Course</Label>
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
                      <Select value={courseId} onValueChange={setCourseId} required>
                        <SelectTrigger id="course" className="h-11 bg-background">
                          <SelectValue placeholder="Select a course" />
                        </SelectTrigger>
                        <SelectContent className="z-50">
                          {courses.map((course) => (
                            <SelectItem key={course.id} value={course.id}>
                              {course.code} — {course.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                </div>

                <div className="mt-5 grid gap-5 sm:grid-cols-[1fr_140px]">
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
              </section>
            </form>

            {isManualUi && (
              <section className="overflow-hidden rounded-2xl border border-violet-200/45 bg-card shadow-sm dark:border-violet-900/40">
                <div className="border-b border-stone-200/90 bg-stone-50/90 px-4 py-3.5 sm:px-6 dark:border-stone-800 dark:bg-stone-950/50">
                  <h2 className="font-semibold text-stone-900 dark:text-stone-100">Questions</h2>
                  <p className="text-sm text-muted-foreground">
                    Outline on the left, editor on the right—add parts and model solutions for grading.
                  </p>
                </div>
                <div className="min-h-[480px]">
                  <QuestionBuilder questions={questions} onQuestionsChange={setQuestions} />
                </div>
              </section>
            )}
          </>
        )}
      </div>
  );
}