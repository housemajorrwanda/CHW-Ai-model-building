import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  loadUserSettings,
  saveUserSettings,
  type UserPreferenceSettings,
} from '@/lib/user-settings';

type UserSettingsContextValue = {
  prefs: UserPreferenceSettings;
  setPrefs: (patch: Partial<UserPreferenceSettings>) => void;
};

const UserSettingsContext = createContext<UserSettingsContextValue | null>(null);

export function UserSettingsProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefsState] = useState<UserPreferenceSettings>(() => loadUserSettings());

  const setPrefs = useCallback((patch: Partial<UserPreferenceSettings>) => {
    setPrefsState((prev) => {
      const next = { ...prev, ...patch };
      saveUserSettings(next);
      return next;
    });
  }, []);

  const value = useMemo(() => ({ prefs, setPrefs }), [prefs, setPrefs]);

  return (
    <UserSettingsContext.Provider value={value}>{children}</UserSettingsContext.Provider>
  );
}

export function useUserSettings() {
  const ctx = useContext(UserSettingsContext);
  if (!ctx) {
    throw new Error('useUserSettings must be used within UserSettingsProvider');
  }
  return ctx;
}
