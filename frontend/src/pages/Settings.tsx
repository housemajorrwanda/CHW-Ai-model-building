import { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Bell, Monitor, Moon, Palette, Sun } from 'lucide-react';
import type { UserPreferenceSettings } from '@/lib/user-settings';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import { toast } from 'sonner';

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const { prefs, setPrefs } = useUserSettings();

  useEffect(() => setMounted(true), []);

  const updatePrefs = (patch: Partial<UserPreferenceSettings>) => {
    setPrefs(patch);
    toast.success('Preference saved');
  };

  const appearanceValue = (theme as string) || 'system';

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Appearance and notifications (stored on this device)
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
                Preferences for in-app messages and future email (when enabled by your school)
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
                Alert when an exam is graded or feedback is ready
              </p>
            </div>
            <Switch
              id="notify-grade"
              checked={prefs.notifyGradeAvailable}
              onCheckedChange={(checked) => updatePrefs({ notifyGradeAvailable: checked })}
            />
          </div>
          <Separator />
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-0.5">
              <Label htmlFor="remind-exam" className="text-base">
                Exam deadlines
              </Label>
              <p className="text-sm text-muted-foreground">
                Reminders before a scheduled exam window ends
              </p>
            </div>
            <Switch
              id="remind-exam"
              checked={prefs.remindExamDeadlines}
              onCheckedChange={(checked) => updatePrefs({ remindExamDeadlines: checked })}
            />
          </div>
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
