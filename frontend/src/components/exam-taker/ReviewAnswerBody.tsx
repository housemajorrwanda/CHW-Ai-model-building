import { RichContentViewer } from './RichContentViewer';
import { MathText } from '@/components/ui/MathText';
import { looksLikeTipTapHtml } from '@/lib/plainTextWithMathToDoc';

/** Renders a stored answer in the review-before-submit dialog. */
export function ReviewAnswerBody({ body }: { body: string }) {
  const text = (body || '').trim();
  if (!text) return null;
  if (looksLikeTipTapHtml(text)) {
    return (
      <div className="prose prose-sm max-w-none text-xs leading-relaxed text-foreground">
        <RichContentViewer content={text} />
      </div>
    );
  }
  return (
    <div className="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-foreground">
      <MathText text={text} />
    </div>
  );
}
