/**
 * API Client - Centralized API calls with authentication
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Helper function to get auth token
function getAuthToken(): string | null {
  return localStorage.getItem('auth_token');
}

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
  role: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
  role: string;
}

export const authAPI = {
  async login(credentials: LoginRequest) {
    return apiCall('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  },

  async register(userData: RegisterRequest) {
    return apiCall('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  },

  async getMe() {
    return apiCall('/auth/me');
  },
};

// ============================================================================
// Courses API
// ============================================================================

export const coursesAPI = {
  async getAll() {
    return apiCall('/courses');
  },

  async getEnrolled() {
    return apiCall('/courses/enrolled');
  },

  async getById(courseId: string) {
    return apiCall(`/courses/${courseId}`);
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

  async publish(examId: string) {
    return apiCall(`/exams/${examId}/publish`, {
      method: 'POST',
    });
  },

  async unpublish(examId: string) {
    return apiCall(`/exams/${examId}/unpublish`, {
      method: 'POST',
    });
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

  async submit(examId: string, images: File[], answers?: any[]) {
    const formData = new FormData();
    formData.append('exam_id', examId);
    
    // Add typed answers if provided
    if (answers) {
      formData.append('answers', JSON.stringify(answers));
    }
    
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
};

