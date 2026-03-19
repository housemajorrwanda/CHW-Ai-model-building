import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { RichContentViewer } from './RichContentViewer';

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
  attachments?: Array<{ id: string; filePath: string; filename: string; attachmentType?: string }>;
  subQuestions?: SubQuestion[];
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const ORIGIN = API_BASE_URL.replace(/\/api\/?$/, '');

function resolveAttachmentSrc(filePath: string): string {
  if (!filePath) return '';
  if (filePath.startsWith('http')) return filePath;
  return `${ORIGIN}${filePath}`;
}

const subPartLabel = (idx: number) => String.fromCharCode(97 + idx);

export function QuestionDisplay({
  questionNumber,
  questionText,
  questionPoints,
  attachments,
  subQuestions,
}: QuestionDisplayProps) {
  const imageAttachments = (attachments ?? []).filter(
    (a) => a.attachmentType === 'image' || !a.attachmentType
  );

  return (
    <Card className="mb-4">
      <CardHeader className="pb-3 bg-muted/30">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl flex items-center gap-3">
            <Badge variant="outline" className="text-base px-3 py-1">
              Q{questionNumber}
            </Badge>
            <span className="text-base font-normal text-muted-foreground">
              {questionPoints} {questionPoints === 1 ? 'point' : 'points'}
            </span>
          </CardTitle>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Main question text — rendered with full KaTeX + TipTap support */}
        {questionText && (
          <RichContentViewer content={questionText} />
        )}

        {/* Images attached to this question */}
        {imageAttachments.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-semibold text-muted-foreground">Diagrams / Images</p>
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
                  <RichContentViewer content={sub.richContent || sub.text} />
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
