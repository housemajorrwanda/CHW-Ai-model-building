import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { remindersAPI, type DueReminderItem } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { playReminderChime } from '@/lib/play-reminder-chime';

/**
 * Polls for due personal reminders and shows a high-attention modal + chime
 * (not mixed into the notification bell dropdown).
 */
export function DueRemindersAlert() {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<DueReminderItem | null>(null);
  const lastChimedKeyRef = useRef<string | null>(null);
  const dismissingRef = useRef(false);

  const { data: dueList = [] } = useQuery({
    queryKey: ['dueReminders'],
    queryFn: () => remindersAPI.getDue(),
    enabled: isAuthenticated && !!user,
    refetchInterval: 10_000,
    refetchOnWindowFocus: true,
    staleTime: 0,
  });

  const dismissMutation = useMutation({
    mutationFn: (id: string) => remindersAPI.acknowledge(id),
  });

  const runAck = async (id: string) => {
    dismissingRef.current = true;
    setOpen(false);
    setActive(null);
    try {
      await dismissMutation.mutateAsync(id);
      await queryClient.refetchQueries({ queryKey: ['dueReminders'] });
    } finally {
      dismissingRef.current = false;
      lastChimedKeyRef.current = null;
    }
  };

  useEffect(() => {
    if (dismissingRef.current) return;
    if (!dueList.length) {
      if (!open) setActive(null);
      return;
    }
    const head = dueList[0];
    const key = `${head.id}|${head.remindAt}`;
    if (open && active) {
      const curKey = `${active.id}|${active.remindAt}`;
      if (curKey === key) return;
    }
    if (!open) {
      setActive(head);
      setOpen(true);
      if (lastChimedKeyRef.current !== key) {
        lastChimedKeyRef.current = key;
        playReminderChime();
      }
    }
  }, [dueList, open, active]);

  const handleDismiss = () => {
    if (!active || dismissMutation.isPending) return;
    void runAck(active.id);
  };

  const handleOpenAndDismiss = async () => {
    if (!active?.link || dismissMutation.isPending) return;
    const path = active.link;
    const id = active.id;
    await runAck(id);
    navigate(path);
  };

  if (!isAuthenticated || !user) return null;

  return (
    <AlertDialog open={open} onOpenChange={() => {}}>
      <AlertDialogContent
        className="z-[100] max-w-md border-2 border-amber-500 bg-amber-50 shadow-2xl animate-[pulse_1.1s_ease-in-out_infinite] dark:border-amber-400 dark:bg-amber-950/95 dark:shadow-amber-900/40 sm:rounded-lg"
        onEscapeKeyDown={(e) => e.preventDefault()}
        onPointerDownOutside={(e) => e.preventDefault()}
      >
        <AlertDialogHeader>
          <AlertDialogTitle className="text-amber-950 dark:text-amber-50">Reminder — it's time</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-2 text-left text-foreground">
              <p className="text-base font-semibold text-foreground">{active?.title}</p>
              {active?.body ? (
                <p className="whitespace-pre-wrap text-sm text-muted-foreground">{active.body}</p>
              ) : null}
              {active?.repeat && active.repeat !== 'none' ? (
                <p className="text-xs text-muted-foreground">Repeats: {active.repeat}</p>
              ) : null}
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex-col gap-2 sm:flex-col">
          {active?.link ? (
            <Button
              type="button"
              variant="default"
              className="w-full"
              disabled={dismissMutation.isPending}
              onClick={() => void handleOpenAndDismiss()}
            >
              {dismissMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Open related page'
              )}
            </Button>
          ) : null}
          <AlertDialogAction
            className="w-full bg-amber-700 text-white hover:bg-amber-800 dark:bg-amber-600 dark:hover:bg-amber-500"
            disabled={dismissMutation.isPending}
            onClick={(e) => {
              e.preventDefault();
              handleDismiss();
            }}
          >
            {dismissMutation.isPending ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving…
              </span>
            ) : (
              'Dismiss'
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
