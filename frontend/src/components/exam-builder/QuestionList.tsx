import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight, Plus, Trash2, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Question } from './QuestionBuilder';
import { questionOutlineLabel } from './questionOutlineLabel';

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
            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="min-w-0 flex-1 text-left">
              {level > 0 ? (
                <span className="block text-sm text-muted-foreground">
                  <span className="font-medium text-foreground/80">({question.number})</span>{' '}
                  <span className="break-words">{questionOutlineLabel(question, 48)}</span>
                </span>
              ) : (
                <span className="block text-sm leading-snug">
                  <span className="font-semibold text-foreground">Q{question.number}</span>
                  <span className="text-muted-foreground font-normal"> · </span>
                  <span className="font-medium break-words">{questionOutlineLabel(question)}</span>
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
    <div className="flex h-full flex-col">
      <div className="border-b border-stone-200/70 bg-white/60 px-3 py-2.5 dark:border-stone-800 dark:bg-stone-950/40">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Outline</h3>
      </div>
      <div className="flex-1 overflow-y-auto">
        {questions.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">
            No questions yet—use <span className="font-medium text-foreground">Add question</span> above
          </div>
        ) : (
          questions.map((q) => renderQuestion(q, 0))
        )}
      </div>
    </div>
  );
}

