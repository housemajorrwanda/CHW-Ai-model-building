import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { FileText, Image, Atom, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Question } from './QuestionBuilder';

interface PreviewPanelProps {
  questions: Question[];
  activeQuestionId: string | null;
}

export function PreviewPanel({ questions, activeQuestionId }: PreviewPanelProps) {
  const renderQuestion = (question: Question, parentNumber: string = '') => {
    const questionNumber = parentNumber ? `${parentNumber}.${question.number}` : question.number.toString();
    const isActive = question.id === activeQuestionId;

    return (
      <div key={question.id} className={cn('space-y-2', isActive && 'ring-2 ring-primary/20 rounded-lg p-2')}>
        {/* Question Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <Badge variant={isActive ? 'default' : 'secondary'}>
              Q{questionNumber}
            </Badge>
            <span className="text-xs text-muted-foreground">{question.points} pts</span>
          </div>
          {question.questionType === 'multi-part' && (
            <Badge variant="outline" className="text-xs">
              Multi-part
            </Badge>
          )}
        </div>

        {/* Question Text */}
        <div className="text-sm">
          {question.text ? (
            <div className="prose prose-sm max-w-none">
              {question.text}
            </div>
          ) : (
            <p className="text-muted-foreground italic">(No question text)</p>
          )}
        </div>

        {/* Attachments */}
        {question.attachments.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {question.attachments.map((att) => (
              <Badge key={att.id} variant="outline" className="text-xs">
                <Image className="h-3 w-3 mr-1" />
                {att.filename}
              </Badge>
            ))}
          </div>
        )}

        {/* Embedded Content */}
        {question.embeddedContent.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {question.embeddedContent.map((content) => (
              <Badge key={content.id} variant="secondary" className="text-xs">
                <Atom className="h-3 w-3 mr-1" />
                {content.contentType}
              </Badge>
            ))}
          </div>
        )}

        {/* Theories */}
        {question.theories.length > 0 && (
          <div className="text-xs space-y-1 p-2 bg-blue-50 border border-blue-200 rounded">
            <p className="font-semibold text-blue-900">Theory & Constants:</p>
            {question.theories.map((theory) => (
              <p key={theory.id} className="text-blue-800">
                • {theory.name}: {theory.value} {theory.unit}
              </p>
            ))}
          </div>
        )}

        {/* Gold Solution Summary */}
        {question.goldSolutionSteps.length > 0 && (
          <div className="text-xs p-2 bg-green-50 border border-green-200 rounded">
            <div className="flex items-center gap-1 mb-1">
              <CheckCircle2 className="h-3 w-3 text-green-700" />
              <span className="font-semibold text-green-900">
                Solution: {question.goldSolutionSteps.length} steps
              </span>
            </div>
            {question.finalAnswer && (
              <p className="text-green-800">
                Final Answer: <strong>{question.finalAnswer}</strong>
              </p>
            )}
          </div>
        )}

        {/* Sub-questions */}
        {question.subQuestions.length > 0 && (
          <div className="ml-4 space-y-2 border-l-2 border-muted pl-3">
            {question.subQuestions.map((sub) => renderQuestion(sub, questionNumber))}
          </div>
        )}
      </div>
    );
  };

  const totalPoints = questions.reduce((sum, q) => {
    const subPoints = q.subQuestions.reduce((subSum, sub) => subSum + sub.points, 0);
    return sum + q.points + subPoints;
  }, 0);

  return (
    <div className="h-full flex flex-col">
      <div className="p-3 border-b bg-muted/20">
        <h3 className="text-sm font-semibold">Live Preview</h3>
        <p className="text-xs text-muted-foreground">Total: {totalPoints} points</p>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {questions.length === 0 ? (
          <div className="text-center text-sm text-muted-foreground py-8">
            <FileText className="h-12 w-12 mx-auto mb-2 opacity-20" />
            <p>No questions to preview</p>
          </div>
        ) : (
          questions.map((q) => (
            <div key={q.id}>
              {renderQuestion(q)}
              <Separator className="my-4" />
            </div>
          ))
        )}
      </div>
    </div>
  );
}

