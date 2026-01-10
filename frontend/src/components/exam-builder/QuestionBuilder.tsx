import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus, Eye, Save, ChevronLeft, ChevronRight } from 'lucide-react';
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
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-4 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <Button onClick={addQuestion} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Add Question
          </Button>
          <Button
            onClick={() => setShowPreview(!showPreview)}
            variant="outline"
            size="sm"
          >
            <Eye className="h-4 w-4 mr-2" />
            {showPreview ? 'Hide' : 'Show'} Preview
          </Button>
        </div>
        <div className="text-sm text-muted-foreground">
          {questions.length} {questions.length === 1 ? 'question' : 'questions'}
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
        <div className={`border-r overflow-y-auto bg-muted/10 transition-all duration-300 ${sidebarCollapsed ? 'w-0 overflow-hidden' : 'w-64'}`}>
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

        {/* Question Editor */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeQuestion ? (
            <QuestionEditor
              question={activeQuestion}
              onUpdate={updateQuestion}
              onAddSubQuestion={() => addSubQuestion(activeQuestion.id)}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="text-muted-foreground mb-4">
                <p className="text-lg font-medium mb-2">No question selected</p>
                <p className="text-sm">Select a question from the list or create a new one</p>
              </div>
              <Button onClick={addQuestion}>
                <Plus className="h-4 w-4 mr-2" />
                Create First Question
              </Button>
            </div>
          )}
        </div>

        {/* Preview Panel */}
        {showPreview && (
          <div className="w-96 border-l overflow-y-auto bg-muted/5">
            <PreviewPanel questions={questions} activeQuestionId={activeQuestionId} />
          </div>
        )}
      </div>
    </div>
  );
}

