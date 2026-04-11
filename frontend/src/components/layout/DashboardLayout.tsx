import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import { Sidebar } from './Sidebar';
import { AppHeader } from './AppHeader';

interface DashboardLayoutProps {
  children: ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { prefs } = useUserSettings();

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div className="flex min-h-screen flex-col pl-64">
        <AppHeader />
        <main
          className={cn(
            'flex-1',
            prefs.comfortableDensity ? 'p-7 md:p-10' : 'p-6 md:p-8'
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}