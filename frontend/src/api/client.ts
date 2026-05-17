/**
 * API Client
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Token management
let authToken: string | null = null;

export const setAuthToken = (token: string | null) => {
  authToken = token;
  if (token) {
    localStorage.setItem('auth_token', token);
  } else {
    localStorage.removeItem('auth_token');
  }
};

export const getAuthToken = (): string | null => {
  if (!authToken) {
    authToken = localStorage.getItem('auth_token');
  }
  return authToken;
};

// Helper function for API calls
async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  
  const headers: HeadersInit = {
    ...options.headers,
  };

  // Add auth token if available
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Add Content-Type for JSON if body is present and not FormData
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

// ============================================================================
// Authentication API
// ============================================================================

export interface LoginRequest {
  email: string;
  password: string;
  role: 'professor' | 'student' | 'admin';
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    name: string;
    email: string;
    role: string;
    avatar?: string;
    createdAt: string;
  };
}

export const authAPI = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await apiCall<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    
    // Store token
    setAuthToken(response.access_token);
    
    return response;
  },

  async register(userData: {
    name: string;
    email: string;
    password: string;
    role: string;
  }): Promise<LoginResponse> {
    const response = await apiCall<LoginResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
    
    setAuthToken(response.access_token);
    
    return response;
  },

  async getMe() {
    return apiCall('/auth/me');
  },

  logout() {
    setAuthToken(null);
  },
};

// ============================================================================
// Courses API
// ============================================================================

export const coursesAPI = {
  async getAll() {
    return apiCall('/courses');
  },

  async getById(courseId: string) {
    return apiCall(`/courses/${courseId}`);
  },

  async getEnrolled() {
    return apiCall('/courses/enrolled');
  },

  async create(courseData: {
    name: string;
    code: string;
    description?: string;
    level?: string;
    topics?: any[];
  }) {
    return apiCall('/courses', {
      method: 'POST',
      body: JSON.stringify(courseData),
    });
  },

  async update(courseId: string, courseData: {
    name?: string;
    code?: string;
    description?: string;
    level?: string;
  }) {
    return apiCall(`/courses/${courseId}`, {
      method: 'PUT',
      body: JSON.stringify(courseData),
    });
  },

  async requestEnrollment(courseId: string) {
    return apiCall(`/courses/${courseId}/enroll`, {
      method: 'POST',
    });
  },

  async approveEnrollment(courseId: string, enrollmentId: string) {
    return apiCall(`/courses/${courseId}/enrollments/${enrollmentId}/approve`, {
      method: 'POST',
    });
  },

  async rejectEnrollment(courseId: string, enrollmentId: string) {
    return apiCall(`/courses/${courseId}/enrollments/${enrollmentId}/reject`, {
      method: 'POST',
    });
  },

  async removeStudent(courseId: string, enrollmentId: string) {
    return apiCall(`/courses/${courseId}/enrollments/${enrollmentId}`, {
      method: 'DELETE',
    });
  },
};

// ============================================================================
// Exams API
// ============================================================================

export const examsAPI = {
  async getAll(courseId?: string) {
    const query = courseId ? `?course_id=${courseId}` : '';
    return apiCall(`/exams${query}`);
  },

  async getById(examId: string) {
    return apiCall(`/exams/${examId}`);
  },

  async create(examData: any) {
    return apiCall('/exams', {
      method: 'POST',
      body: JSON.stringify(examData),
    });
  },

  async update(examId: string, examData: any) {
    return apiCall(`/exams/${examId}`, {
      method: 'PUT',
      body: JSON.stringify(examData),
    });
  },

  async delete(examId: string) {
    return apiCall(`/exams/${examId}`, { method: 'DELETE' });
  },

  async publish(examId: string) {
    return apiCall(`/exams/${examId}/publish`, { method: 'POST' });
  },

  async unpublish(examId: string) {
    return apiCall(`/exams/${examId}/unpublish`, { method: 'POST' });
  },
};

// ============================================================================
// Submissions API
// ============================================================================

export const submissionsAPI = {
  async getAll(filters?: { examId?: string; status?: string }) {
    let query = '';
    if (filters) {
      const params = new URLSearchParams();
      if (filters.examId) params.append('exam_id', filters.examId);
      if (filters.status) params.append('status', filters.status);
      query = params.toString() ? `?${params.toString()}` : '';
    }
    return apiCall(`/submissions${query}`);
  },

  async getById(submissionId: string) {
    return apiCall(`/submissions/${submissionId}`);
  },

  async submit(examId: string, images: File[]) {
    const formData = new FormData();
    formData.append('exam_id', examId);
    
    images.forEach((image) => {
      formData.append('images', image);
    });

    return apiCall('/submissions', {
      method: 'POST',
      body: formData,
    });
  },

  async grade(submissionId: string) {
    return apiCall(`/submissions/${submissionId}/grade`, {
      method: 'POST',
    });
  },
};

// ============================================================================
// Dashboard API
// ============================================================================

export const dashboardAPI = {
  async getStats() {
    return apiCall('/dashboard/stats');
  },

  async getAnalytics() {
    return apiCall('/dashboard/analytics');
  },
};

// ============================================================================
// Course announcements
// ============================================================================

export type AnnouncementReactionKind = 'like' | 'improve' | 'implement';

export interface AnnouncementComment {
  id: string;
  authorId: string;
  authorName: string;
  body: string;
  createdAt: string;
}

export interface CourseAnnouncement {
  id: string;
  courseId: string;
  authorId: string;
  authorName: string;
  title: string;
  body: string;
  pinned: boolean;
  createdAt: string;
  likeCount: number;
  improveCount: number;
  implementCount: number;
  commentCount: number;
  myLiked: boolean;
  myImprove: boolean;
  myImplement: boolean;
  comments: AnnouncementComment[];
}

export const announcementsAPI = {
  async list(courseId: string) {
    return apiCall<CourseAnnouncement[]>(`/courses/${encodeURIComponent(courseId)}/announcements`);
  },

  async create(
    courseId: string,
    payload: { title: string; body: string; pinned?: boolean }
  ) {
    return apiCall<CourseAnnouncement>(`/courses/${encodeURIComponent(courseId)}/announcements`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async update(
    courseId: string,
    announcementId: string,
    payload: { title?: string; body?: string; pinned?: boolean }
  ) {
    return apiCall<CourseAnnouncement>(
      `/courses/${encodeURIComponent(courseId)}/announcements/${encodeURIComponent(announcementId)}`,
      { method: 'PATCH', body: JSON.stringify(payload) }
    );
  },

  async remove(courseId: string, announcementId: string) {
    return apiCall<{ message: string }>(
      `/courses/${encodeURIComponent(courseId)}/announcements/${encodeURIComponent(announcementId)}`,
      { method: 'DELETE' }
    );
  },

  async toggleReaction(courseId: string, announcementId: string, kind: AnnouncementReactionKind) {
    return apiCall<CourseAnnouncement>(
      `/courses/${encodeURIComponent(courseId)}/announcements/${encodeURIComponent(announcementId)}/reactions/toggle`,
      { method: 'POST', body: JSON.stringify({ kind }) }
    );
  },

  async addComment(courseId: string, announcementId: string, body: string) {
    return apiCall<CourseAnnouncement>(
      `/courses/${encodeURIComponent(courseId)}/announcements/${encodeURIComponent(announcementId)}/comments`,
      { method: 'POST', body: JSON.stringify({ body }) }
    );
  },

  async deleteComment(courseId: string, announcementId: string, commentId: string) {
    return apiCall<CourseAnnouncement>(
      `/courses/${encodeURIComponent(courseId)}/announcements/${encodeURIComponent(announcementId)}/comments/${encodeURIComponent(commentId)}`,
      { method: 'DELETE' }
    );
  },
};

// ============================================================================
// Notifications API
// ============================================================================

export const notificationsAPI = {
  async getFeed(limit = 80) {
    return apiCall(`/notifications?limit=${limit}`);
  },

  async markRead(notificationId: string) {
    return apiCall(`/notifications/${encodeURIComponent(notificationId)}/read`, {
      method: 'PATCH',
    });
  },

  async markAllRead() {
    return apiCall('/notifications/read-all', { method: 'POST' });
  },
};

// ============================================================================
// Reminders API (personal schedule from bell)
// ============================================================================

export const remindersAPI = {
  async getDue() {
    return apiCall('/reminders/due');
  },

  async schedule(payload: {
    sourceKey: string;
    title: string;
    body?: string;
    link?: string;
    userNote?: string;
    remindAt: string;
    repeat: 'none' | 'daily' | 'weekly' | 'monthly';
  }) {
    return apiCall<{ id: string }>('/reminders/schedule', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async acknowledge(reminderId: string) {
    return apiCall<{ ok: boolean }>(
      `/reminders/scheduled/${encodeURIComponent(reminderId)}/acknowledge`,
      { method: 'POST' }
    );
  },
};

// ============================================================================
// Export all
// ============================================================================

export const api = {
  auth: authAPI,
  courses: coursesAPI,
  announcements: announcementsAPI,
  exams: examsAPI,
  submissions: submissionsAPI,
  dashboard: dashboardAPI,
  notifications: notificationsAPI,
  reminders: remindersAPI,
};

export default api;

