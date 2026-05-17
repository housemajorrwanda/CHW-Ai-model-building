"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Optional
from datetime import datetime, date
from enum import Enum


# Enums
class UserRole(str, Enum):
    PROFESSOR = "professor"
    STUDENT = "student"
    ADMIN = "admin"


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    GRADING = "grading"
    GRADED = "graded"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"


class CourseLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ALL_LEVELS = "all_levels"


class EnrollmentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# Auth Schemas
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    role: UserRole


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole
    institution: Optional[str] = None
    country: Optional[str] = None
    majorDepartment: Optional[str] = None
    yearOfStudy: Optional[int] = Field(None, ge=1, le=20)
    gender: Optional[str] = None
    studentId: Optional[str] = None
    dateOfBirth: Optional[date] = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    avatar: Optional[str] = None
    createdAt: datetime
    institution: Optional[str] = None
    country: Optional[str] = None
    majorDepartment: Optional[str] = None
    yearOfStudy: Optional[int] = None
    gender: Optional[str] = None
    studentId: Optional[str] = None
    dateOfBirth: Optional[date] = None
    remindExamDeadlinesEnabled: bool = True
    remindExamOffsetsHours: List[int] = Field(default_factory=lambda: [168, 72, 24])
    remindTeachingDeadlinesEnabled: bool = True

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """Partial update for the signed-in user."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    institution: Optional[str] = None
    country: Optional[str] = None
    majorDepartment: Optional[str] = None
    yearOfStudy: Optional[int] = Field(None, ge=1, le=20)
    gender: Optional[str] = None
    studentId: Optional[str] = None
    dateOfBirth: Optional[date] = None
    remindExamDeadlinesEnabled: Optional[bool] = None
    remindExamOffsetsHours: Optional[List[int]] = None
    remindTeachingDeadlinesEnabled: Optional[bool] = None

    @field_validator("remindExamOffsetsHours")
    @classmethod
    def validate_exam_offsets(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is None:
            return None
        out: List[int] = []
        for x in v:
            try:
                h = int(x)
            except (TypeError, ValueError):
                continue
            if 1 <= h <= 8760:
                out.append(h)
        out = sorted(set(out))
        if len(out) > 12:
            raise ValueError("At most 12 reminder windows allowed")
        if not out:
            raise ValueError("Choose at least one time window, or turn off exam reminders")
        return out


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# Topic and Subtopic Schemas
class SubtopicCreate(BaseModel):
    name: str
    description: Optional[str] = None
    order: int = 0


class SubtopicResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    order: int
    
    class Config:
        from_attributes = True


class TopicCreate(BaseModel):
    name: str
    description: Optional[str] = None
    order: int = 0
    subtopics: List[SubtopicCreate] = []


class TopicResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    order: int
    subtopics: List[SubtopicResponse] = []
    
    class Config:
        from_attributes = True


# Enrollment Schemas
class EnrollmentResponse(BaseModel):
    id: str
    studentId: str
    studentName: str
    studentEmail: str
    status: EnrollmentStatus
    requestedAt: datetime
    enrolledAt: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Course Schemas
class CourseCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    level: CourseLevel = CourseLevel.ALL_LEVELS
    topics: List[TopicCreate] = []


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    level: Optional[CourseLevel] = None


class CourseResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None
    level: CourseLevel
    professorId: str
    professorName: Optional[str] = None
    topics: List[TopicResponse] = []
    enrolledStudents: List[EnrollmentResponse] = []
    pendingEnrollments: List[EnrollmentResponse] = []
    examCount: int = 0
    submissionCount: int = 0
    createdAt: datetime
    
    class Config:
        from_attributes = True


class AnnouncementReactionKind(str, Enum):
    LIKE = "like"
    IMPROVE = "improve"
    IMPLEMENT = "implement"


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=20000)
    pinned: bool = False


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    body: Optional[str] = Field(None, min_length=1, max_length=20000)
    pinned: Optional[bool] = None


class AnnouncementCommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=8000)


class AnnouncementCommentResponse(BaseModel):
    id: str
    authorId: str
    authorName: str
    body: str
    createdAt: datetime

    class Config:
        from_attributes = True


class AnnouncementResponse(BaseModel):
    id: str
    courseId: str
    authorId: str
    authorName: str
    title: str
    body: str
    pinned: bool
    createdAt: datetime
    likeCount: int = 0
    improveCount: int = 0
    implementCount: int = 0
    commentCount: int = 0
    myLiked: bool = False
    myImprove: bool = False
    myImplement: bool = False
    comments: List[AnnouncementCommentResponse] = []

    class Config:
        from_attributes = True


class AnnouncementReactionToggle(BaseModel):
    kind: AnnouncementReactionKind


# Attachment Schemas
class AttachmentCreate(BaseModel):
    attachmentType: str  # image, scan, document
    filePath: str
    filename: str
    fileSize: Optional[int] = None
    mimeType: Optional[str] = None


class AttachmentResponse(BaseModel):
    id: str
    attachmentType: str
    filePath: str
    filename: str
    
    class Config:
        from_attributes = True


# Embedded Content Schemas
class EmbeddedContentCreate(BaseModel):
    contentType: str  # shape, table, graph, chart, calculator, periodic_table, unit_converter
    contentData: dict  # Configuration data as JSON
    positionData: Optional[dict] = None


class EmbeddedContentResponse(BaseModel):
    id: str
    contentType: str
    contentData: dict
    positionData: Optional[dict] = None
    
    class Config:
        from_attributes = True


# Theory & Constants Schemas
class TheoryCreate(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None  # physics, chemistry, mathematics


class TheoryResponse(BaseModel):
    id: str
    name: str
    value: str
    unit: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    
    class Config:
        from_attributes = True


# Gold Solution Step Schemas
class GoldSolutionStepCreate(BaseModel):
    stepNumber: int
    description: str = ""
    expression: str
    latex: str = ""
    points: int = 5
    required: bool = True


class GoldSolutionStepResponse(BaseModel):
    stepNumber: int
    description: str
    expression: str
    latex: str
    points: int
    required: bool = True
    
    class Config:
        from_attributes = True


# Question Schemas
class SubQuestionCreate(BaseModel):
    number: int
    text: str
    points: int
    goldSolutionSteps: List[GoldSolutionStepCreate]
    finalAnswer: str
    finalAnswerLatex: str = ""
    questionType: str = "standard"
    richContent: Optional[dict] = None
    outlineTitle: Optional[str] = None
    outlineLevel: int = 2
    subQuestions: List['SubQuestionCreate'] = []


class QuestionCreate(BaseModel):
    number: int
    text: str
    points: int
    goldSolutionSteps: List[GoldSolutionStepCreate]
    finalAnswer: str
    finalAnswerLatex: str = ""
    # Enhanced fields
    questionType: str = "standard"  # standard, multi-part
    richContent: Optional[dict] = None  # TipTap JSON
    outlineTitle: Optional[str] = None  # Short label in outline (e.g. "Linear equations")
    outlineLevel: int = 1
    parentQuestionId: Optional[str] = None
    subQuestions: List['SubQuestionCreate'] = []
    attachments: List[AttachmentCreate] = []
    embeddedContent: List[EmbeddedContentCreate] = []
    theories: List[TheoryCreate] = []


class GoldSolutionResponse(BaseModel):
    steps: List[GoldSolutionStepResponse]
    finalAnswer: str
    finalAnswerLatex: str


class AttachmentResponse(BaseModel):
    id: str
    attachmentType: str
    filePath: str
    filename: str
    mimeType: Optional[str] = None

    class Config:
        from_attributes = True


class EmbeddedContentResponse(BaseModel):
    id: str
    contentType: str
    contentData: dict
    positionData: Optional[dict] = None

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    id: str
    number: int
    text: str
    points: int
    goldSolution: GoldSolutionResponse
    goldSolutionSteps: Optional[List[GoldSolutionStepResponse]] = None
    finalAnswer: Optional[str] = None
    finalAnswerLatex: Optional[str] = None
    questionType: Optional[str] = "standard"
    richContent: Optional[dict] = None
    outlineTitle: Optional[str] = None
    outlineLevel: Optional[int] = 1
    parentQuestionId: Optional[str] = None
    subQuestions: Optional[List['QuestionResponse']] = []
    attachments: Optional[List[AttachmentResponse]] = []
    embeddedContent: Optional[List[EmbeddedContentResponse]] = []
    theories: Optional[List] = []

    class Config:
        from_attributes = True


# Exam Schemas
class ExamCreate(BaseModel):
    courseId: str
    title: str
    description: Optional[str] = None
    questions: List[QuestionCreate]
    dueDate: Optional[datetime] = None


class ExamResponse(BaseModel):
    id: str
    courseId: str
    title: str
    description: Optional[str] = None
    questions: List[QuestionResponse]
    totalPoints: int
    dueDate: Optional[datetime] = None
    isPublished: bool = False
    publishedAt: Optional[datetime] = None
    createdAt: datetime
    
    class Config:
        from_attributes = True


# Step Result Schemas
class StepResultResponse(BaseModel):
    id: str
    stepNumber: int
    isCorrect: bool
    score: float
    maxScore: int
    feedback: str
    expected: Optional[str] = None
    received: Optional[str] = None
    expectedDisplay: Optional[str] = None
    receivedDisplay: Optional[str] = None
    receivedMathLatex: Optional[str] = None
    
    class Config:
        from_attributes = True


# Extracted Step Schemas
class ExtractedStepResponse(BaseModel):
    stepNumber: int
    text: str
    latex: str


# Grading Result Schemas
class GradingResultResponse(BaseModel):
    id: str
    score: float
    maxScore: int
    feedback: str
    stepResults: List[StepResultResponse]
    isCorrect: bool
    
    class Config:
        from_attributes = True


# Submitted Answer Schemas
class SubmittedAnswerResponse(BaseModel):
    questionId: str
    questionNumber: int
    extractedText: Optional[str] = None
    extractedLatex: Optional[str] = None
    extractedTextDisplay: Optional[str] = None
    extractedMathLatex: Optional[str] = None
    extractedSteps: List[ExtractedStepResponse]
    gradingResult: Optional[GradingResultResponse] = None
    
    class Config:
        from_attributes = True


# Submission Schemas
class SubmissionResponse(BaseModel):
    id: str
    examId: str
    studentId: str
    studentName: str
    submittedAt: datetime
    status: SubmissionStatus
    imageUrl: Optional[str] = None
    answers: List[SubmittedAnswerResponse] = []
    totalScore: Optional[float] = None
    maxScore: int
    
    class Config:
        from_attributes = True


# Dashboard Stats Schemas
class DashboardStatsResponse(BaseModel):
    totalCourses: int
    totalExams: int
    totalSubmissions: int
    pendingGrading: int
    averageScore: Optional[float] = None


class AnalyticsCountItem(BaseModel):
    """Single bucket for status / category charts."""

    label: str
    key: str
    count: int


class InstructorCourseAnalyticsItem(BaseModel):
    courseId: str
    courseName: str
    courseCode: str
    submissionCount: int
    gradedCount: int
    avgPercent: Optional[float] = None


class InstructorWeekSubmissionsItem(BaseModel):
    weekStart: str
    count: int


class InstructorEnrollmentItem(BaseModel):
    courseId: str
    courseName: str
    approvedStudents: int


class InstructorAnalyticsData(BaseModel):
    submissionStatus: List[AnalyticsCountItem]
    courseBreakdown: List[InstructorCourseAnalyticsItem]
    weeklySubmissions: List[InstructorWeekSubmissionsItem]
    enrollmentsByCourse: List[InstructorEnrollmentItem]


class StudentExamScoreItem(BaseModel):
    examId: str
    examTitle: str
    courseName: str
    percent: float
    submittedAt: datetime


class StudentCoursePerformanceItem(BaseModel):
    courseId: str
    courseName: str
    avgPercent: float
    gradedCount: int


class StudentAnalyticsData(BaseModel):
    submissionStatus: List[AnalyticsCountItem]
    releasedExamScores: List[StudentExamScoreItem]
    coursePerformance: List[StudentCoursePerformanceItem]


class DashboardAnalyticsResponse(BaseModel):
    role: str
    instructor: Optional[InstructorAnalyticsData] = None
    student: Optional[StudentAnalyticsData] = None


class StepAdjustmentRequest(BaseModel):
    stepResultId: str
    score: Optional[float] = None
    feedback: Optional[str] = None


class GradeAdjustmentItem(BaseModel):
    gradingResultId: str
    score: Optional[float] = None
    feedback: Optional[str] = None
    stepAdjustments: Optional[List[StepAdjustmentRequest]] = []


class GradeAdjustmentRequest(BaseModel):
    adjustments: List[GradeAdjustmentItem] = []


# Notifications
class NotificationFeedItem(BaseModel):
    id: str
    category: str  # "notification" | "reminder"
    kind: str
    title: str
    body: Optional[str] = None
    link: Optional[str] = None
    createdAt: datetime
    readAt: Optional[datetime] = None
    scheduledReminderId: Optional[str] = None
    repeat: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationFeedResponse(BaseModel):
    items: List[NotificationFeedItem]
    unreadCount: int


class ScheduleReminderRequest(BaseModel):
    """Create a personal follow-up reminder from the bell."""

    sourceKey: Optional[str] = None
    title: str
    body: Optional[str] = None
    link: Optional[str] = None
    userNote: Optional[str] = Field(None, max_length=2000)
    remindAt: datetime
    repeat: str = "none"

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        t = (v or "").strip()
        if not t:
            raise ValueError("Title is required")
        return t[:500]

    @field_validator("repeat")
    @classmethod
    def repeat_allowed(cls, v: str) -> str:
        r = (v or "none").lower()
        allowed = frozenset({"none", "daily", "weekly", "monthly"})
        if r not in allowed:
            return "none"
        return r


class ScheduledReminderDueItem(BaseModel):
    id: str
    title: str
    body: Optional[str] = None
    link: Optional[str] = None
    remindAt: datetime
    repeat: str

    class Config:
        from_attributes = True

