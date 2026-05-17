/** Shared rules for how an exam appears in the student portal (matches StudentExams). */

export type StudentExamUiStatus =
  | 'available'
  | 'overdue'
  | 'pending'
  | 'grading'
  | 'graded';

export interface ExamLike {
  id: string;
  dueDate: string | null;
}

export interface SubmissionLike {
  examId: string;
  status: string;
}

export function getStudentExamUiStatus(
  exam: ExamLike,
  submissions: SubmissionLike[]
): { status: StudentExamUiStatus; submission?: SubmissionLike } {
  const submission = submissions.find((s) => s.examId === exam.id);

  if (!submission) {
    if (exam.dueDate && new Date(exam.dueDate) < new Date()) {
      return { status: 'overdue' };
    }
    return { status: 'available' };
  }

  if (submission.status === 'approved') {
    return { status: 'graded', submission };
  }
  if (
    submission.status === 'graded' ||
    submission.status === 'awaiting_approval' ||
    submission.status === 'grading'
  ) {
    return { status: 'grading', submission };
  }
  return { status: 'pending', submission };
}

export function partitionStudentExams<T extends ExamLike>(exams: T[], submissions: SubmissionLike[]) {
  const available: T[] = [];
  const submitted: T[] = [];
  const graded: T[] = [];

  for (const exam of exams) {
    const { status } = getStudentExamUiStatus(exam, submissions);
    if (status === 'available' || status === 'overdue') {
      available.push(exam);
    } else if (status === 'pending' || status === 'grading') {
      submitted.push(exam);
    } else if (status === 'graded') {
      graded.push(exam);
    }
  }

  return { available, submitted, graded };
}
