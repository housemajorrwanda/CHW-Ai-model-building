import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Loader2, Upload, ListChecks, CheckCircle2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { examsAPI, type AnswerKeyPreviewResponse } from '@/lib/api';

interface AnswerKeyUploadProps {
  examId: string;
  examTitle?: string;
  onApplied?: () => void;
}

export function AnswerKeyUpload({ examId, examTitle, onApplied }: AnswerKeyUploadProps) {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [overwrite, setOverwrite] = useState(true);
  const [preview, setPreview] = useState<AnswerKeyPreviewResponse | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isApplying, setIsApplying] = useState(false);

  const handlePreview = async () => {
    if (!file) {
      toast.error('Choose an answer key file first');
      return;
    }
    setIsPreviewing(true);
    try {
      const result = await examsAPI.previewAnswerKey(examId, file);
      setPreview(result);
      if (result.summary.matched_count === 0) {
        toast.warning('No answers could be matched to exam questions');
      } else {
        toast.success(`Matched ${result.summary.matched_count} question/part(s)`);
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Preview failed');
      setPreview(null);
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleApply = async () => {
    if (!file) {
      toast.error('Choose an answer key file first');
      return;
    }
    setIsApplying(true);
    try {
      const result = await examsAPI.uploadAnswerKey(examId, file, overwrite);
      toast.success(`Applied gold answers to ${result.questions_updated} question/part(s)`);
      setPreview(null);
      setFile(null);
      queryClient.invalidateQueries({ queryKey: ['exam', examId] });
      onApplied?.();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to apply answer key');
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <Card className="border-amber-200/60 dark:border-amber-900/40">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <ListChecks className="h-5 w-5 text-amber-600" />
          Upload answer key separately
        </CardTitle>
        <CardDescription>
          {examTitle ? (
            <>
              Add marking schemes for <span className="font-medium">{examTitle}</span> without
              mixing them into the question upload. Answers are matched by question number and
              sub-part labels (A, B, (i), etc.).
            </>
          ) : (
            <>
              Upload a marking scheme or model answers document and align it to existing questions.
              Inline gold solutions in the exam editor still work as before.
            </>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor={`answer-key-file-${examId}`}>Answer key file (.txt, .pdf, image)</Label>
          <Input
            id={`answer-key-file-${examId}`}
            type="file"
            accept=".txt,.pdf,.jpg,.jpeg,.png"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setPreview(null);
            }}
          />
          <p className="text-xs text-muted-foreground">
            Use the same numbering as your exam: Question 1, Q2, Gold Solution, Model Answer, etc.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Checkbox
            id={`overwrite-gold-${examId}`}
            checked={overwrite}
            onCheckedChange={(v) => setOverwrite(v === true)}
          />
          <Label htmlFor={`overwrite-gold-${examId}`} className="text-sm font-normal cursor-pointer">
            Replace existing gold solutions on matched questions
          </Label>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={!file || isPreviewing || isApplying}
            onClick={handlePreview}
          >
            {isPreviewing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ListChecks className="mr-2 h-4 w-4" />
            )}
            Preview alignment
          </Button>
          <Button type="button" disabled={!file || isApplying || isPreviewing} onClick={handleApply}>
            {isApplying ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Upload className="mr-2 h-4 w-4" />
            )}
            Apply to exam
          </Button>
        </div>

        {preview && (
          <div className="space-y-4 rounded-xl border bg-muted/30 p-4">
            <div className="flex flex-wrap gap-2">
              <Badge variant="default" className="gap-1">
                <CheckCircle2 className="h-3 w-3" />
                {preview.summary.matched_count} matched
              </Badge>
              {preview.summary.unmatched_exam_count > 0 && (
                <Badge variant="secondary" className="gap-1">
                  {preview.summary.unmatched_exam_count} exam Q without key
                </Badge>
              )}
              {preview.summary.unmatched_key_count > 0 && (
                <Badge variant="outline" className="gap-1 text-amber-700 border-amber-300">
                  <AlertCircle className="h-3 w-3" />
                  {preview.summary.unmatched_key_count} key section unmatched
                </Badge>
              )}
            </div>

            {preview.matched.length > 0 && (
              <div>
                <p className="text-sm font-semibold mb-2">Matched</p>
                <ul className="space-y-2 max-h-48 overflow-y-auto text-sm">
                  {preview.matched.map((m) => (
                    <li key={`${m.question_id}-${m.path}`} className="rounded-lg border bg-background px-3 py-2">
                      <span className="font-medium">{m.path}</span>
                      <span className="text-muted-foreground"> · {m.step_count} step(s)</span>
                      {m.preview && (
                        <p className="text-xs text-muted-foreground mt-1 truncate">{m.preview}</p>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {preview.unmatched_key_sections.length > 0 && (
              <div>
                <p className="text-sm font-semibold mb-2 text-amber-800 dark:text-amber-200">
                  Unmatched key sections
                </p>
                <ul className="space-y-1 max-h-32 overflow-y-auto text-xs text-muted-foreground">
                  {preview.unmatched_key_sections.map((u, i) => (
                    <li key={`${u.path}-${i}`}>
                      {u.path}: {u.preview || u.reason || 'No preview'}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
