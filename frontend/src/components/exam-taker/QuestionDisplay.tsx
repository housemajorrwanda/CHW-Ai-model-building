import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface QuestionDisplayProps {
  questionNumber: number;
  questionText: string | any;
  questionPoints: number;
}

export function QuestionDisplay({ questionNumber, questionText, questionPoints }: QuestionDisplayProps) {
  // Parse richContent if it's a TipTap JSON object
  const renderQuestionContent = () => {
    if (!questionText) return 'No question text';
    
    // If it's a string, use it directly
    if (typeof questionText === 'string') {
      // Check if it's HTML
      if (questionText.includes('<')) {
        return <div dangerouslySetInnerHTML={{ __html: questionText }} />;
      }
      return <p>{questionText}</p>;
    }
    
    // If it's a TipTap JSON object, render it
    if (questionText.type === 'doc' && questionText.content) {
      return renderTipTapContent(questionText.content);
    }
    
    // Fallback: stringify it
    return <p>{JSON.stringify(questionText)}</p>;
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
        case 'heading':
          const HeadingTag = `h${node.attrs?.level || 1}` as keyof JSX.IntrinsicElements;
          return (
            <HeadingTag key={index} className="font-bold mb-2">
              {node.content ? renderInlineContent(node.content) : ''}
            </HeadingTag>
          );
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
        
        // Apply marks (bold, italic, etc.)
        if (node.marks) {
          node.marks.forEach((mark: any) => {
            if (mark.type === 'bold') {
              text = <strong key={index}>{text}</strong>;
            } else if (mark.type === 'italic') {
              text = <em key={index}>{text}</em>;
            } else if (mark.type === 'code') {
              text = <code key={index} className="bg-muted px-1 rounded">{text}</code>;
            }
          });
        }
        
        return <span key={index}>{text}</span>;
      }
      return null;
    });
  };

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
      <CardContent className="pt-4">
        <div className="prose prose-sm max-w-none">
          {renderQuestionContent()}
        </div>
      </CardContent>
    </Card>
  );
}

