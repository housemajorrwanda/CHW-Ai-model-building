import { ReactNode } from 'react';
import { AppHeader } from './AppHeader';

interface MainLayoutProps {
  children: ReactNode;
}

/** Legacy shell: top header + container (no sidebar). Prefer DashboardLayout for app pages. */
export default function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="container py-6">{children}</main>
      <footer className="border-t py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row">
          <p className="text-center text-sm leading-loose text-muted-foreground md:text-left" />
        </div>
      </footer>
    </div>
  );
}
