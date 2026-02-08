import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
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
import { Save, ArrowLeft, ChevronLeft, ChevronRight, ChevronUp, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import { QuestionBuilder, Question } from '@/components/exam-builder/QuestionBuilder';

export default function CreateExam() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [searchParams] = useSearchParams();
  const examId = searchParams.get('examId');
  const isEditMode = !!examId;
  
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [courseId, setCourseId] = useState('');
  const [duration, setDuration] = useState(120);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [topbarCollapsed, setTopbarCollapsed] = useState(false);

  // Fetch courses
  const { data: courses = [] } = useQuery({
    queryKey: ['courses'],
    queryFn: () => coursesAPI.getAll(),
    enabled: !!token,
  });

  // Fetch exam data if editing
  const { data: examData } = useQuery({
    queryKey: ['exam', examId],
    queryFn: () => examsAPI.getById(examId!),
    enabled: !!examId && !!token,
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
      setDuration(examData.duration || 120);
      
      // Transform questions
      const transformedQuestions = (examData.questions || []).map((q: any, idx: number) =>
        transformApiQuestionToQuestion(q, idx + 1)
      );
      setQuestions(transformedQuestions);
      setIsLoading(false);
    }
  }, [examData, isEditMode]);

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
        duration,
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

  if (isLoading && isEditMode) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <p>Loading exam data...</p>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="flex flex-col h-[calc(100vh-120px)] relative">
        {/* Collapse Toggle Button */}
        <Button
          variant="outline"
          size="icon"
          className="fixed top-4 right-4 z-50 bg-background shadow-lg"
          onClick={() => setTopbarCollapsed(!topbarCollapsed)}
          title={topbarCollapsed ? 'Show Header' : 'Hide Header'}
        >
          {topbarCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
        </Button>

        {/* Header */}
        <div className={`flex-none border-b bg-background transition-all duration-300 overflow-hidden ${topbarCollapsed ? 'max-h-0 p-0' : 'p-6'}`}>
          <form onSubmit={handleSubmit}>
            <div className="flex items-start justify-between gap-6">
              <div className="flex-1 max-w-2xl space-y-4">
                <div className="flex items-center gap-3">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => navigate('/exams')}
                  >
                    <ArrowLeft className="h-4 w-4" />
                  </Button>
          <div>
                    <h1 className="text-3xl font-bold tracking-tight">
                      {isEditMode ? 'Edit Exam' : 'Create Exam'}
                    </h1>
                    <p className="text-muted-foreground mt-1">
                      {isEditMode
                        ? 'Update your exam questions and solutions'
                        : 'Enhanced question builder with scientific tools'}
                    </p>
          </div>
        </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="title">Exam Title</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g., Midterm Exam - Physics"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="course">Course</Label>
                <Select value={courseId} onValueChange={setCourseId} required>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a course" />
                  </SelectTrigger>
                  <SelectContent>
                        {courses.map((course) => (
                      <SelectItem key={course.id} value={course.id}>
                        {course.code} - {course.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="col-span-2 space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Exam description"
                rows={2}
              />
            </div>
                  <div className="space-y-2">
                    <Label htmlFor="duration">Duration (minutes)</Label>
                    <Input
                      id="duration"
                      type="number"
                      value={duration}
                      onChange={(e) => setDuration(parseInt(e.target.value) || 120)}
                      min={1}
                    />
                  </div>
                </div>
                </div>

              <div className="flex-none space-y-3">
                <Card className="p-4">
                  <div className="text-center space-y-1">
                    <p className="text-sm text-muted-foreground">Total Points</p>
                    <p className="text-3xl font-bold">{totalPoints}</p>
                    <p className="text-xs text-muted-foreground">
                      {questions.length} {questions.length === 1 ? 'question' : 'questions'}
                    </p>
                  </div>
                </Card>
                <Button type="submit" size="lg" className="w-full" disabled={isSaving || isLoading}>
                  <Save className="h-4 w-4 mr-2" />
                  {isSaving
                    ? isEditMode
                      ? 'Updating...'
                      : 'Creating...'
                    : isEditMode
                    ? 'Update Exam'
                    : 'Save Exam'}
                              </Button>
                          </div>
                        </div>
          </form>
                </div>

        {/* Question Builder */}
        <div className="flex-1 overflow-hidden">
          <QuestionBuilder
            questions={questions}
            onQuestionsChange={setQuestions}
          />
        </div>
      </div>
    </DashboardLayout>
  );
}