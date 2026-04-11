const STORAGE_KEY = 'mathgrade-user-settings';

export type UserPreferenceSettings = {
  /** Notify when a graded submission is available */
  notifyGradeAvailable: boolean;
  /** Reminders before an exam window closes */
  remindExamDeadlines: boolean;
  /** Softer UI density in main content areas */
  comfortableDensity: boolean;
};

const defaults: UserPreferenceSettings = {
  notifyGradeAvailable: true,
  remindExamDeadlines: true,
  comfortableDensity: false,
};

export function loadUserSettings(): UserPreferenceSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...defaults };
    const parsed = JSON.parse(raw) as Partial<UserPreferenceSettings>;
    return { ...defaults, ...parsed };
  } catch {
    return { ...defaults };
  }
}

export function saveUserSettings(next: UserPreferenceSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* ignore quota / private mode */
  }
}
