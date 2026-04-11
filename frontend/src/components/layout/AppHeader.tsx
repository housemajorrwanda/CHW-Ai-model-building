import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { resolveAvatarUrl } from '@/lib/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  GraduationCap,
  LayoutDashboard,
  BookOpen,
  FileText,
  Users,
  LogOut,
  Menu,
  Search,
  ClipboardList,
  BarChart3,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';

const professorNav = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
  { label: 'My Courses', icon: BookOpen, path: '/courses' },
  { label: 'Exams', icon: FileText, path: '/exams' },
  { label: 'Submissions', icon: ClipboardList, path: '/submissions' },
];

const studentNav = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
  { label: 'Browse Courses', icon: Search, path: '/browse-courses' },
  { label: 'My Exams', icon: FileText, path: '/my-exams' },
  { label: 'My Results', icon: BarChart3, path: '/my-results' },
];

const adminNav = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
  { label: 'Users', icon: Users, path: '/users' },
];

export function AppHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const navItems =
    user?.role === 'student' ? studentNav : user?.role === 'admin' ? adminNav : professorNav;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getInitials = (name: string) =>
    name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase();

  const isNavActive = (path: string) => {
    if (path === '/dashboard') return location.pathname === '/dashboard';
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  const NavItems = ({ mobile = false }: { mobile?: boolean }) => (
    <nav className={cn('flex gap-1', mobile ? 'flex-col' : 'flex-row')}>
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = isNavActive(item.path);
        return (
          <Button
            key={item.path}
            variant={isActive ? 'default' : 'ghost'}
            className={cn('justify-start', mobile && 'w-full', !isActive && 'hover:bg-accent')}
            onClick={() => navigate(item.path)}
          >
            <Icon className="mr-2 h-4 w-4" />
            {item.label}
          </Button>
        );
      })}
    </nav>
  );

  return (
    <header className="sticky top-0 z-30 w-full border-b bg-background/95 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="flex h-16 items-center justify-between gap-4 px-4 md:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-6 md:gap-8">
          <button
            type="button"
            className="flex shrink-0 cursor-pointer items-center gap-2"
            onClick={() => navigate('/dashboard')}
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <GraduationCap className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="hidden text-xl font-bold sm:inline-block">MathGrade</span>
          </button>

          <div className="hidden min-w-0 md:flex">
            <NavItems />
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <Sheet>
            <SheetTrigger asChild className="md:hidden">
              <Button variant="ghost" size="icon" aria-label="Open menu">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[min(100vw,20rem)]">
              <div className="mb-6 flex items-center gap-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
                  <GraduationCap className="h-5 w-5 text-primary-foreground" />
                </div>
                <span className="text-xl font-bold">MathGrade</span>
              </div>
              <NavItems mobile />
            </SheetContent>
          </Sheet>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-10 gap-2">
                <Avatar className="h-8 w-8 border border-border">
                  <AvatarImage
                    src={resolveAvatarUrl(user?.avatar)}
                    alt=""
                    className="object-cover"
                  />
                  <AvatarFallback className="bg-primary text-sm text-primary-foreground">
                    {user?.name ? getInitials(user.name) : 'U'}
                  </AvatarFallback>
                </Avatar>
                <span className="hidden max-w-[140px] truncate text-sm font-medium sm:inline-block">
                  {user?.name}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{user?.name}</p>
                  <p className="text-xs leading-none text-muted-foreground">{user?.email}</p>
                  <p className="mt-1 text-xs capitalize leading-none text-muted-foreground">{user?.role}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout}>
                <LogOut className="mr-2 h-4 w-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
