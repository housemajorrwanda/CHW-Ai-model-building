import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { Bell, CheckCheck, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ScrollArea } from '@/components/ui/scroll-area';
import { notificationsAPI, remindersAPI, type NotificationFeedItem } from '@/lib/api';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import {
  ScheduleReminderDialog,
  type ScheduleReminderContext,
} from '@/components/layout/ScheduleReminderDialog';

function timeAgo(iso: string) {
  try {
    return formatDistanceToNow(new Date(iso), { addSuffix: true });
  } catch {
    return '';
  }
}

export function NotificationsBell() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { prefs } = useUserSettings();
  const { user } = useAuth();
  const seenGradeIds = useRef<Set<string>>(new Set());
  const gradeToastPrimed = useRef(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [scheduleContext, setScheduleContext] = useState<ScheduleReminderContext | null>(null);

  const reminderKey = [
    user?.id,
    user?.remindExamDeadlinesEnabled,
    (user?.remindExamOffsetsHours ?? []).join(','),
    user?.remindTeachingDeadlinesEnabled,
  ].join('|');

  const { data, isLoading } = useQuery({
    queryKey: ['notifications', reminderKey],
    queryFn: () => notificationsAPI.getFeed(60),
    enabled: !!user,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
    staleTime: 30_000,
  });

  const markRead = useMutation({
    mutationFn: (id: string) => notificationsAPI.markRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const markAllRead = useMutation({
    mutationFn: () => notificationsAPI.markAllRead(),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      toast.success(res.marked ? `${res.marked} cleared` : 'Up to date');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  useEffect(() => {
    if (!data?.items) return;
    if (!gradeToastPrimed.current) {
      gradeToastPrimed.current = true;
      for (const item of data.items) {
        if (item.category === 'notification' && item.kind === 'grade_released') {
          seenGradeIds.current.add(item.id);
        }
      }
      return;
    }
    if (!prefs.notifyGradeAvailable) return;
    for (const item of data.items) {
      if (item.category !== 'notification' || item.kind !== 'grade_released') continue;
      if (seenGradeIds.current.has(item.id)) continue;
      seenGradeIds.current.add(item.id);
      if (item.readAt) continue;
      toast.info(item.title, { description: item.body || undefined });
    }
  }, [data, prefs.notifyGradeAvailable]);

  const items = data?.items ?? [];
  const unread = data?.unreadCount ?? 0;
  const storedUnread = items.filter((i) => i.category === 'notification' && !i.readAt).length;

  const handleOpenItem = (item: NotificationFeedItem) => {
    if (item.link) navigate(item.link);
    if (item.category === 'notification' && !item.readAt && !item.id.startsWith('reminder:')) {
      markRead.mutate(item.id);
    }
  };

  const openScheduleFor = (item: NotificationFeedItem) => {
    setScheduleContext({
      sourceKey: item.id,
      title: item.title,
      body: item.body,
      link: item.link,
    });
    setScheduleOpen(true);
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="relative shrink-0" aria-label="Notifications">
            <Bell className="h-5 w-5" />
            {unread > 0 ? (
              <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold text-destructive-foreground">
                {unread > 99 ? '99+' : unread}
              </span>
            ) : null}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-[min(100vw-2rem,22rem)] p-0">
          <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
            <DropdownMenuLabel className="p-0 text-base font-semibold">Notifications</DropdownMenuLabel>
            {storedUnread > 0 ? (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 gap-1 text-xs text-muted-foreground"
                disabled={markAllRead.isPending}
                onClick={(e) => {
                  e.preventDefault();
                  markAllRead.mutate();
                }}
              >
                {markAllRead.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CheckCheck className="h-3.5 w-3.5" />
                )}
                Mark all read
              </Button>
            ) : null}
          </div>
          <ScrollArea className="max-h-[min(70vh,20rem)]">
            {isLoading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : items.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">You're all caught up.</p>
            ) : (
              <ul className="divide-y">
                {items.map((item) => (
                  <li key={item.id}>
                    <div
                      className={cn(
                        'flex items-start gap-2 px-3 py-2.5',
                        item.category === 'notification' && !item.readAt && 'bg-primary/5'
                      )}
                    >
                      <button
                        type="button"
                        className={cn(
                          'flex min-w-0 flex-1 flex-col gap-0.5 text-left text-sm transition-colors hover:bg-accent/60 rounded-sm px-0 py-0 -mx-0'
                        )}
                        onClick={() => handleOpenItem(item)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-medium leading-snug">{item.title}</span>
                        </div>
                        {item.body ? (
                          <p className="line-clamp-2 text-xs text-muted-foreground">{item.body}</p>
                        ) : null}
                        <p className="text-[10px] text-muted-foreground">{timeAgo(item.createdAt)}</p>
                      </button>
                      {item.category === 'reminder' ? (
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          className="mt-0.5 h-8 shrink-0 rounded-full px-3 text-xs font-medium"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            openScheduleFor(item);
                          }}
                        >
                          Reminder
                        </Button>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </ScrollArea>
        </DropdownMenuContent>
      </DropdownMenu>

      <ScheduleReminderDialog
        open={scheduleOpen}
        onOpenChange={setScheduleOpen}
        context={scheduleContext}
        onScheduled={() => {
          queryClient.invalidateQueries({ queryKey: ['notifications'] });
          queryClient.invalidateQueries({ queryKey: ['dueReminders'] });
        }}
      />
    </>
  );
}
