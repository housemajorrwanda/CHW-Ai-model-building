import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { RichContentViewer } from './RichContentViewer';
import { cn } from '@/lib/utils';
import { AttachmentImage } from '@/components/ui/AttachmentImage';

export interface SubQuestion {
  id: string;
  number?: number;
  text?: string;
  richContent?: any;
  points?: number;
  outlineTitle?: string | null;
  subQuestions?: SubQuestion[];
}

interface QuestionDisplayProps {
  questionNumber: number;
  questionText: string | any;
  questionPoints: number;
  /** Short label from the exam author (shown under the question number). */
  outlineTitle?: string | null;
  attachments?: Array<{ id: string; filePath: string; filename: string; attachmentType?: string }>;
  subQuestions?: SubQuestion[];
  /** When false, sub-parts are omitted (e.g. parent page renders its own answer fields). */
  showSubQuestions?: boolean;
  /** When false, hides the top meta row (number / points) so the parent can render its own chrome. */
  showQuestionHeader?: boolean;
}

const subPartLabel = (sub: SubQuestion, idx: number) => {
  const title = sub.outlineTitle?.trim();
  if (title) return title;
  return String.fromCharCode(97 + idx);
};

function renderSubQuestions(subs: SubQuestion[], depth = 0): JSX.Element {
  return (
    <div className={cn('space-y-3', depth > 0 ? 'mt-2 ml-4' : 'mt-2')}>
      {subs.map((sub, idx) => {
        const letter = subPartLabel(sub, idx);
        const nested = sub.subQuestions ?? [];
        return (
          <div key={sub.id || `${depth}-${idx}`}>
            <div
              className={cn(
                'flex gap-3 pl-2 border-l-2 border-primary/30',
                depth > 0 && 'border-primary/20'
              )}
            >
              <span className="font-semibold text-primary shrink-0 min-w-[2rem] pt-0.5">
                {letter}
              </span>
              <div className="flex-1 space-y-1">
                <RichContentViewer
                  content={
                    sub.richContent ||
                    (typeof (sub.richContent || sub.text) === 'string'
                      ? dedupeLeadingPartLabel(sub.richContent || sub.text || '', letter.replace(/[().]/g, ''))
                      : sub.text)
                  }
                />
                <span className="text-xs text-muted-foreground">
                  [{sub.points ?? 0} {(sub.points ?? 0) === 1 ? 'point' : 'points'}]
                </span>
              </div>
            </div>
            {nested.length > 0 ? renderSubQuestions(nested, depth + 1) : null}
          </div>
        );
      })}
    </div>
  );
}

/** Avoid "(a) (a) …" when the stem already includes the part label */
function dedupeLeadingPartLabel(text: string, letter: string): string {
  const t = text.trim();
  if (!t) return text;
  const esc = letter.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const double = new RegExp(`^\\(\\s*${esc}\\s*\\)\\s*\\(\\s*${esc}\\s*\\)\\s*`, 'i');
  if (double.test(t)) return t.replace(double, `(${letter}) `);
  return text;
}

export function QuestionDisplay({
  questionNumber,
  questionText,
  questionPoints,
  outlineTitle,
  attachments,
  subQuestions,
  showSubQuestions = true,
  showQuestionHeader = true,
}: QuestionDisplayProps) {
  const imageAttachments = (attachments ?? []).filter(
    (a) => a.attachmentType === 'image' || !a.attachmentType
  );

  return (
    <Card className="mb-4 border-0 shadow-none">
      {showQuestionHeader ? (
        <CardHeader className="bg-muted/30 pb-3">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex flex-wrap items-center gap-3 text-xl">
              <Badge variant="outline" className="px-3 py-1 text-base">
                Q{questionNumber}
              </Badge>
              <span className="text-base font-normal text-muted-foreground">
                {questionPoints} {questionPoints === 1 ? 'point' : 'points'}
              </span>
            </CardTitle>
            {outlineTitle?.trim() ? (
              <p className="text-sm font-medium text-foreground sm:max-w-[60%] sm:truncate sm:pl-2 sm:text-right">
                {outlineTitle.trim()}
              </p>
            ) : null}
          </div>
        </CardHeader>
      ) : outlineTitle?.trim() ? (
        <CardHeader className="border-b border-border/50 pb-3 pt-0">
          <p className="text-sm font-medium text-muted-foreground">{outlineTitle.trim()}</p>
        </CardHeader>
      ) : null}

      <CardContent className={cn('space-y-4', showQuestionHeader ? 'pt-4' : 'pt-2')}>
        {/* Main question text — rendered with full KaTeX + TipTap support */}
        {questionText && (
          <RichContentViewer content={questionText} />
        )}

        {/* Images attached to this question */}
        {imageAttachments.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Figures</p>
            <div className="flex flex-wrap gap-4">
              {imageAttachments.map((att) => (
                <AttachmentImage
                  key={att.id}
                  filePath={att.filePath}
                  alt={att.filename}
                  className="max-w-full max-h-64 rounded-lg border object-contain"
                />
              ))}
            </div>
          </div>
        )}

        {/* Sub-questions (a), (b), (c) … */}
        {showSubQuestions && subQuestions && subQuestions.length > 0 && renderSubQuestions(subQuestions)}
      </CardContent>
    </Card>
  );
}
