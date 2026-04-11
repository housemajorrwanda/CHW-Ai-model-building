import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Stable display for fractional points (avoids 7.170000000000001 in UI). */
export function formatScoreDisplay(score: number | null | undefined): string | null {
  if (score == null || Number.isNaN(score)) return null;
  const r = Math.round(score * 100) / 100;
  if (Number.isInteger(r)) return String(r);
  return r.toFixed(2).replace(/\.?0+$/, '');
}
