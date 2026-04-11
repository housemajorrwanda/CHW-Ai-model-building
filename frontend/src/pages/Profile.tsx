import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Loader2,
  Save,
  Camera,
  Trash2,
  Eye,
  EyeOff,
  Mail,
  MapPin,
  Shield,
  Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';
import { format, parseISO, isValid } from 'date-fns';
import { resolveAvatarUrl } from '@/lib/avatar';
import { GENDER_OPTIONS, labelForGender } from '@/constants/demographics';
import { cn } from '@/lib/utils';

function formatDobDisplay(iso?: string): string {
  if (!iso) return '—';
  try {
    const d = parseISO(iso);
    return isValid(d) ? format(d, 'MMMM d, yyyy') : iso;
  } catch {
    return iso;
  }
}

function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete,
  show,
  onToggle,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete: string;
  show: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={show ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          className="pr-10"
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="absolute right-0.5 top-1/2 h-8 w-8 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          onClick={onToggle}
          aria-label={show ? 'Hide password' : 'Show password'}
          aria-pressed={show}
        >
          {show ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}
        </Button>
      </div>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5 border-b border-border/50 py-2.5 last:border-0 last:pb-0">
      <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="truncate text-sm font-medium text-foreground">{value || '—'}</span>
    </div>
  );
}

export default function Profile() {
  const { user, updateProfile, uploadAvatar, removeAvatar } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [institution, setInstitution] = useState('');
  const [country, setCountry] = useState('');
  const [majorDepartment, setMajorDepartment] = useState('');
  const [yearOfStudy, setYearOfStudy] = useState('');
  const [gender, setGender] = useState('_none');
  const [studentId, setStudentId] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [savingContact, setSavingContact] = useState(false);
  const [savingDemo, setSavingDemo] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  useEffect(() => {
    if (!user) return;
    setName(user.name);
    setEmail(user.email);
    setInstitution(user.institution ?? '');
    setCountry(user.country ?? '');
    setMajorDepartment(user.majorDepartment ?? '');
    setYearOfStudy(user.yearOfStudy != null ? String(user.yearOfStudy) : '');
    setGender(user.gender && user.gender.length > 0 ? user.gender : '_none');
    setStudentId(user.studentId ?? '');
    setDateOfBirth(user.dateOfBirth ? user.dateOfBirth.slice(0, 10) : '');
  }, [user]);

  const handleAvatarPick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file || !file.type.startsWith('image/')) {
      toast.error('Please choose an image file');
      return;
    }
    setAvatarBusy(true);
    try {
      await uploadAvatar(file);
      toast.success('Profile photo updated');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setAvatarBusy(false);
    }
  };

  const handleRemoveAvatar = async () => {
    setAvatarBusy(true);
    try {
      await removeAvatar();
      toast.success('Profile photo removed');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Could not remove photo');
    } finally {
      setAvatarBusy(false);
    }
  };

  const handleSaveContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setSavingContact(true);
    try {
      await updateProfile({
        name: name.trim(),
        email: email.trim(),
      });
      toast.success('Contact details saved');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setSavingContact(false);
    }
  };

  const handleSaveDemographics = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    const yTrim = yearOfStudy.trim();
    let yearNum: number | null = null;
    if (yTrim) {
      const n = parseInt(yTrim, 10);
      if (Number.isNaN(n) || n < 1 || n > 20) {
        toast.error('Year of study must be between 1 and 20 (or leave blank)');
        return;
      }
      yearNum = n;
    }
    setSavingDemo(true);
    try {
      await updateProfile({
        institution: institution.trim(),
        country: country.trim(),
        majorDepartment: majorDepartment.trim(),
        yearOfStudy: yTrim ? yearNum : null,
        gender: gender === '_none' ? '' : gender,
        studentId: studentId.trim(),
        dateOfBirth: dateOfBirth ? dateOfBirth : null,
      });
      toast.success('Profile details saved');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setSavingDemo(false);
    }
  };

  const handleSavePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    const wantsPassword = newPassword.length > 0 || currentPassword.length > 0;
    if (!wantsPassword) {
      toast.info('Enter a new password to change it');
      return;
    }
    if (!currentPassword) {
      toast.error('Enter your current password');
      return;
    }
    if (newPassword.length < 8) {
      toast.error('New password must be at least 8 characters');
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }
    setSavingPassword(true);
    try {
      await updateProfile({
        currentPassword,
        newPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      toast.success('Password updated');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setSavingPassword(false);
    }
  };

  if (!user) {
    return null;
  }

  const avatarSrc = resolveAvatarUrl(user.avatar);
  const initials = user.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const yTrimCheck = yearOfStudy.trim();
  let yearInvalid = false;
  if (yTrimCheck) {
    const n = parseInt(yTrimCheck, 10);
    yearInvalid = Number.isNaN(n) || n < 1 || n > 20;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-8 pb-10">
      {/* Page intro */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Profile</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your photo, contact info, demographics, and password in separate sections.
          </p>
        </div>
        <span className="inline-flex items-center rounded-full border border-border bg-muted/50 px-3 py-1 text-xs font-medium capitalize text-muted-foreground">
          {user.role}
        </span>
      </div>

      <div className="grid gap-6 lg:grid-cols-12 lg:items-start">
        {/* Left column: photo + snapshot */}
        <aside className="space-y-6 lg:col-span-4 lg:sticky lg:top-24">
          <Card className="overflow-hidden border-border/80 shadow-sm">
            <CardHeader className="border-b bg-muted/30 pb-4">
              <CardTitle className="text-base font-semibold">Photo</CardTitle>
              <CardDescription>Shown in the header and sidebar</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center gap-4 pt-6">
              <Avatar className={cn('h-32 w-32 border-2 border-border shadow-md')}>
                <AvatarImage src={avatarSrc} alt="" className="object-cover" />
                <AvatarFallback className="bg-primary/10 text-3xl font-semibold text-primary">
                  {initials || 'U'}
                </AvatarFallback>
              </Avatar>
              <input
                ref={fileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                className="hidden"
                onChange={handleAvatarPick}
              />
              <div className="flex w-full flex-col gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  className="w-full"
                  disabled={avatarBusy}
                  onClick={() => fileRef.current?.click()}
                >
                  {avatarBusy ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Camera className="mr-2 h-4 w-4" />
                  )}
                  Upload
                </Button>
                {user.avatar && (
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    disabled={avatarBusy}
                    onClick={handleRemoveAvatar}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Remove photo
                  </Button>
                )}
              </div>
              <p className="text-center text-xs text-muted-foreground">JPEG, PNG, WebP, or GIF · max 2 MB</p>
            </CardContent>
          </Card>

          <Card className="border-border/80 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base font-semibold">
                <Sparkles className="h-4 w-4 text-violet-600" />
                On file
              </CardTitle>
              <CardDescription>Snapshot from your registration</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="rounded-xl bg-muted/40 px-3 py-1">
                <SummaryRow label="Institution" value={user.institution?.trim() ?? ''} />
                <SummaryRow label="Country" value={user.country?.trim() ?? ''} />
                <SummaryRow label="Major" value={user.majorDepartment?.trim() ?? ''} />
                <SummaryRow
                  label="Year"
                  value={user.yearOfStudy != null ? String(user.yearOfStudy) : ''}
                />
                <SummaryRow label="Gender" value={labelForGender(user.gender)} />
                <SummaryRow label="ID" value={user.studentId?.trim() ?? ''} />
                <SummaryRow label="Birth" value={formatDobDisplay(user.dateOfBirth)} />
              </div>
            </CardContent>
          </Card>
        </aside>

        {/* Right column: forms */}
        <div className="space-y-6 lg:col-span-8">
          <Card className="border-border/80 shadow-sm">
            <CardHeader className="border-b bg-muted/20 pb-4">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-violet-100 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300">
                  <Mail className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-lg">Contact</CardTitle>
                  <CardDescription>Name and email used to sign in</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <form onSubmit={handleSaveContact} className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      autoComplete="name"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoComplete="email"
                      required
                    />
                  </div>
                </div>
                <Button type="submit" disabled={savingContact}>
                  {savingContact ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 h-4 w-4" />
                  )}
                  Save contact
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className="border-border/80 shadow-sm">
            <CardHeader className="border-b bg-muted/20 pb-4">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">
                  <MapPin className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-lg">Demographics</CardTitle>
                  <CardDescription>School details and optional background information</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <form onSubmit={handleSaveDemographics} className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="institution">School or institution</Label>
                    <Input
                      id="institution"
                      value={institution}
                      onChange={(e) => setInstitution(e.target.value)}
                      placeholder="Optional"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="country">Country / region</Label>
                    <Input
                      id="country"
                      value={country}
                      onChange={(e) => setCountry(e.target.value)}
                      autoComplete="country-name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="dob">Date of birth</Label>
                    <Input
                      id="dob"
                      type="date"
                      value={dateOfBirth}
                      onChange={(e) => setDateOfBirth(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="major">Major / department</Label>
                    <Input
                      id="major"
                      value={majorDepartment}
                      onChange={(e) => setMajorDepartment(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="year">Year of study</Label>
                    <Input
                      id="year"
                      inputMode="numeric"
                      value={yearOfStudy}
                      onChange={(e) => setYearOfStudy(e.target.value.replace(/\D/g, ''))}
                      placeholder="1–20"
                      className={cn(yearInvalid && 'border-destructive')}
                    />
                    {yearInvalid && (
                      <p className="text-xs text-destructive">Enter a number from 1 to 20, or leave blank</p>
                    )}
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label>Gender</Label>
                    <Select value={gender} onValueChange={setGender}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {GENDER_OPTIONS.map((o) => (
                          <SelectItem key={o.value} value={o.value}>
                            {o.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="sid">Student / staff ID</Label>
                    <Input
                      id="sid"
                      value={studentId}
                      onChange={(e) => setStudentId(e.target.value)}
                      placeholder="Optional"
                    />
                  </div>
                </div>
                <Button type="submit" disabled={savingDemo || yearInvalid}>
                  {savingDemo ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 h-4 w-4" />
                  )}
                  Save demographics
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className="border-border/80 shadow-sm">
            <CardHeader className="border-b bg-muted/20 pb-4">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-900 dark:bg-amber-950/40 dark:text-amber-100">
                  <Shield className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-lg">Password</CardTitle>
                  <CardDescription>Change your password — leave blank if you do not want to change it</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <form onSubmit={handleSavePassword} className="space-y-4">
                <PasswordField
                  id="current"
                  label="Current password"
                  value={currentPassword}
                  onChange={setCurrentPassword}
                  autoComplete="current-password"
                  show={showCurrentPassword}
                  onToggle={() => setShowCurrentPassword((v) => !v)}
                />
                <PasswordField
                  id="newpass"
                  label="New password"
                  value={newPassword}
                  onChange={setNewPassword}
                  autoComplete="new-password"
                  show={showNewPassword}
                  onToggle={() => setShowNewPassword((v) => !v)}
                />
                <PasswordField
                  id="confirm"
                  label="Confirm new password"
                  value={confirmPassword}
                  onChange={setConfirmPassword}
                  autoComplete="new-password"
                  show={showConfirmPassword}
                  onToggle={() => setShowConfirmPassword((v) => !v)}
                />
                <Button type="submit" disabled={savingPassword}>
                  {savingPassword ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Shield className="mr-2 h-4 w-4" />
                  )}
                  Update password
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
