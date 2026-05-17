import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { remindersAPI } from '@/lib/api';

export type ScheduleReminderContext = {
  sourceKey: string;
  title: string;
  body: string | null | undefined;
  link: string | null | undefined;
};

function defaultLocalDatetime(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(14, 30, 0, 0);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

type Repeat = 'none' | 'daily' | 'weekly' | 'monthly';

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: ScheduleReminderContext | null;
  onScheduled: () => void;
};

export function ScheduleReminderDialog({ open, onOpenChange, context, onScheduled }: Props) {
  const [whenLocal, setWhenLocal] = useState<string>(() => defaultLocalDatetime());
  const [repeat, setRepeat] = useState<Repeat>('none');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open && context) {
      setWhenLocal(defaultLocalDatetime());
      setRepeat('none');
      setNote('');
    }
  }, [open, context?.sourceKey]);

  const handleSave = async () => {
    if (!context) return;
    const t = new Date(whenLocal);
    if (Number.isNaN(t.getTime())) {
      toast.error('Invalid date and time');
      return;
    }
    setSaving(true);
    try {
      await remindersAPI.schedule({
        sourceKey: context.sourceKey,
        title: context.title,
        body: context.body ?? undefined,
        link: context.link ?? undefined,
        userNote: note.trim() || undefined,
        remindAt: t.toISOString(),
        repeat,
      });
      toast.success('Reminder scheduled');
      onOpenChange(false);
      onScheduled();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Could not save reminder');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md" onClick={(e) => e.stopPropagation()}>
        <DialogHeader>
          <DialogTitle>Schedule reminder</DialogTitle>
          <DialogDescription>
            When the time is reached, a separate alert will appear (with a sound). Your device time zone is used.
          </DialogDescription>
        </DialogHeader>
        {context ? (
          <div className="space-y-4">
            <div className="rounded-md border bg-muted/40 px-3 py-2 text-sm">
              <p className="font-medium leading-snug">{context.title}</p>
              {context.body ? (
                <p className="mt-1 line-clamp-3 text-muted-foreground">{context.body}</p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="remind-when">When</Label>
              <input
                id="remind-when"
                type="datetime-local"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                value={whenLocal}
                onChange={(e) => setWhenLocal(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Repeat</Label>
              <Select value={repeat} onValueChange={(v) => setRepeat(v as Repeat)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Does not repeat</SelectItem>
                  <SelectItem value="daily">Every day</SelectItem>
                  <SelectItem value="weekly">Every week</SelectItem>
                  <SelectItem value="monthly">Every month (approx.)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="remind-note">Note (optional)</Label>
              <Textarea
                id="remind-note"
                placeholder="Why you want to be reminded…"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={3}
                maxLength={2000}
                className="resize-none"
              />
            </div>
          </div>
        ) : null}
        <DialogFooter className="gap-2 sm:gap-0">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button type="button" onClick={handleSave} disabled={saving || !context}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save reminder'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
