"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
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


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    avatar: Optional[str] = None
    createdAt: datetime
    
    class Config:
        from_attributes = True


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
    richContent: Optional[dict] = None


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


class QuestionResponse(BaseModel):
    id: str
    number: int
    text: str
    points: int
    goldSolution: GoldSolutionResponse
    
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
    stepNumber: int
    isCorrect: bool
    score: float
    maxScore: int
    feedback: str
    expected: Optional[str] = None
    received: Optional[str] = None
    
    class Config:
        from_attributes = True


# Extracted Step Schemas
class ExtractedStepResponse(BaseModel):
    stepNumber: int
    text: str
    latex: str


# Grading Result Schemas
class GradingResultResponse(BaseModel):
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

