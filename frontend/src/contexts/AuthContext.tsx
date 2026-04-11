import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { User, UserRole } from '@/types';
import { authAPI, type RegisterRequest } from '@/lib/api';

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string, role: UserRole) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  updateProfile: (data: {
    name?: string;
    email?: string;
    currentPassword?: string;
    newPassword?: string;
    institution?: string;
    country?: string;
    majorDepartment?: string;
    yearOfStudy?: number | null;
    gender?: string;
    studentId?: string;
    dateOfBirth?: string | null;
  }) => Promise<void>;
  uploadAvatar: (file: File) => Promise<void>;
  removeAvatar: () => Promise<void>;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

function mapApiUser(userData: Record<string, unknown>): User {
  const ys = userData.yearOfStudy;
  return {
    id: userData.id as string,
    name: userData.name as string,
    email: userData.email as string,
    role: userData.role as User['role'],
    avatar: userData.avatar as string | undefined,
    createdAt: new Date(userData.createdAt as string),
    institution: (userData.institution as string | undefined) || undefined,
    country: (userData.country as string | undefined) || undefined,
    majorDepartment: (userData.majorDepartment as string | undefined) || undefined,
    yearOfStudy: typeof ys === 'number' && !Number.isNaN(ys) ? ys : undefined,
    gender: (userData.gender as string | undefined) || undefined,
    studentId: (userData.studentId as string | undefined) || undefined,
    dateOfBirth:
      typeof userData.dateOfBirth === 'string' ? userData.dateOfBirth : undefined,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing token on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
          
          if (response.ok) {
            const userData = await response.json();
            setUser(mapApiUser(userData));
          } else {
            localStorage.removeItem('auth_token');
          }
        } catch (error) {
          console.error('Auth check failed:', error);
          localStorage.removeItem('auth_token');
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string, role: UserRole) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, role }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      localStorage.setItem('auth_token', data.access_token);
      
      setUser(mapApiUser(data.user as Record<string, unknown>));
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterRequest) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        const detail = errBody.detail;
        const message =
          typeof detail === 'string'
            ? detail
            : Array.isArray(detail)
              ? detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ')
              : 'Registration failed';
        throw new Error(message || 'Registration failed');
      }

      const res = await response.json();
      localStorage.setItem('auth_token', res.access_token);
      setUser(mapApiUser(res.user as Record<string, unknown>));
    } catch (error) {
      console.error('Register error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setUser(null);
  };

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) return;
    const userData = (await authAPI.getMe()) as Record<string, unknown>;
    setUser(mapApiUser(userData));
  }, []);

  const updateProfile = useCallback(async (data: {
    name?: string;
    email?: string;
    currentPassword?: string;
    newPassword?: string;
    institution?: string;
    country?: string;
    majorDepartment?: string;
    yearOfStudy?: number | null;
    gender?: string;
    studentId?: string;
    dateOfBirth?: string | null;
  }) => {
    const userData = (await authAPI.updateMe({
      name: data.name,
      email: data.email,
      current_password: data.currentPassword,
      new_password: data.newPassword,
      institution: data.institution,
      country: data.country,
      majorDepartment: data.majorDepartment,
      yearOfStudy: data.yearOfStudy,
      gender: data.gender,
      studentId: data.studentId,
      dateOfBirth: data.dateOfBirth,
    })) as Record<string, unknown>;
    setUser(mapApiUser(userData));
  }, []);

  const uploadAvatar = useCallback(async (file: File) => {
    const userData = (await authAPI.uploadAvatar(file)) as Record<string, unknown>;
    setUser(mapApiUser(userData));
  }, []);

  const removeAvatar = useCallback(async () => {
    const userData = (await authAPI.deleteAvatar()) as Record<string, unknown>;
    setUser(mapApiUser(userData));
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        register,
        logout,
        refreshUser,
        updateProfile,
        uploadAvatar,
        removeAvatar,
        isAuthenticated: !!user,
        isLoading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}