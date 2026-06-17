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
  institution?: string;
  country?: string;
  majorDepartment?: string;
  yearOfStudy?: number;
  gender?: string;
  studentId?: string;
  /** YYYY-MM-DD */
  dateOfBirth?: string;
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

  async uploadAvatar(file: File) {
    const token = getAuthToken();
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/auth/me/avatar`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Upload failed' }));
      const d = err.detail;
      throw new Error(typeof d === 'string' ? d : 'Upload failed');
    }
    return response.json();
  },

  async deleteAvatar() {
    return apiCall('/auth/me/avatar', { method: 'DELETE' });
  },

  async updateMe(body: {
    name?: string;
    email?: string;
    current_password?: string;
    new_password?: string;
    institution?: string;
    country?: string;
    majorDepartment?: string;
    yearOfStudy?: number | null;
    gender?: string;
    studentId?: string;
    dateOfBirth?: string | null;
    remindExamDeadlinesEnabled?: boolean;
    remindExamOffsetsHours?: number[];
    remindTeachingDeadlinesEnabled?: boolean;
  }) {
    return apiCall('/auth/me', {
      method: 'PUT',
      body: JSON.stringify(body),
    });
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

export const attachmentsAPI = {
  async upload(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    
    const token = getAuthToken();
    const headers: HeadersInit = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE_URL}/attachments/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }
    
    return response.json();
  },
};

export const examsAPI = {
  async getAll(courseId?: string) {
    const query = courseId ? `?course_id=${courseId}` : '';
    return apiCall(`/exams${query}`);
  },

  async getById(examId: string) {
    return apiCall<ExamDetail>(`/exams/${examId}`);
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
    return apiCall(`/exams/${examId}/publish`, {
      method: 'POST',
    });
  },

  async unpublish(examId: string) {
    return apiCall(`/exams/${examId}/unpublish`, {
      method: 'POST',
    });
  },

  async downloadPDF(
    examId: string,
    includeSolutions: boolean = false,
    paper: 'a4' | 'letter' | 'legal' = 'letter'
  ) {
    const token = getAuthToken();
    const response = await fetch(
      `${API_BASE_URL}/exams/${examId}/download?include_solutions=${includeSolutions}&paper=${encodeURIComponent(paper)}&t=${Date.now()}`,
      { headers: { 'Authorization': `Bearer ${token}`, 'Cache-Control': 'no-cache' } }
    );
    if (!response.ok) throw new Error('Failed to download PDF');
    return response.blob();
  },

  async upload(formData: FormData) {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/exams/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to upload exam');
    }
    return response.json();
  },

  /** Preview how a separate answer-key file aligns to existing exam questions. */
  async previewAnswerKey(examId: string, file: File) {
    const token = getAuthToken();
    const formData = new FormData();
    formData.append('file', file, file.name);
    const response = await fetch(`${API_BASE_URL}/exams/${examId}/preview-answer-key`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(typeof err.detail === 'string' ? err.detail : 'Answer key preview failed');
    }
    return response.json() as Promise<AnswerKeyPreviewResponse>;
  },

  /** Apply a separate answer-key file to existing exam questions. */
  async uploadAnswerKey(examId: string, file: File, overwrite = true) {
    const token = getAuthToken();
    const formData = new FormData();
    formData.append('file', file, file.name);
    formData.append('overwrite', overwrite ? 'true' : 'false');
    const response = await fetch(`${API_BASE_URL}/exams/${examId}/upload-answer-key`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(typeof err.detail === 'string' ? err.detail : 'Answer key upload failed');
    }
    return response.json() as Promise<AnswerKeyUploadResponse>;
  },

  /** Preview how a full-answer PDF will map to exam questions (take-exam flow). */
  async previewAnswerPdf(examId: string, file: File) {
    const token = getAuthToken();
    const formData = new FormData();
    formData.append('file', file, file.name);
    const response = await fetch(`${API_BASE_URL}/exams/${examId}/preview-answer-pdf`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      const detail = err.detail;
      let message = 'Preview failed';
      if (typeof detail === 'string') message = detail;
      else if (Array.isArray(detail) && detail[0]?.msg) message = detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ');
      throw new Error(message);
    }
    return response.json() as Promise<AnswerPdfPreviewResponse>;
  },

  /** Which OCR engines are currently wired up on the backend. */
  async getOcrStatus(): Promise<OcrStatusResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/ocr/status`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new Error('Failed to fetch OCR status');
    return response.json() as Promise<OcrStatusResponse>;
  },
};

export interface AnswerKeyPreviewResponse {
  exam_id: string;
  exam_title?: string;
  matched: Array<{
    question_id: string;
    question_number: number;
    path: string;
    step_count: number;
    preview: string;
  }>;
  unmatched_exam_questions: Array<{
    question_id: string;
    question_number: number;
    path: string;
    text_preview: string;
  }>;
  unmatched_key_sections: Array<{
    number?: number;
    label?: string;
    path: string;
    preview?: string;
    reason?: string;
  }>;
  summary: {
    key_sections_found: number;
    matched_count: number;
    unmatched_exam_count: number;
    unmatched_key_count: number;
  };
}

export interface AnswerKeyUploadResponse {
  message: string;
  exam_id: string;
  questions_updated: number;
  matched_count: number;
  unmatched_exam_count: number;
  unmatched_key_count: number;
  summary: AnswerKeyPreviewResponse['summary'];
}

export interface OcrStatusResponse {
  cloud: {
    active: 'mathpix' | 'gcv' | 'azure' | null;
    available: string[];
    configured: string[];
  };
  localTrocr: {
    enabled: boolean;
    runtimeAvailable: boolean;
    /** Prose TrOCR checkpoint (same as `proseModel` when present). */
    model: string | null;
    proseModel?: string | null;
    mathTrocrModel?: string | null;
    pix2texOptIn?: boolean;
    pix2texReady?: boolean;
    /** `full` = math model on every line at submit time; `heuristic` = cheaper path */
    mathEnsembleMode?: string | null;
  };
  localEasyOcr: boolean;
  tesseract: boolean;
  summary: string;
}

/** Response from POST /exams/:id/preview-answer-pdf */
export interface AnswerPdfPreviewResponse {
  strategy: string;
  pdfPageCount: number;
  topLevelCount: number;
  rows: Array<{
    questionNumber: number;
    questionLabel: string;
    source: string;
    subParts: Array<{
      part: string | null;
      chars: number | null;
      hasContent: boolean | null;
      delivery: string;
    }>;
    /** Plain-text excerpt for review (OCR or extracted PDF text), may be approximate for handwriting */
    answerExcerpt?: string | null;
    /** 1-based page index in the answer PDF when using per-page routing */
    pdfPage?: number | null;
    note?: string;
  }>;
  warnings: string[];
  monolithicDetected: boolean;
  summary: string;
}

// ============================================================================
// Submission / exam detail (GET by id — used by SubmissionDetail and flows)
// ============================================================================

/** Step-level result returned with a question’s grading breakdown */
export interface GradingStepResult {
  id: string;
  score?: number;
  feedback?: string;
  stepNumber?: number;
  isCorrect?: boolean;
  maxScore?: number;
  expected?: string;
  received?: string;
  expectedDisplay?: string;
  expectedMathLatex?: string;
  receivedDisplay?: string;
  receivedMathLatex?: string;
}

export interface GradingResult {
  id?: string;
  score?: number;
  maxScore?: number;
  feedback?: string;
  stepResults?: GradingStepResult[];
  isCorrect?: boolean;
}

export interface SubmissionAnswer {
  questionId: string;
  questionNumber: number;
  parentQuestionId?: string | null;
  outlineTitle?: string | null;
  displayLabel?: string | null;
  gradingResult?: GradingResult;
  gradingResultId?: string;
  extractedText?: string;
  extractedLatex?: string;
  /** Cleaned / normalized transcript for reading (API adds from SymPy + heuristics) */
  extractedTextDisplay?: string;
  /** KaTeX-ready LaTeX when the backend could normalize an expression */
  extractedMathLatex?: string;
}

export interface SubmissionDetail {
  id?: string;
  examId: string;
  status: string;
  studentName?: string;
  submittedAt: string;
  answers?: SubmissionAnswer[];
  totalScore?: number | null;
  maxScore: number;
}

export interface ExamQuestion {
  id: string;
  number?: number;
  text?: string;
  richContent?: unknown;
  points?: number;
  outlineTitle?: string | null;
  subQuestions?: ExamQuestion[];
  goldSolution?: { steps?: unknown[] };
  goldSolutionSteps?: unknown;
  finalAnswer?: string;
  finalAnswerLatex?: string;
}

export interface ExamDetail {
  id?: string;
  title: string;
  questions?: ExamQuestion[];
}

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
    return apiCall<SubmissionDetail>(`/submissions/${submissionId}`);
  },

  async submit(
    examId: string,
    imageEntries: { questionId: string; file: File }[],
    answers?: any[],
    fullAnswerPdf?: File | null,
  ) {
    const formData = new FormData();
    formData.append('exam_id', examId);

    if (answers) {
      formData.append('answers', JSON.stringify(answers));
    }

    // Encode the question ID into the filename so the backend can route each
    // image to the correct question: "q_{questionId}_{index}.ext"
    imageEntries.forEach(({ questionId, file }, idx) => {
      const ext = file.name.includes('.')
        ? '.' + file.name.split('.').pop()!.toLowerCase()
        : '.jpg';
      const encodedName = `q_${questionId}_${idx}${ext}`;
      formData.append('images', file, encodedName);
    });

    // Full-exam answer PDF (page N = answer to question N)
    if (fullAnswerPdf) {
      formData.append('answer_pdf', fullAnswerPdf, fullAnswerPdf.name);
    }

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

  async approve(submissionId: string) {
    return apiCall(`/submissions/${submissionId}/approve`, {
      method: 'POST',
    });
  },

  async reject(submissionId: string) {
    return apiCall(`/submissions/${submissionId}/reject`, {
      method: 'POST',
    });
  },

  async adjustGrades(submissionId: string, adjustments: any) {
    return apiCall(`/submissions/${submissionId}/adjust-grades`, {
      method: 'PUT',
      body: JSON.stringify(adjustments),
    });
  },

  /** Marked submission: questions, student work, scores, step feedback; optional model solutions (professor). */
  async downloadMarkedPdf(
    submissionId: string,
    options?: {
      paper?: 'a4' | 'letter' | 'legal';
      includeReferenceSolutions?: boolean;
    }
  ) {
    const token = getAuthToken();
    const paper = options?.paper ?? 'a4';
    const ref = options?.includeReferenceSolutions ? 'true' : 'false';
    const response = await fetch(
      `${API_BASE_URL}/submissions/${submissionId}/marked-pdf?paper=${encodeURIComponent(paper)}&include_reference_solutions=${ref}&t=${Date.now()}`,
      { headers: { Authorization: `Bearer ${token}`, 'Cache-Control': 'no-cache' } }
    );
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || 'Failed to download marked PDF');
    }
    return response.blob();
  },
};

// ============================================================================
// Notifications
// ============================================================================

export type NotificationFeedItem = {
  id: string;
  category: 'notification' | 'reminder';
  kind: string;
  title: string;
  body?: string | null;
  link?: string | null;
  createdAt: string;
  readAt?: string | null;
  scheduledReminderId?: string | null;
  repeat?: string | null;
};

export type NotificationFeedResponse = {
  items: NotificationFeedItem[];
  unreadCount: number;
};

export const notificationsAPI = {
  async getFeed(limit = 80): Promise<NotificationFeedResponse> {
    return apiCall(`/notifications?limit=${limit}`);
  },

  async markRead(notificationId: string) {
    return apiCall(`/notifications/${encodeURIComponent(notificationId)}/read`, {
      method: 'PATCH',
    });
  },

  async markAllRead() {
    return apiCall<{ marked: number }>('/notifications/read-all', { method: 'POST' });
  },
};

export type ScheduleRepeat = 'none' | 'daily' | 'weekly' | 'monthly';

export type DueReminderItem = {
  id: string;
  title: string;
  body?: string | null;
  link?: string | null;
  remindAt: string;
  repeat: string;
};

export const remindersAPI = {
  async getDue(): Promise<DueReminderItem[]> {
    return apiCall('/reminders/due');
  },

  async schedule(payload: {
    sourceKey: string;
    title: string;
    body?: string;
    link?: string;
    userNote?: string;
    remindAt: string;
    repeat: ScheduleRepeat;
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

