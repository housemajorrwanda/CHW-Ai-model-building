"""
SQLAlchemy database models
"""
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime, Date, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    PROFESSOR = "professor"
    STUDENT = "student"
    ADMIN = "admin"


class SubmissionStatus(str, enum.Enum):
    PENDING = "pending"
    GRADING = "grading"
    GRADED = "graded"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"


class CourseLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ALL_LEVELS = "all_levels"


class EnrollmentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AnnouncementReactionKind(str, enum.Enum):
    LIKE = "like"
    IMPROVE = "improve"
    IMPLEMENT = "implement"


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    avatar = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Profile / demographics (optional; collected at registration or later)
    institution = Column(String(255), nullable=True)
    country = Column(String(128), nullable=True)
    major_department = Column(String(255), nullable=True)
    year_of_study = Column(Integer, nullable=True)
    gender = Column(String(64), nullable=True)
    student_id = Column(String(128), nullable=True)
    date_of_birth = Column(Date, nullable=True)

    # Reminder preferences (in-app feed; stored server-side)
    remind_exam_deadlines_enabled = Column(Boolean, default=True, nullable=False)
    remind_exam_offsets_hours = Column(String(512), nullable=True)  # JSON array of ints, e.g. [168,72,24]
    remind_teaching_deadlines_enabled = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    courses_taught = relationship("Course", back_populates="professor", foreign_keys="Course.professor_id")
    submissions = relationship("Submission", back_populates="student", foreign_keys="Submission.student_id")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    scheduled_reminders = relationship(
        "UserScheduledReminder", back_populates="user", cascade="all, delete-orphan"
    )


class Course(Base):
    __tablename__ = "courses"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    level = Column(Enum(CourseLevel), default=CourseLevel.ALL_LEVELS)
    professor_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    professor = relationship("User", back_populates="courses_taught", foreign_keys=[professor_id])
    exams = relationship("Exam", back_populates="course", cascade="all, delete-orphan")
    topics = relationship("CourseTopic", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("CourseEnrollment", back_populates="course", cascade="all, delete-orphan")
    announcements = relationship("CourseAnnouncement", back_populates="course", cascade="all, delete-orphan")


class Exam(Base):
    __tablename__ = "exams"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    total_points = Column(Integer, nullable=False, default=0)
    due_date = Column(DateTime(timezone=True), nullable=True)
    is_published = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan", order_by="Question.number")
    submissions = relationship("Submission", back_populates="exam")


class Question(Base):
    __tablename__ = "questions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    exam_id = Column(String, ForeignKey("exams.id"), nullable=False)
    number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    points = Column(Integer, nullable=False)
    final_answer = Column(String(500), nullable=True)
    final_answer_latex = Column(String(500), nullable=True)
    
    # Enhanced fields
    question_type = Column(String(50), default="standard")  # standard, multi-part
    rich_content = Column(Text, nullable=True)  # JSON for TipTap content
    outline_title = Column(String(500), nullable=True)  # Short label for outline / nav (optional)
    outline_level = Column(Integer, default=1)
    parent_question_id = Column(String, ForeignKey("questions.id"), nullable=True)
    
    # Relationships
    exam = relationship("Exam", back_populates="questions")
    gold_steps = relationship("GoldSolutionStep", back_populates="question", cascade="all, delete-orphan", order_by="GoldSolutionStep.step_number")
    sub_questions = relationship("Question", backref="parent_question", remote_side=[id])
    attachments = relationship("QuestionAttachment", back_populates="question", cascade="all, delete-orphan")
    embedded_content = relationship("EmbeddedContent", back_populates="question", cascade="all, delete-orphan")
    theories = relationship("QuestionTheory", back_populates="question", cascade="all, delete-orphan")


class GoldSolutionStep(Base):
    __tablename__ = "gold_solution_steps"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    expression = Column(String(500), nullable=False)
    latex = Column(String(500), nullable=True)
    points = Column(Integer, nullable=False)
    required = Column(Boolean, default=True)
    
    # Relationships
    question = relationship("Question", back_populates="gold_steps")


class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    exam_id = Column(String, ForeignKey("exams.id"), nullable=False)
    student_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.PENDING, nullable=False)
    total_score = Column(Float, nullable=True)
    max_score = Column(Integer, nullable=False)
    typed_answers = Column(Text, nullable=True)  # JSON data with typed answers
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    graded_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    exam = relationship("Exam", back_populates="submissions")
    student = relationship("User", back_populates="submissions", foreign_keys=[student_id])
    approver = relationship("User", foreign_keys=[approved_by])
    images = relationship("SubmissionImage", back_populates="submission", cascade="all, delete-orphan")
    grading_results = relationship("GradingResult", back_populates="submission", cascade="all, delete-orphan")


class SubmissionImage(Base):
    __tablename__ = "submission_images"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False)
    image_path = Column(String(500), nullable=False)
    page_number = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    submission = relationship("Submission", back_populates="images")


class GradingResult(Base):
    __tablename__ = "grading_results"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    extracted_text = Column(Text, nullable=True)
    extracted_latex = Column(Text, nullable=True)
    score = Column(Float, nullable=False, default=0.0)
    max_score = Column(Integer, nullable=False)
    feedback = Column(Text, nullable=True)
    is_correct = Column(Boolean, default=False)
    
    # Relationships
    submission = relationship("Submission", back_populates="grading_results")
    question = relationship("Question")
    step_results = relationship("StepResult", back_populates="grading_result", cascade="all, delete-orphan", order_by="StepResult.step_number")


class StepResult(Base):
    __tablename__ = "step_results"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    grading_result_id = Column(String, ForeignKey("grading_results.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    student_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    score = Column(Float, nullable=False, default=0.0)
    max_score = Column(Integer, nullable=False)
    feedback = Column(Text, nullable=True)
    expected = Column(String(500), nullable=True)
    received = Column(String(500), nullable=True)
    
    # Relationships
    grading_result = relationship("GradingResult", back_populates="step_results")


class QuestionAttachment(Base):
    __tablename__ = "question_attachments"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    attachment_type = Column(String(50), nullable=False)  # image, scan, document
    file_path = Column(String(500), nullable=False)
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    question = relationship("Question", back_populates="attachments")


class EmbeddedContent(Base):
    __tablename__ = "embedded_content"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    content_type = Column(String(50), nullable=False)  # shape, table, graph, chart, calculator, etc.
    content_data = Column(Text, nullable=False)  # JSON configuration
    position_data = Column(Text, nullable=True)  # JSON position info
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    question = relationship("Question", back_populates="embedded_content")


class QuestionTheory(Base):
    __tablename__ = "question_theories"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    name = Column(String(255), nullable=False)
    value = Column(String(500), nullable=False)
    unit = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # physics, chemistry, mathematics
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    question = relationship("Question", back_populates="theories")


class CourseTopic(Base):
    __tablename__ = "course_topics"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="topics")
    subtopics = relationship("TopicSubtopic", back_populates="topic", cascade="all, delete-orphan")


class TopicSubtopic(Base):
    __tablename__ = "topic_subtopics"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    topic_id = Column(String, ForeignKey("course_topics.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    topic = relationship("CourseTopic", back_populates="subtopics")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(64), nullable=False)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    link = Column(String(1024), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")


class UserScheduledReminder(Base):
    """User-chosen date/time reminders (from notification bell)."""

    __tablename__ = "user_scheduled_reminders"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    source_key = Column(String(512), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    link = Column(String(1024), nullable=True)
    user_note = Column(Text, nullable=True)
    remind_at = Column(DateTime(timezone=True), nullable=False, index=True)
    repeat = Column(String(32), nullable=False, default="none")
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="scheduled_reminders")


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    student_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(EnrollmentStatus), default=EnrollmentStatus.PENDING)
    enrolled_at = Column(DateTime(timezone=True), nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    course = relationship("Course", back_populates="enrollments")
    student = relationship("User", foreign_keys=[student_id])


class CourseAnnouncement(Base):
    __tablename__ = "course_announcements"

    id = Column(String, primary_key=True, default=generate_uuid)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False, index=True)
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    pinned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course", back_populates="announcements")
    author = relationship("User", foreign_keys=[author_id])
    comments = relationship(
        "AnnouncementComment", back_populates="announcement", cascade="all, delete-orphan"
    )
    reactions = relationship(
        "AnnouncementReaction", back_populates="announcement", cascade="all, delete-orphan"
    )


class AnnouncementComment(Base):
    __tablename__ = "announcement_comments"

    id = Column(String, primary_key=True, default=generate_uuid)
    announcement_id = Column(String, ForeignKey("course_announcements.id"), nullable=False, index=True)
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    announcement = relationship("CourseAnnouncement", back_populates="comments")
    author = relationship("User", foreign_keys=[author_id])


class AnnouncementReaction(Base):
    __tablename__ = "announcement_reactions"

    id = Column(String, primary_key=True, default=generate_uuid)
    announcement_id = Column(String, ForeignKey("course_announcements.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(Enum(AnnouncementReactionKind), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    announcement = relationship("CourseAnnouncement", back_populates="reactions")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("announcement_id", "user_id", "kind", name="uq_announcement_reaction_user_kind"),
    )

