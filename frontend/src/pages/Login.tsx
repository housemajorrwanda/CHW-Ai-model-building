import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { UserRole } from '@/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { GraduationCap, User, Shield, AlertCircle, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { Separator } from '@/components/ui/separator';
import { GENDER_OPTIONS } from '@/constants/demographics';

const roles: { value: UserRole; label: string; icon: typeof User; description: string }[] = [
  { value: 'professor', label: 'Professor', icon: GraduationCap, description: 'Create and grade exams' },
  { value: 'student', label: 'Student', icon: User, description: 'Submit and view results' },
  { value: 'admin', label: 'Admin', icon: Shield, description: 'Manage system' },
];

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [selectedRole, setSelectedRole] = useState<UserRole>('student');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirm, setRegConfirm] = useState('');
  const [institution, setInstitution] = useState('');
  const [country, setCountry] = useState('');
  const [majorDepartment, setMajorDepartment] = useState('');
  const [yearOfStudy, setYearOfStudy] = useState('');
  const [gender, setGender] = useState<string>('_none');
  const [studentId, setStudentId] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [portalTab, setPortalTab] = useState('signin');

  const { login, register } = useAuth();

  const onTabChange = useCallback((v: string) => {
    setPortalTab(v);
    setError('');
  }, []);
  const navigate = useNavigate();

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password, selectedRole);
      toast.success('Login successful!');
      navigate('/dashboard');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed. Please check your credentials.';
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (regPassword.length < 8) {
      setError('Password must be at least 8 characters');
      toast.error('Password must be at least 8 characters');
      return;
    }
    if (regPassword !== regConfirm) {
      setError('Passwords do not match');
      toast.error('Passwords do not match');
      return;
    }
    const y = yearOfStudy.trim();
    let yearNum: number | undefined;
    if (y) {
      const n = parseInt(y, 10);
      if (Number.isNaN(n) || n < 1 || n > 20) {
        setError('Year of study must be between 1 and 20 (or leave blank)');
        toast.error('Invalid year of study');
        return;
      }
      yearNum = n;
    }

    setIsLoading(true);
    try {
      await register({
        name: regName.trim(),
        email: regEmail.trim(),
        password: regPassword,
        role: selectedRole,
        institution: institution.trim() || undefined,
        country: country.trim() || undefined,
        majorDepartment: majorDepartment.trim() || undefined,
        yearOfStudy: yearNum,
        gender: gender === '_none' ? undefined : gender,
        studentId: studentId.trim() || undefined,
        dateOfBirth: dateOfBirth || undefined,
      });
      toast.success('Account created — welcome!');
      navigate('/dashboard');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-primary/5 p-4 py-10">
      <div className="w-full max-w-lg space-y-8 animate-fade-up">
        <div className="text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-primary shadow-glow mb-4">
            <GraduationCap className="h-8 w-8 text-primary-foreground" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">MathGrade</h1>
          <p className="text-muted-foreground mt-2">Exam Grading System</p>
        </div>

        <Card className="border-border/50 shadow-xl">
          <CardHeader className="space-y-1 pb-2">
            <CardTitle className="text-xl">Account portal</CardTitle>
            <CardDescription>Sign in with your credentials or create an account with your profile details</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={portalTab} onValueChange={onTabChange} className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="signin">Sign in</TabsTrigger>
                <TabsTrigger value="register">Create account</TabsTrigger>
              </TabsList>

              <div className="grid grid-cols-3 gap-2 mb-6">
                {roles.map((role) => {
                  const Icon = role.icon;
                  const isSelected = selectedRole === role.value;
                  return (
                    <button
                      key={role.value}
                      type="button"
                      onClick={() => setSelectedRole(role.value)}
                      className={cn(
                        'flex flex-col items-center gap-2 p-3 rounded-xl border-2 transition-all duration-200',
                        isSelected
                          ? 'border-primary bg-primary/5 shadow-glow'
                          : 'border-border hover:border-primary/50 hover:bg-muted/50'
                      )}
                    >
                      <Icon className={cn('h-5 w-5', isSelected ? 'text-primary' : 'text-muted-foreground')} />
                      <span className={cn('text-xs font-medium text-center', isSelected ? 'text-primary' : 'text-muted-foreground')}>
                        {role.label}
                      </span>
                    </button>
                  );
                })}
              </div>

              <TabsContent value="signin" className="mt-0 space-y-4">
                <form onSubmit={handleSignIn} className="space-y-4">
                  {error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="you@university.edu"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="h-11"
                      required
                      disabled={isLoading}
                      autoComplete="email"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="h-11"
                      required
                      disabled={isLoading}
                      autoComplete="current-password"
                    />
                  </div>
                  <Button type="submit" className="w-full h-11 font-semibold" disabled={isLoading}>
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Signing in…
                      </>
                    ) : (
                      `Sign in as ${roles.find((r) => r.value === selectedRole)?.label ?? 'user'}`
                    )}
                  </Button>
                </form>
                <p className="text-center text-sm text-muted-foreground pt-2">
                  Demo: professor@university.edu / password (match role above)
                </p>
              </TabsContent>

              <TabsContent value="register" className="mt-0">
                <form onSubmit={handleRegister} className="space-y-4">
                  {error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor="reg-name">Full name</Label>
                      <Input
                        id="reg-name"
                        value={regName}
                        onChange={(e) => setRegName(e.target.value)}
                        className="h-11"
                        required
                        disabled={isLoading}
                        autoComplete="name"
                        placeholder="Jane Doe"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="reg-email">Email</Label>
                      <Input
                        id="reg-email"
                        type="email"
                        value={regEmail}
                        onChange={(e) => setRegEmail(e.target.value)}
                        className="h-11"
                        required
                        disabled={isLoading}
                        autoComplete="email"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="reg-student-id">Student / staff ID</Label>
                      <Input
                        id="reg-student-id"
                        value={studentId}
                        onChange={(e) => setStudentId(e.target.value)}
                        className="h-11"
                        disabled={isLoading}
                        placeholder="Optional"
                        autoComplete="off"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="reg-password">Password</Label>
                      <Input
                        id="reg-password"
                        type="password"
                        value={regPassword}
                        onChange={(e) => setRegPassword(e.target.value)}
                        className="h-11"
                        required
                        minLength={8}
                        disabled={isLoading}
                        autoComplete="new-password"
                        placeholder="At least 8 characters"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="reg-confirm">Confirm password</Label>
                      <Input
                        id="reg-confirm"
                        type="password"
                        value={regConfirm}
                        onChange={(e) => setRegConfirm(e.target.value)}
                        className="h-11"
                        required
                        disabled={isLoading}
                        autoComplete="new-password"
                      />
                    </div>
                  </div>

                  <Separator className="my-2" />
                  <p className="text-sm font-medium text-foreground">Demographics</p>
                  <p className="text-xs text-muted-foreground -mt-2">
                    Optional fields help your institution with reporting; you can update them later in Profile.
                  </p>

                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor="institution">School or institution</Label>
                      <Input
                        id="institution"
                        value={institution}
                        onChange={(e) => setInstitution(e.target.value)}
                        className="h-11"
                        disabled={isLoading}
                        placeholder="e.g. State University"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="country">Country / region</Label>
                      <Input
                        id="country"
                        value={country}
                        onChange={(e) => setCountry(e.target.value)}
                        className="h-11"
                        disabled={isLoading}
                        placeholder="Optional"
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
                        className="h-11"
                        disabled={isLoading}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="major">Major / department</Label>
                      <Input
                        id="major"
                        value={majorDepartment}
                        onChange={(e) => setMajorDepartment(e.target.value)}
                        className="h-11"
                        disabled={isLoading}
                        placeholder="e.g. Mathematics"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="year">Year of study</Label>
                      <Input
                        id="year"
                        inputMode="numeric"
                        value={yearOfStudy}
                        onChange={(e) => setYearOfStudy(e.target.value.replace(/\D/g, ''))}
                        className="h-11"
                        disabled={isLoading}
                        placeholder="1–20, optional"
                      />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label>Gender</Label>
                      <Select value={gender} onValueChange={setGender} disabled={isLoading}>
                        <SelectTrigger className="h-11">
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
                  </div>

                  <Button type="submit" className="w-full h-11 font-semibold" disabled={isLoading}>
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Creating account…
                      </>
                    ) : (
                      `Create account as ${roles.find((r) => r.value === selectedRole)?.label ?? 'user'}`
                    )}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
