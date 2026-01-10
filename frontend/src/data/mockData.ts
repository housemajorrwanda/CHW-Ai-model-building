import { Course, Exam, Submission, DashboardStats } from '@/types';

export const mockCourses: Course[] = [
  {
    id: 'course-1',
    name: 'Calculus I',
    code: 'MATH 101',
    description: 'Introduction to differential and integral calculus',
    professorId: 'prof-1',
    students: ['student-1', 'student-2', 'student-3'],
    createdAt: new Date('2024-01-15'),
  },
  {
    id: 'course-2',
    name: 'Linear Algebra',
    code: 'MATH 201',
    description: 'Vectors, matrices, and linear transformations',
    professorId: 'prof-1',
    students: ['student-1', 'student-4'],
    createdAt: new Date('2024-01-20'),
  },
  {
    id: 'course-3',
    name: 'Differential Equations',
    code: 'MATH 301',
    description: 'Ordinary and partial differential equations',
    professorId: 'prof-1',
    students: ['student-2', 'student-3', 'student-5'],
    createdAt: new Date('2024-02-01'),
  },
];

export const mockExams: Exam[] = [
  {
    id: 'exam-1',
    courseId: 'course-1',
    title: 'Midterm Exam',
    description: 'Covers chapters 1-5: Limits, Derivatives, and Applications',
    totalPoints: 100,
    dueDate: new Date('2024-03-15'),
    createdAt: new Date('2024-02-28'),
    questions: [
      {
        id: 'q1',
        number: 1,
        text: 'Find the derivative of f(x) = x³ + 2x² - 5x + 3',
        points: 20,
        goldSolution: {
          steps: [
            { stepNumber: 1, description: 'Apply power rule to x³', expression: '3x²', latex: '3x^2', points: 5 },
            { stepNumber: 2, description: 'Apply power rule to 2x²', expression: '4x', latex: '4x', points: 5 },
            { stepNumber: 3, description: 'Apply power rule to -5x', expression: '-5', latex: '-5', points: 5 },
            { stepNumber: 4, description: 'Combine terms', expression: '3x² + 4x - 5', latex: '3x^2 + 4x - 5', points: 5 },
          ],
          finalAnswer: '3x² + 4x - 5',
          finalAnswerLatex: "f'(x) = 3x^2 + 4x - 5",
        },
      },
      {
        id: 'q2',
        number: 2,
        text: 'Evaluate the integral ∫(2x + 1)dx',
        points: 15,
        goldSolution: {
          steps: [
            { stepNumber: 1, description: 'Integrate 2x', expression: 'x²', latex: 'x^2', points: 5 },
            { stepNumber: 2, description: 'Integrate 1', expression: 'x', latex: 'x', points: 5 },
            { stepNumber: 3, description: 'Add constant C', expression: 'x² + x + C', latex: 'x^2 + x + C', points: 5 },
          ],
          finalAnswer: 'x² + x + C',
          finalAnswerLatex: '\\int(2x + 1)dx = x^2 + x + C',
        },
      },
    ],
  },
  {
    id: 'exam-2',
    courseId: 'course-1',
    title: 'Quiz 1',
    description: 'Quick quiz on limits',
    totalPoints: 30,
    createdAt: new Date('2024-02-10'),
    questions: [],
  },
  {
    id: 'exam-3',
    courseId: 'course-2',
    title: 'Matrix Operations Test',
    description: 'Matrix multiplication and determinants',
    totalPoints: 50,
    dueDate: new Date('2024-03-20'),
    createdAt: new Date('2024-03-01'),
    questions: [],
  },
];

export const mockSubmissions: Submission[] = [
  {
    id: 'sub-1',
    examId: 'exam-1',
    studentId: 'student-1',
    studentName: 'Alex Johnson',
    submittedAt: new Date('2024-03-14T10:30:00'),
    status: 'graded',
    maxScore: 100,
    totalScore: 85,
    answers: [
      {
        questionId: 'q1',
        questionNumber: 1,
        extractedText: "3x² + 4x - 5",
        extractedLatex: "3x^2 + 4x - 5",
        extractedSteps: [
          { stepNumber: 1, text: '3x²', latex: '3x^2' },
          { stepNumber: 2, text: '4x', latex: '4x' },
          { stepNumber: 3, text: '-5', latex: '-5' },
        ],
        gradingResult: {
          score: 20,
          maxScore: 20,
          feedback: 'Perfect! All steps correct.',
          isCorrect: true,
          stepResults: [
            { stepNumber: 1, isCorrect: true, score: 5, maxScore: 5, feedback: 'Correct', expected: '3x²', received: '3x²' },
            { stepNumber: 2, isCorrect: true, score: 5, maxScore: 5, feedback: 'Correct', expected: '4x', received: '4x' },
            { stepNumber: 3, isCorrect: true, score: 5, maxScore: 5, feedback: 'Correct', expected: '-5', received: '-5' },
            { stepNumber: 4, isCorrect: true, score: 5, maxScore: 5, feedback: 'Correct final answer', expected: '3x² + 4x - 5', received: '3x² + 4x - 5' },
          ],
        },
      },
    ],
  },
  {
    id: 'sub-2',
    examId: 'exam-1',
    studentId: 'student-2',
    studentName: 'Emma Williams',
    submittedAt: new Date('2024-03-14T11:15:00'),
    status: 'graded',
    maxScore: 100,
    totalScore: 72,
    answers: [],
  },
  {
    id: 'sub-3',
    examId: 'exam-1',
    studentId: 'student-3',
    studentName: 'Michael Brown',
    submittedAt: new Date('2024-03-15T09:00:00'),
    status: 'pending',
    maxScore: 100,
    answers: [],
  },
  {
    id: 'sub-4',
    examId: 'exam-3',
    studentId: 'student-1',
    studentName: 'Alex Johnson',
    submittedAt: new Date('2024-03-19T14:20:00'),
    status: 'grading',
    maxScore: 50,
    answers: [],
  },
];

export const mockProfessorStats: DashboardStats = {
  totalCourses: 3,
  totalExams: 8,
  totalSubmissions: 45,
  pendingGrading: 12,
  averageScore: 78.5,
};

export const mockStudentStats: DashboardStats = {
  totalCourses: 2,
  totalExams: 5,
  totalSubmissions: 4,
  pendingGrading: 1,
  averageScore: 82.3,
};

export const mockAdminStats: DashboardStats = {
  totalCourses: 15,
  totalExams: 42,
  totalSubmissions: 320,
  pendingGrading: 28,
  averageScore: 75.8,
};