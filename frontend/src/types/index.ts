export type UserRole = 'professor' | 'student' | 'admin';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
  createdAt: Date;
}

export interface Course {
  id: string;
  name: string;
  code: string;
  description?: string;
  professorId: string;
  students: string[];
  createdAt: Date;
}

export interface Exam {
  id: string;
  courseId: string;
  title: string;
  description?: string;
  questions: Question[];
  totalPoints: number;
  dueDate?: Date;
  createdAt: Date;
}

export interface Question {
  id: string;
  number: number;
  text: string;
  points: number;
  goldSolution: GoldSolution;
}

export interface GoldSolution {
  steps: SolutionStep[];
  finalAnswer: string;
  finalAnswerLatex: string;
}

export interface SolutionStep {
  stepNumber: number;
  description: string;
  expression: string;
  latex: string;
  points: number;
}

export interface Submission {
  id: string;
  examId: string;
  studentId: string;
  studentName: string;
  submittedAt: Date;
  status: 'pending' | 'grading' | 'graded';
  imageUrl?: string;
  answers: SubmittedAnswer[];
  totalScore?: number;
  maxScore: number;
}

export interface SubmittedAnswer {
  questionId: string;
  questionNumber: number;
  extractedText?: string;
  extractedLatex?: string;
  extractedSteps: ExtractedStep[];
  gradingResult?: GradingResult;
}

export interface ExtractedStep {
  stepNumber: number;
  text: string;
  latex: string;
}

export interface GradingResult {
  score: number;
  maxScore: number;
  feedback: string;
  stepResults: StepResult[];
  isCorrect: boolean;
}

export interface StepResult {
  stepNumber: number;
  isCorrect: boolean;
  score: number;
  maxScore: number;
  feedback: string;
  expected?: string;
  received?: string;
}

export interface DashboardStats {
  totalCourses: number;
  totalExams: number;
  totalSubmissions: number;
  pendingGrading: number;
  averageScore?: number;
}