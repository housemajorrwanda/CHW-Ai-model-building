import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import {
  LayoutDashboard,
  BookOpen,
  FileText,
  Users,
  LogOut,
  GraduationCap,
  BarChart3,
  ClipboardList,
  User,
  Settings,
  LineChart,
  Megaphone,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { resolveAvatarUrl } from '@/lib/avatar';

const professorLinks = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/analytics', icon: LineChart, label: 'Analytics' },
  { to: '/courses', icon: BookOpen, label: 'Courses' },
  { to: '/announcements', icon: Megaphone, label: 'Announcements' },
  { to: '/exams', icon: FileText, label: 'Exams' },
  { to: '/submissions', icon: ClipboardList, label: 'Submissions' },
  { to: '/settings', icon: Settings, label: 'Settings' },
  { to: '/profile', icon: User, label: 'Profile' },
];

const studentLinks = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/analytics', icon: LineChart, label: 'Analytics' },
  { to: '/browse-courses', icon: BookOpen, label: 'Browse Courses' },
  { to: '/announcements', icon: Megaphone, label: 'Announcements' },
  { to: '/my-exams', icon: FileText, label: 'My Exams' },
  { to: '/my-results', icon: BarChart3, label: 'My Results' },
  { to: '/settings', icon: Settings, label: 'Settings' },
  { to: '/profile', icon: User, label: 'Profile' },
];

const adminLinks = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/users', icon: Users, label: 'Users' },
  { to: '/all-courses', icon: BookOpen, label: 'All Courses' },
  { to: '/announcements', icon: Megaphone, label: 'Announcements' },
  { to: '/analytics', icon: LineChart, label: 'Analytics' },
  { to: '/settings', icon: Settings, label: 'Settings' },
  { to: '/profile', icon: User, label: 'Profile' },
];

export function Sidebar() {
  const location = useLocation();
  const { user, logout } = useAuth();

  const links = user?.role === 'professor' 
    ? professorLinks 
    : user?.role === 'student' 
    ? studentLinks 
    : adminLinks;

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 bg-sidebar border-r border-sidebar-border">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
            <GraduationCap className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-sidebar-foreground">MathGrade</h1>
            <p className="text-xs text-sidebar-foreground/60">Exam grading</p>
          </div>
        </div>

        {/* User — opens profile */}
        <div className="border-b border-sidebar-border p-3">
          <Link
            to="/profile"
            className="flex items-center gap-3 rounded-lg p-2 transition-colors hover:bg-sidebar-accent/50"
          >
            <Avatar className="h-10 w-10 shrink-0 border border-sidebar-border">
              <AvatarImage
                src={resolveAvatarUrl(user?.avatar)}
                alt=""
                className="object-cover"
              />
              <AvatarFallback className="bg-sidebar-accent text-sidebar-accent-foreground text-sm font-medium">
                {user?.name?.charAt(0) || 'U'}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-sidebar-foreground">{user?.name}</p>
              <p className="text-xs capitalize text-sidebar-foreground/60">{user?.role}</p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-3">
          {user?.role === 'student' && (
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-sidebar-foreground/45">
              Workspace
            </p>
          )}
          {links.map((link) => {
            const isCourses = link.to === '/courses';
            const isAnnouncements = link.to === '/announcements';
            const isActive =
              location.pathname === link.to ||
              (isAnnouncements && location.pathname.endsWith('/announcements')) ||
              (isCourses &&
                location.pathname.startsWith('/courses') &&
                !location.pathname.includes('/announcements')) ||
              (!isAnnouncements &&
                !isCourses &&
                link.to !== '/dashboard' &&
                location.pathname.startsWith(`${link.to}/`));
            return (
              <Link
                key={link.to}
                to={link.to}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-glow'
                    : 'text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
                )}
              >
                <link.icon className="h-4 w-4" />
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Bottom Actions */}
        <div className="border-t border-sidebar-border p-3 space-y-1">
          <Button
            variant="ghost"
            onClick={logout}
            className="w-full justify-start gap-3 px-3 py-2.5 text-sm font-medium text-sidebar-foreground/70 hover:bg-destructive/10 hover:text-destructive"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </div>
      </div>
    </aside>
  );
}