import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

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

export function QuestionDisplay({
  questionNumber,
  questionText,
  questionPoints,
  attachments,
  subQuestions,
}: QuestionDisplayProps) {

  const renderQuestionContent = (content: string | any) => {
    if (!content) return null;

    if (typeof content === 'string') {
      if (content.includes('<')) {
        return <div dangerouslySetInnerHTML={{ __html: content }} />;
      }
      return <p>{content}</p>;
    }

    if (content.type === 'doc' && content.content) {
      return <>{renderTipTapContent(content.content)}</>;
    }

    return <p>{JSON.stringify(content)}</p>;
  };

  const renderTipTapContent = (content: any[]) => {
    return content.map((node: any, index: number) => {
      switch (node.type) {
        case 'paragraph':
          return (
            <p key={index} className="mb-2">
              {node.content ? renderInlineContent(node.content) : ''}
            </p>
          );
        case 'heading': {
          const HeadingTag = `h${node.attrs?.level || 1}` as keyof JSX.IntrinsicElements;
          return (
            <HeadingTag key={index} className="font-bold mb-2">
              {node.content ? renderInlineContent(node.content) : ''}
            </HeadingTag>
          );
        }
        case 'bulletList':
          return (
            <ul key={index} className="list-disc pl-6 mb-2">
              {node.content?.map((item: any, itemIndex: number) => (
                <li key={itemIndex}>
                  {item.content ? renderTipTapContent(item.content) : ''}
                </li>
              ))}
            </ul>
          );
        case 'orderedList':
          return (
            <ol key={index} className="list-decimal pl-6 mb-2">
              {node.content?.map((item: any, itemIndex: number) => (
                <li key={itemIndex}>
                  {item.content ? renderTipTapContent(item.content) : ''}
                </li>
              ))}
            </ol>
          );
        case 'image':
          return (
            <img
              key={index}
              src={node.attrs?.src}
              alt={node.attrs?.alt || ''}
              className="max-w-full rounded-lg my-4"
            />
          );
        default:
          return null;
      }
    });
  };

  const renderInlineContent = (content: any[]) => {
    return content.map((node: any, index: number) => {
      if (node.type === 'text') {
        let text: React.ReactNode = node.text;
        if (node.marks) {
          node.marks.forEach((mark: any) => {
            if (mark.type === 'bold') text = <strong key={index}>{text}</strong>;
            else if (mark.type === 'italic') text = <em key={index}>{text}</em>;
            else if (mark.type === 'code') text = <code key={index} className="bg-muted px-1 rounded">{text}</code>;
          });
        }
        return <span key={index}>{text}</span>;
      }
      return null;
    });
  };

  const subPartLabel = (idx: number) => String.fromCharCode(97 + idx); // a, b, c, …

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
              {questionPoints} {questionPoints === 1 ? 'mark' : 'marks'}
            </span>
          </CardTitle>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Main question text / intro */}
        {questionText && (
          <div className="prose prose-sm max-w-none">
            {renderQuestionContent(questionText)}
          </div>
        )}

        {/* Embedded images attached to this question (from PDF extraction) */}
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
                  <div className="prose prose-sm max-w-none">
                    {renderQuestionContent(sub.richContent || sub.text)}
                  </div>
                  <span className="text-xs text-muted-foreground">
                    [{sub.points} {sub.points === 1 ? 'mark' : 'marks'}]
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
