import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { RichContentViewer } from './RichContentViewer';
import { cn } from '@/lib/utils';

interface SubQuestion {
  id: string;
  number: number;
  text: string;
  richContent?: any;
  points: number;
}

interface QuestionDisplayProps {
  questionNumber: number;
  questionText: string | any;
  questionPoints: number;
  /** Short label from the exam author (shown under the question number). */
  outlineTitle?: string | null;
  attachments?: Array<{ id: string; filePath: string; filename: string; attachmentType?: string }>;
  subQuestions?: SubQuestion[];
  /** When false, hides the top meta row (number / points) so the parent can render its own chrome. */
  showQuestionHeader?: boolean;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const ORIGIN = API_BASE_URL.replace(/\/api\/?$/, '');

function resolveAttachmentSrc(filePath: string): string {
  if (!filePath) return '';
  if (filePath.startsWith('http')) return filePath;
  return `${ORIGIN}${filePath}`;
}

const subPartLabel = (idx: number) => String.fromCharCode(97 + idx);

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
                <img
                  key={att.id}
                  src={resolveAttachmentSrc(att.filePath)}
                  alt={att.filename}
                  className="max-w-full max-h-64 rounded-lg border object-contain"
                />
              ))}
            </div>
          </div>
        )}

        {/* Sub-questions (a), (b), (c) … */}
        {subQuestions && subQuestions.length > 0 && (
          <div className="space-y-3 mt-2">
            {subQuestions.map((sub, idx) => (
              <div
                key={sub.id || idx}
                className="flex gap-3 pl-2 border-l-2 border-primary/30"
              >
                <span className="font-semibold text-primary shrink-0 w-6 pt-0.5">
                  ({subPartLabel(idx)})
                </span>
                <div className="flex-1 space-y-1">
                  <RichContentViewer
                    content={
                      typeof (sub.richContent || sub.text) === 'string'
                        ? dedupeLeadingPartLabel(sub.richContent || sub.text, subPartLabel(idx))
                        : sub.richContent || sub.text
                    }
                  />
                  <span className="text-xs text-muted-foreground">
                    [{sub.points} {sub.points === 1 ? 'point' : 'points'}]
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
