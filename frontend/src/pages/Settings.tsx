import { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { Bell, Monitor, Moon, Palette, Sun, Loader2 } from 'lucide-react';
import type { UserPreferenceSettings } from '@/lib/user-settings';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

const EXAM_REMINDER_OPTIONS: { hours: number; label: string }[] = [
  { hours: 336, label: '2 weeks' },
  { hours: 168, label: '1 week' },
  { hours: 72, label: '3 days' },
  { hours: 48, label: '2 days' },
  { hours: 24, label: '24 hours' },
  { hours: 12, label: '12 hours' },
  { hours: 6, label: '6 hours' },
  { hours: 3, label: '3 hours' },
  { hours: 1, label: '1 hour' },
];

const DEFAULT_EXAM_OFFSETS = [168, 72, 24];

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const { prefs, setPrefs } = useUserSettings();
  const { user, updateProfile } = useAuth();
  const queryClient = useQueryClient();
  const [reminderBusy, setReminderBusy] = useState(false);

  useEffect(() => setMounted(true), []);

  const updatePrefs = (patch: Partial<UserPreferenceSettings>) => {
    setPrefs(patch);
    toast.success('Preference saved');
  };

  const patchServerReminders = async (patch: {
    remindExamDeadlinesEnabled?: boolean;
    remindExamOffsetsHours?: number[];
    remindTeachingDeadlinesEnabled?: boolean;
  }) => {
    if (!user) return;
    setReminderBusy(true);
    try {
      await updateProfile(patch);
      await queryClient.invalidateQueries({ queryKey: ['notifications'] });
      toast.success('Reminder settings saved');
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Could not save reminders');
    } finally {
      setReminderBusy(false);
    }
  };

  const examOffsets = user?.remindExamOffsetsHours?.length
    ? [...user.remindExamOffsetsHours].sort((a, b) => a - b)
    : DEFAULT_EXAM_OFFSETS;
  const examEnabled = user?.remindExamDeadlinesEnabled !== false;
  const teachingEnabled = user?.remindTeachingDeadlinesEnabled !== false;

  const toggleExamOffset = async (hours: number, checked: boolean) => {
    if (!user) return;
    const set = new Set(examOffsets);
    if (checked) set.add(hours);
    else set.delete(hours);
    let next = [...set].sort((a, b) => a - b);
    if (examEnabled && next.length === 0) {
      toast.error('Keep at least one time window, or turn off exam reminders above.');
      return;
    }
    await patchServerReminders({ remindExamOffsetsHours: next });
  };

  const appearanceValue = (theme as string) || 'system';

  const showStudentReminders = user?.role === 'student';
  const showTeachingReminders = user?.role === 'professor' || user?.role === 'admin';

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Appearance and device preferences; reminders sync with your account
        </p>
      </div>

      <Card className="border-border/80 shadow-sm">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Palette className="h-6 w-6" />
            </div>
            <div>
              <CardTitle className="text-lg">Appearance</CardTitle>
              <CardDescription>Theme applies across MathGrade on this browser</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {!mounted ? (
            <p className="text-sm text-muted-foreground">Loading theme…</p>
          ) : (
            <RadioGroup
              value={appearanceValue}
              onValueChange={(v) => setTheme(v)}
              className="grid gap-3"
            >
              <div className="flex items-center justify-between rounded-lg border border-border/80 p-3 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring">
                <Label htmlFor="theme-light" className="flex cursor-pointer items-center gap-3 font-normal">
                  <Sun className="h-4 w-4 text-muted-foreground" />
                  Light
                </Label>
                <RadioGroupItem value="light" id="theme-light" />
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border/80 p-3 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring">
                <Label htmlFor="theme-dark" className="flex cursor-pointer items-center gap-3 font-normal">
                  <Moon className="h-4 w-4 text-muted-foreground" />
                  Dark
                </Label>
                <RadioGroupItem value="dark" id="theme-dark" />
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border/80 p-3 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring">
                <Label htmlFor="theme-system" className="flex cursor-pointer items-center gap-3 font-normal">
                  <Monitor className="h-4 w-4 text-muted-foreground" />
                  System
                </Label>
                <RadioGroupItem value="system" id="theme-system" />
              </div>
            </RadioGroup>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/80 shadow-sm">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Bell className="h-6 w-6" />
            </div>
            <div>
              <CardTitle className="text-lg">Notifications</CardTitle>
              <CardDescription>
                In-app bell and toasts. Exam and teaching reminders are saved to your account.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-0.5">
              <Label htmlFor="notify-grade" className="text-base">
                Grades & feedback
              </Label>
              <p className="text-sm text-muted-foreground">
                Toast when newly released grades appear in the bell list
              </p>
            </div>
            <Switch
              id="notify-grade"
              checked={prefs.notifyGradeAvailable}
              onCheckedChange={(checked) => updatePrefs({ notifyGradeAvailable: checked })}
            />
          </div>

          {showStudentReminders ? (
            <>
              <Separator />
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-4">
                  <div className="space-y-0.5">
                    <Label htmlFor="remind-exam" className="text-base">
                      Exam deadline reminders
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Show due-soon and overdue exams in the notification list
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {reminderBusy ? <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" /> : null}
                    <Switch
                      id="remind-exam"
                      checked={examEnabled}
                      disabled={reminderBusy}
                      onCheckedChange={async (checked) => {
                        if (checked) {
                          await patchServerReminders({
                            remindExamDeadlinesEnabled: true,
                            remindExamOffsetsHours:
                              examOffsets.length > 0 ? examOffsets : [...DEFAULT_EXAM_OFFSETS],
                          });
                        } else {
                          await patchServerReminders({ remindExamDeadlinesEnabled: false });
                        }
                      }}
                    />
                  </div>
                </div>
                {examEnabled ? (
                  <div className="rounded-lg border border-border/80 bg-muted/30 p-3">
                    <p className="mb-3 text-sm font-medium text-foreground">Remind when the due date is within:</p>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {EXAM_REMINDER_OPTIONS.map(({ hours, label }) => (
                        <label
                          key={hours}
                          className="flex cursor-pointer items-center gap-2 rounded-md border border-transparent px-1 py-1.5 text-sm hover:bg-background/80 has-[[data-state=checked]]:border-border"
                        >
                          <Checkbox
                            checked={examOffsets.includes(hours)}
                            disabled={reminderBusy}
                            onCheckedChange={(v) => toggleExamOffset(hours, v === true)}
                          />
                          <span>{label}</span>
                        </label>
                      ))}
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      You get one reminder per exam for the tightest window that still applies.
                    </p>
                  </div>
                ) : null}
              </div>
            </>
          ) : null}

          {showTeachingReminders ? (
            <>
              <Separator />
              <div className="flex items-center justify-between gap-4">
                <div className="space-y-0.5">
                  <Label htmlFor="remind-teaching" className="text-base">
                    Teaching workload reminders
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Pending enrollments and submissions waiting for approval or release
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {reminderBusy ? <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" /> : null}
                  <Switch
                    id="remind-teaching"
                    checked={teachingEnabled}
                    disabled={reminderBusy}
                    onCheckedChange={(checked) =>
                      patchServerReminders({ remindTeachingDeadlinesEnabled: checked })
                    }
                  />
                </div>
              </div>
            </>
          ) : null}

          <Separator />
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-0.5">
              <Label htmlFor="comfortable" className="text-base">
                Comfortable layout
              </Label>
              <p className="text-sm text-muted-foreground">
                Slightly more spacing in lists and cards on this device
              </p>
            </div>
            <Switch
              id="comfortable"
              checked={prefs.comfortableDensity}
              onCheckedChange={(checked) => updatePrefs({ comfortableDensity: checked })}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
