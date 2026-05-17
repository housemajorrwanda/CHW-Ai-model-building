import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  variant?: 'default' | 'primary' | 'accent' | 'warning' | 'softRose' | 'softApricot' | 'softLilac' | 'softSky';
}

export function StatsCard({ title, value, subtitle, icon: Icon, trend, variant = 'default' }: StatsCardProps) {
  const variants = {
    default:
      'border-slate-200/90 bg-gradient-to-br from-slate-50/90 to-card dark:from-slate-950/40 dark:border-slate-800',
    primary:
      'border-violet-200/90 bg-gradient-to-br from-violet-50/95 to-violet-100/20 dark:from-violet-950/50 dark:border-violet-900/60',
    accent:
      'border-emerald-200/90 bg-gradient-to-br from-emerald-50/95 to-teal-50/30 dark:from-emerald-950/40 dark:border-emerald-900/50',
    warning:
      'border-amber-200/90 bg-gradient-to-br from-amber-50/95 to-orange-50/20 dark:from-amber-950/30 dark:border-amber-900/50',
    softRose:
      'border-rose-200/80 bg-gradient-to-br from-rose-50/95 via-white to-rose-50/40 dark:from-rose-950/35 dark:border-rose-900/45',
    softApricot:
      'border-orange-200/70 bg-gradient-to-br from-orange-50/90 via-white to-amber-50/35 dark:from-orange-950/30 dark:border-orange-900/40',
    softLilac:
      'border-violet-200/70 bg-gradient-to-br from-violet-50/80 via-white to-fuchsia-50/25 dark:from-violet-950/35 dark:border-violet-900/45',
    softSky:
      'border-sky-200/75 bg-gradient-to-br from-sky-50/90 via-white to-cyan-50/30 dark:from-sky-950/30 dark:border-sky-900/40',
  };

  const iconVariants = {
    default: 'bg-slate-200/80 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
    primary: 'bg-violet-600 text-white shadow-md shadow-violet-500/25',
    accent: 'bg-emerald-600 text-white shadow-md shadow-emerald-500/25',
    warning: 'bg-amber-500 text-white shadow-md shadow-amber-500/25',
    softRose: 'bg-rose-400/90 text-white shadow-sm dark:bg-rose-600/80',
    softApricot: 'bg-orange-400/90 text-white shadow-sm dark:bg-orange-600/80',
    softLilac: 'bg-violet-500/90 text-white shadow-sm dark:bg-violet-600/80',
    softSky: 'bg-sky-500/90 text-white shadow-sm dark:bg-sky-600/80',
  };

  return (
    <div
      className={cn(
        'rounded-2xl border-2 p-5 shadow-sm transition-all duration-300 hover:shadow-md md:p-6 animate-fade-up',
        variants[variant]
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground md:text-sm">{title}</p>
          <p className="text-3xl font-bold tabular-nums tracking-tight md:text-4xl">{value}</p>
          {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
          {trend && (
            <p className={cn('text-sm font-medium', trend.isPositive ? 'text-emerald-600' : 'text-destructive')}>
              {trend.isPositive ? '+' : ''}
              {trend.value}% from last week
            </p>
          )}
        </div>
        <div className={cn('shrink-0 rounded-xl p-3.5', iconVariants[variant])}>
          <Icon className="h-5 w-5 md:h-6 md:w-6" />
        </div>
      </div>
    </div>
  );
}