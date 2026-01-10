import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight, Plus, Trash2, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Question } from './QuestionBuilder';

interface QuestionListProps {
  questions: Question[];
  activeId: string | null;
  expandedIds?: Set<string>;
  onSelect: (id: string) => void;
  onAddSubQuestion: (parentId: string) => void;
  onDelete: (id: string) => void;
  onToggleExpand?: (id: string) => void;
}

export function QuestionList({ 
  questions, 
  activeId, 
  expandedIds = new Set(),
  onSelect, 
  onAddSubQuestion, 
  onDelete,
  onToggleExpand
}: QuestionListProps) {
  const toggleExpand = (id: string) => {
    if (onToggleExpand) {
      onToggleExpand(id);
    }
  };

  const renderQuestion = (question: Question, level: number = 0) => {
    const isActive = question.id === activeId;
    const isExpanded = expandedIds.has(question.id);
    const hasSubQuestions = question.subQuestions.length > 0;

    return (
      <div key={question.id}>
        <div
          className={cn(
            'group flex items-center gap-2 px-3 py-2 hover:bg-accent/50 cursor-pointer transition-colors',
            isActive && 'bg-primary/10 border-l-2 border-primary',
            level > 0 && 'pl-6'
          )}
          style={{ paddingLeft: `${12 + level * 16}px` }}
        >
          {/* Expand/Collapse */}
          {hasSubQuestions ? (
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5 p-0"
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(question.id);
              }}
            >
              {isExpanded ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
            </Button>
          ) : (
            <div className="w-5" />
          )}

          {/* Question Item */}
          <div
            className="flex-1 flex items-center gap-2"
            onClick={() => onSelect(question.id)}
          >
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">
              {level > 0 ? (
                <span className="text-muted-foreground">
                  {question.number}. {question.text || '(Untitled)'}
                </span>
              ) : (
                <span>
                  Q{question.number}: {question.text || '(Untitled)'}
                </span>
              )}
            </span>
            <span className="ml-auto text-xs text-muted-foreground">
              {question.points}pts
            </span>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={(e) => {
                e.stopPropagation();
                onAddSubQuestion(question.id);
              }}
              title="Add sub-question"
            >
              <Plus className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-destructive hover:text-destructive"
              onClick={(e) => {
                e.stopPropagation();
                if (confirm('Delete this question?')) {
                  onDelete(question.id);
                }
              }}
              title="Delete question"
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        </div>

        {/* Render Sub-questions */}
        {hasSubQuestions && isExpanded && (
          <div>
            {question.subQuestions.map((subQ) => renderQuestion(subQ, level + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-3 border-b bg-muted/20">
        <h3 className="text-sm font-semibold">Question Outline</h3>
      </div>
      <div className="flex-1 overflow-y-auto">
        {questions.length === 0 ? (
          <div className="p-4 text-center text-sm text-muted-foreground">
            No questions yet
          </div>
        ) : (
          questions.map((q) => renderQuestion(q, 0))
        )}
      </div>
    </div>
  );
}

