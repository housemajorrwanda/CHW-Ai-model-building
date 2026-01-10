import { ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
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
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';

interface MainLayoutProps {
  children: ReactNode;
}

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
  { label: 'My Results', icon: ClipboardList, path: '/my-results' },
];

export default function MainLayout({ children }: MainLayoutProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = user?.role === 'student' ? studentNav : professorNav;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase();
  };

  const NavItems = ({ mobile = false }: { mobile?: boolean }) => (
    <nav className={cn('flex gap-1', mobile ? 'flex-col' : 'flex-row')}>
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = location.pathname === item.path;
        return (
          <Button
            key={item.path}
            variant={isActive ? 'default' : 'ghost'}
            className={cn(
              'justify-start',
              mobile && 'w-full',
              !isActive && 'hover:bg-accent'
            )}
            onClick={() => navigate(item.path)}
          >
            <Icon className="h-4 w-4 mr-2" />
            {item.label}
          </Button>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/dashboard')}>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
                <GraduationCap className="h-5 w-5 text-primary-foreground" />
              </div>
              <span className="text-xl font-bold hidden sm:inline-block">MathGrade</span>
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex">
              <NavItems />
            </div>
          </div>

          {/* Right Side */}
          <div className="flex items-center gap-2">
            {/* Mobile Menu */}
            <Sheet>
              <SheetTrigger asChild className="md:hidden">
                <Button variant="ghost" size="icon">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left">
                <div className="flex items-center gap-2 mb-6">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
                    <GraduationCap className="h-5 w-5 text-primary-foreground" />
                  </div>
                  <span className="text-xl font-bold">MathGrade</span>
                </div>
                <NavItems mobile />
              </SheetContent>
            </Sheet>

            {/* User Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-10 gap-2">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary text-primary-foreground text-sm">
                      {user?.name ? getInitials(user.name) : 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <span className="hidden sm:inline-block text-sm font-medium">
                    {user?.name}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{user?.name}</p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user?.email}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground capitalize mt-1">
                      {user?.role}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container py-6">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row">
          <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
            {/* Footer content can be added here */}
          </p>
        </div>
      </footer>
    </div>
  );
}

