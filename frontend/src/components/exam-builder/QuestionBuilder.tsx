import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus, Eye, ChevronLeft, ChevronRight, Sparkles } from 'lucide-react';
import { QuestionList } from './QuestionList';
import { QuestionEditor } from './QuestionEditor';
import { PreviewPanel } from './PreviewPanel';
import { toast } from 'sonner';

export interface Question {
  id: string;
  number: number;
  text: string;
  richContent?: any;
  questionType: 'standard' | 'multi-part';
  points: number;
  subQuestions: Question[];
  attachments: Attachment[];
  embeddedContent: EmbeddedContentItem[];
  theories: Theory[];
  goldSolutionSteps: GoldStep[];
  finalAnswer: string;
  finalAnswerLatex: string;
  outlineLevel: number;
  parentQuestionId?: string;
}

export interface Attachment {
  id: string;
  attachmentType: 'image' | 'scan' | 'document';
  filePath: string;
  filename: string;
  fileSize?: number;
  mimeType?: string;
}

export interface EmbeddedContentItem {
  id: string;
  contentType: string;
  contentData: any;
  positionData?: any;
}

export interface Theory {
  id: string;
  name: string;
  value: string;
  unit?: string;
  description?: string;
  category?: string;
}

export interface GoldStep {
  stepNumber: number;
  description: string;
  expression: string;
  latex: string;
  points: number;
  required: boolean;
}

interface QuestionBuilderProps {
  questions: Question[];
  onQuestionsChange: (questions: Question[]) => void;
}

export function QuestionBuilder({ questions, onQuestionsChange }: QuestionBuilderProps) {
  const [activeQuestionId, setActiveQuestionId] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [expandedQuestions, setExpandedQuestions] = useState<Set<string>>(new Set());
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const addQuestion = () => {
    const newQuestion: Question = {
      id: crypto.randomUUID(),
      number: questions.length + 1,
      text: '',
      questionType: 'standard',
      points: 10,
      subQuestions: [],
      attachments: [],
      embeddedContent: [],
      theories: [],
      goldSolutionSteps: [],
      finalAnswer: '',
      finalAnswerLatex: '',
      outlineLevel: 1,
    };
    onQuestionsChange([...questions, newQuestion]);
    setActiveQuestionId(newQuestion.id);
    toast.success('Question added');
  };

  const addSubQuestion = (parentId: string) => {
    if (!parentId) {
      toast.error('No parent question selected');
      return;
    }

    let newSubId: string | null = null;
    const findAndAddSub = (qs: Question[]): Question[] => {
      return qs.map(q => {
        if (q.id === parentId) {
          const newSub: Question = {
            id: crypto.randomUUID(),
            number: q.subQuestions.length + 1,
            text: '',
            questionType: 'standard',
            points: 5,
            subQuestions: [],
            attachments: [],
            embeddedContent: [],
            theories: [],
            goldSolutionSteps: [],
            finalAnswer: '',
            finalAnswerLatex: '',
            outlineLevel: q.outlineLevel + 1,
            parentQuestionId: parentId,
          };
          newSubId = newSub.id;
          return {
            ...q,
            questionType: 'multi-part',
            subQuestions: [...q.subQuestions, newSub]
          };
        }
        if (q.subQuestions.length > 0) {
          return { ...q, subQuestions: findAndAddSub(q.subQuestions) };
        }
        return q;
      });
    };
    
    const updatedQuestions = findAndAddSub(questions);
    
    if (!newSubId) {
      toast.error('Could not find parent question');
      return;
    }
    
    onQuestionsChange(updatedQuestions);
    
    // Automatically expand parent and select the newly added sub-question
    const newExpanded = new Set(expandedQuestions);
    newExpanded.add(parentId);
    setExpandedQuestions(newExpanded);
    setActiveQuestionId(newSubId);
    toast.success('Sub-question added');
  };

  const updateQuestion = (updated: Question) => {
    const updateInTree = (qs: Question[]): Question[] => {
      return qs.map(q => {
        if (q.id === updated.id) {
          return updated;
        }
        if (q.subQuestions.length > 0) {
          return { ...q, subQuestions: updateInTree(q.subQuestions) };
        }
        return q;
      });
    };
    onQuestionsChange(updateInTree(questions));
  };

  const deleteQuestion = (id: string) => {
    const deleteFromTree = (qs: Question[]): Question[] => {
      return qs
        .filter(q => q.id !== id)
        .map(q => ({
          ...q,
          subQuestions: deleteFromTree(q.subQuestions)
        }));
    };
    onQuestionsChange(deleteFromTree(questions));
    if (activeQuestionId === id) {
      setActiveQuestionId(null);
    }
    toast.success('Question deleted');
  };

  const findQuestion = (id: string, qs: Question[] = questions): Question | undefined => {
    for (const q of qs) {
      if (q.id === id) return q;
      if (q.subQuestions.length > 0) {
        const found = findQuestion(id, q.subQuestions);
        if (found) return found;
      }
    }
    return undefined;
  };

  const activeQuestion = activeQuestionId ? findQuestion(activeQuestionId) : null;

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200/80 bg-gradient-to-r from-stone-50/90 to-violet-50/20 px-4 py-3 dark:border-stone-800 dark:from-stone-950/80 dark:to-violet-950/20 sm:px-5">
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={addQuestion} size="sm" className="shadow-sm">
            <Plus className="mr-2 h-4 w-4" />
            Add question
          </Button>
          <Button
            onClick={() => setShowPreview(!showPreview)}
            variant="outline"
            size="sm"
            className="border-stone-200 bg-background/80 dark:border-stone-700"
          >
            <Eye className="mr-2 h-4 w-4" />
            {showPreview ? 'Hide' : 'Show'} preview
          </Button>
        </div>
        <div className="text-sm tabular-nums text-muted-foreground">
          <span className="font-medium text-stone-700 dark:text-stone-200">{questions.length}</span>{' '}
          {questions.length === 1 ? 'question' : 'questions'}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Sidebar Toggle Button */}
        <Button
          variant="ghost"
          size="icon"
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 h-8 w-8 bg-background border border-r-0 rounded-r-lg shadow-sm"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          title={sidebarCollapsed ? 'Show Sidebar' : 'Hide Sidebar'}
        >
          {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>

        {/* Question List - Outline */}
        <div
          className={`overflow-y-auto border-r border-stone-200/70 bg-stone-50/40 transition-all duration-300 dark:border-stone-800 dark:bg-stone-950/30 ${sidebarCollapsed ? 'w-0 overflow-hidden' : 'w-64'}`}
        >
          {!sidebarCollapsed && (
            <QuestionList
              questions={questions}
              activeId={activeQuestionId}
              expandedIds={expandedQuestions}
              onSelect={setActiveQuestionId}
              onAddSubQuestion={addSubQuestion}
              onDelete={deleteQuestion}
              onToggleExpand={(id) => {
                const newExpanded = new Set(expandedQuestions);
                if (newExpanded.has(id)) {
                  newExpanded.delete(id);
                } else {
                  newExpanded.add(id);
                }
                setExpandedQuestions(newExpanded);
              }}
            />
          )}
        </div>

        {/* Question Editor - fills remaining space (horizontal and vertical) */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto p-6">
          {activeQuestion ? (
            <QuestionEditor
              question={activeQuestion}
              onUpdate={updateQuestion}
              onAddSubQuestion={() => addSubQuestion(activeQuestion.id)}
            />
          ) : (
            <div className="flex h-full min-h-[280px] flex-col items-center justify-center px-4 text-center">
              <div className="mb-6 max-w-md rounded-2xl border border-violet-200/60 bg-gradient-to-br from-violet-50/80 via-white to-emerald-50/30 p-8 shadow-sm dark:border-violet-900/45 dark:from-violet-950/40 dark:via-card dark:to-emerald-950/20">
                <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-violet-600 text-white shadow-md">
                  <Sparkles className="h-6 w-6" />
                </span>
                <p className="text-lg font-semibold text-stone-900 dark:text-stone-100">Build your first question</p>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Questions appear in the outline on the left. Select one to edit text, points, and gold solutions—or
                  add a new question to get started.
                </p>
                <Button onClick={addQuestion} size="lg" className="mt-6 shadow-md">
                  <Plus className="mr-2 h-4 w-4" />
                  Add question
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Preview Panel */}
        {showPreview && (
          <div className="w-96 overflow-y-auto border-l border-stone-200/70 bg-stone-50/30 dark:border-stone-800 dark:bg-stone-950/20">
            <PreviewPanel questions={questions} activeQuestionId={activeQuestionId} />
          </div>
        )}
      </div>
    </div>
  );
}

