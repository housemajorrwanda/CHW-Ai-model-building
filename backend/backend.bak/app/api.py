from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import func
from typing import List, Optional
import os
import json
from pathlib import Path
import shutil
from datetime import datetime, timedelta
import jwt

from database import get_db, init_db, engine
import models
import schemas
from math_grader import MathGrader, Step as GraderStep
from ocr_pipeline import OCRProcessor

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

import hashlib

def simple_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

pwd_context = None
security = HTTPBearer()

app = FastAPI(
    title="EasyGrade API",
    description="Modern Exam Grading Platform",
    version="1.0.0"
)

allowed_origins = [
    "http://localhost:8080",
    "http://localhost:8081",
    "http://localhost:8082",
    "http://localhost:8083",
    "http://localhost:5173",
    "http://localhost:3000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ocr_processor = OCRProcessor(language="en", dpi=300, psm=6, use_easyocr=True)



def verify_password(plain_password: str, hashed_password: str) -> bool:
    return simple_hash(plain_password) == hashed_password


def get_password_hash(password: str) -> str:
    return simple_hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> models.User:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def user_to_response(user: models.User) -> schemas.UserResponse:
    return schemas.UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        avatar=user.avatar,
        createdAt=user.created_at
    )


@app.on_event("startup")
def startup_event():
    init_db()
    db = next(get_db())
    if db.query(models.User).count() == 0:
        professor = models.User(
            name="Dr. Sarah Chen",
            email="professor@university.edu",
            password_hash=get_password_hash("password"),
            role=models.UserRole.PROFESSOR
        )
        student = models.User(
            name="Alex Johnson",
            email="student@university.edu",
            password_hash=get_password_hash("password"),
            role=models.UserRole.STUDENT
        )
        admin = models.User(
            name="System Admin",
            email="admin@university.edu",
            password_hash=get_password_hash("password"),
            role=models.UserRole.ADMIN
        )
        db.add_all([professor, student, admin])
        db.commit()
        print("✅ Created demo users (password: 'password')")



@app.post("/api/auth/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    if user.role.value != credentials.role.value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect role selected"
        )
    access_token = create_access_token(data={"sub": user.id, "role": user.role.value})
    
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=user_to_response(user)
    )


@app.post("/api/auth/register", response_model=schemas.Token)
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = models.User(
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token(data={"sub": new_user.id, "role": new_user.role.value})
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=user_to_response(new_user)
    )


@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return user_to_response(current_user)



def course_to_response(course: models.Course, db: Session) -> schemas.CourseResponse:
    topics = []
    for topic in sorted(course.topics, key=lambda t: t.order):
        subtopics = [
            schemas.SubtopicResponse(
                id=sub.id,
                name=sub.name,
                description=sub.description,
                order=sub.order
            )
            for sub in sorted(topic.subtopics, key=lambda s: s.order)
        ]
        topics.append(schemas.TopicResponse(
            id=topic.id,
            name=topic.name,
            description=topic.description,
            order=topic.order,
            subtopics=subtopics
        )        )
    enrolled = []
    pending = []
    for enrollment in course.enrollments:
        enrollment_data = schemas.EnrollmentResponse(
            id=enrollment.id,
            studentId=enrollment.student_id,
            studentName=enrollment.student.name,
            studentEmail=enrollment.student.email,
            status=enrollment.status.value,
            requestedAt=enrollment.requested_at,
            enrolledAt=enrollment.enrolled_at
        )
        if enrollment.status == models.EnrollmentStatus.APPROVED:
            enrolled.append(enrollment_data)
        elif enrollment.status == models.EnrollmentStatus.PENDING:
            pending.append(enrollment_data)
    exam_count = len(course.exams)
    submission_count = sum(len(exam.submissions) for exam in course.exams)
    
    return schemas.CourseResponse(
        id=course.id,
        name=course.name,
        code=course.code,
        description=course.description,
        level=course.level.value,
        professorId=course.professor_id,
        professorName=course.professor.name,
        topics=topics,
        enrolledStudents=enrolled,
        pendingEnrollments=pending,
        examCount=exam_count,
        submissionCount=submission_count,
        createdAt=course.created_at
    )


@app.get("/api/courses", response_model=List[schemas.CourseResponse])
def get_courses(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == models.UserRole.PROFESSOR:
        courses = db.query(models.Course).filter(
            models.Course.professor_id == current_user.id
        ).all()
    elif current_user.role == models.UserRole.ADMIN:
        courses = db.query(models.Course).all()
    else:
        courses = db.query(models.Course).all()
    
    return [course_to_response(course, db) for course in courses]


@app.get("/api/courses/enrolled", response_model=List[schemas.CourseResponse])
def get_enrolled_courses(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == models.UserRole.STUDENT:
        enrollments = db.query(models.CourseEnrollment).filter(
            models.CourseEnrollment.student_id == current_user.id,
            models.CourseEnrollment.status == models.EnrollmentStatus.APPROVED
        ).all()
        course_ids = [e.course_id for e in enrollments]
        courses = db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()
        return [course_to_response(course, db) for course in courses]
    else:
        return []


@app.get("/api/courses/{course_id}", response_model=schemas.CourseResponse)
def get_course(
    course_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return course_to_response(course, db)


@app.post("/api/courses", response_model=schemas.CourseResponse)
def create_course(
    course_data: schemas.CourseCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.PROFESSOR:
        raise HTTPException(status_code=403, detail="Only professors can create courses")
    new_course = models.Course(
        name=course_data.name,
        code=course_data.code,
        description=course_data.description,
        level=course_data.level,
        professor_id=current_user.id
    )
    db.add(new_course)
    db.flush()
    for topic_data in course_data.topics:
        new_topic = models.CourseTopic(
            course_id=new_course.id,
            name=topic_data.name,
            description=topic_data.description,
            order=topic_data.order
        )
        db.add(new_topic)
        db.flush()
        
        for subtopic_data in topic_data.subtopics:
            new_subtopic = models.TopicSubtopic(
                topic_id=new_topic.id,
                name=subtopic_data.name,
                description=subtopic_data.description,
                order=subtopic_data.order
            )
            db.add(new_subtopic)
    
    db.commit()
    db.refresh(new_course)
    
    return course_to_response(new_course, db)


@app.put("/api/courses/{course_id}", response_model=schemas.CourseResponse)
def update_course(
    course_id: str,
    course_data: schemas.CourseUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.professor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this course")
    
    if course_data.name is not None:
        course.name = course_data.name
    if course_data.code is not None:
        course.code = course_data.code
    if course_data.description is not None:
        course.description = course_data.description
    if course_data.level is not None:
        course.level = course_data.level
    
    db.commit()
    db.refresh(course)
    
    return course_to_response(course, db)


@app.post("/api/courses/{course_id}/enroll")
def request_enrollment(
    course_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can request enrollment")
    
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    existing = db.query(models.CourseEnrollment).filter(
        models.CourseEnrollment.course_id == course_id,
        models.CourseEnrollment.student_id == current_user.id
    ).first()
    
    if existing:
        if existing.status == models.EnrollmentStatus.APPROVED:
            raise HTTPException(status_code=400, detail="Already enrolled in this course")
        elif existing.status == models.EnrollmentStatus.PENDING:
            raise HTTPException(status_code=400, detail="Enrollment request already pending")
    enrollment = models.CourseEnrollment(
        course_id=course_id,
        student_id=current_user.id,
        status=models.EnrollmentStatus.PENDING
    )
    db.add(enrollment)
    db.commit()
    
    return {"message": "Enrollment request submitted"}


@app.post("/api/courses/{course_id}/enrollments/{enrollment_id}/approve")
def approve_enrollment(
    course_id: str,
    enrollment_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.professor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    enrollment = db.query(models.CourseEnrollment).filter(
        models.CourseEnrollment.id == enrollment_id,
        models.CourseEnrollment.course_id == course_id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    if enrollment.status == models.EnrollmentStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Enrollment already approved")
    
    enrollment.status = models.EnrollmentStatus.APPROVED
    enrollment.enrolled_at = func.now()
    db.commit()
    db.refresh(enrollment)
    
    return {"message": "Student approved"}


@app.post("/api/courses/{course_id}/enrollments/{enrollment_id}/reject")
def reject_enrollment(
    course_id: str,
    enrollment_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.professor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    enrollment = db.query(models.CourseEnrollment).filter(
        models.CourseEnrollment.id == enrollment_id,
        models.CourseEnrollment.course_id == course_id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment.status = models.EnrollmentStatus.REJECTED
    db.commit()
    
    return {"message": "Student rejected"}


@app.delete("/api/courses/{course_id}/enrollments/{enrollment_id}")
def remove_student(
    course_id: str,
    enrollment_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.professor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    enrollment = db.query(models.CourseEnrollment).filter(
        models.CourseEnrollment.id == enrollment_id,
        models.CourseEnrollment.course_id == course_id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    db.delete(enrollment)
    db.commit()
    
    return {"message": "Student removed from course"}



@app.get("/api/exams", response_model=List[schemas.ExamResponse])
def get_exams(
    course_id: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Exam).options(
        joinedload(models.Exam.questions).joinedload(models.Question.gold_steps)
    )
    if current_user.role == models.UserRole.STUDENT:
        query = query.filter(models.Exam.is_published == True)
    
    if course_id:
        query = query.filter(models.Exam.course_id == course_id)
    
    exams = query.all()
    
    result = []
    for exam in exams:
        questions_data = []
        for question in exam.questions:
            gold_steps = [
                schemas.GoldSolutionStepResponse(
                    stepNumber=step.step_number,
                    description=step.description or "",
                    expression=step.expression,
                    latex=step.latex or "",
                    points=step.points
                )
                for step in question.gold_steps
            ]
            
            questions_data.append(
                schemas.QuestionResponse(
                    id=question.id,
                    number=question.number,
                    text=question.text,
                    points=question.points,
                    goldSolution=schemas.GoldSolutionResponse(
                        steps=gold_steps,
                        finalAnswer=question.final_answer or "",
                        finalAnswerLatex=question.final_answer_latex or ""
                    )
                )
            )
        
        result.append(
            schemas.ExamResponse(
                id=exam.id,
                courseId=exam.course_id,
                title=exam.title,
                description=exam.description,
                questions=questions_data,
                totalPoints=exam.total_points,
                dueDate=exam.due_date,
                isPublished=exam.is_published or False,
                publishedAt=exam.published_at,
                createdAt=exam.created_at
            )
        )
    
    return result


@app.post("/api/exams", response_model=schemas.ExamResponse)
def create_exam(
    exam_data: schemas.ExamCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.PROFESSOR:
        raise HTTPException(status_code=403, detail="Only professors can create exams")
    total_points = sum(q.points for q in exam_data.questions)
    new_exam = models.Exam(
        course_id=exam_data.courseId,
        title=exam_data.title,
        description=exam_data.description,
        total_points=total_points,
        due_date=exam_data.dueDate,
        is_published=False,
        published_at=None
    )
    db.add(new_exam)
    db.flush()
    for question_data in exam_data.questions:
        new_question = models.Question(
            exam_id=new_exam.id,
            number=question_data.number,
            text=question_data.text,
            points=question_data.points,
            final_answer=question_data.finalAnswer,
            final_answer_latex=question_data.finalAnswerLatex
        )
        db.add(new_question)
        db.flush()
        for step_data in question_data.goldSolutionSteps:
            new_step = models.GoldSolutionStep(
                question_id=new_question.id,
                step_number=step_data.stepNumber,
                description=step_data.description,
                expression=step_data.expression,
                latex=step_data.latex,
                points=step_data.points,
                required=step_data.required
            )
            db.add(new_step)
    
    db.commit()
    db.refresh(new_exam)
    return get_exams(db=db, current_user=current_user)[0]


@app.get("/api/exams/{exam_id}", response_model=schemas.ExamResponse)
def get_exam(
    exam_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exam = db.query(models.Exam).options(
        joinedload(models.Exam.questions).joinedload(models.Question.gold_steps)
    ).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if current_user.role == models.UserRole.STUDENT and not exam.is_published:
        raise HTTPException(status_code=403, detail="This exam is not available")
    questions_data = []
    for question in exam.questions:
        gold_steps = [
            schemas.GoldSolutionStepResponse(
                stepNumber=step.step_number,
                description=step.description or "",
                expression=step.expression,
                latex=step.latex or "",
                points=step.points
            )
            for step in question.gold_steps
        ]
        
        questions_data.append(
            schemas.QuestionResponse(
                id=question.id,
                number=question.number,
                text=question.text,
                points=question.points,
                goldSolution=schemas.GoldSolutionResponse(
                    steps=gold_steps,
                    finalAnswer=question.final_answer or "",
                    finalAnswerLatex=question.final_answer_latex or ""
                )
            )
        )
    
    return schemas.ExamResponse(
        id=exam.id,
        courseId=exam.course_id,
        title=exam.title,
        description=exam.description,
        questions=questions_data,
        totalPoints=exam.total_points,
        dueDate=exam.due_date,
        isPublished=exam.is_published or False,
        publishedAt=exam.published_at,
        createdAt=exam.created_at
    )


@app.put("/api/exams/{exam_id}", response_model=schemas.ExamResponse)
def update_exam(
    exam_id: str,
    exam_data: schemas.ExamCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if current_user.role != models.UserRole.PROFESSOR:
        raise HTTPException(status_code=403, detail="Only professors can update exams")
    exam.course_id = exam_data.courseId
    exam.title = exam_data.title
    exam.description = exam_data.description
    exam.due_date = exam_data.dueDate
    total_points = sum(q.points for q in exam_data.questions)
    exam.total_points = total_points
    for question in exam.questions:
        db.delete(question)
    db.flush()
    for question_data in exam_data.questions:
        new_question = models.Question(
            exam_id=exam.id,
            number=question_data.number,
            text=question_data.text,
            points=question_data.points,
            final_answer=question_data.finalAnswer,
            final_answer_latex=question_data.finalAnswerLatex,
            question_type=question_data.questionType,
            rich_content=str(question_data.richContent) if question_data.richContent else None,
            outline_level=question_data.outlineLevel,
            parent_question_id=question_data.parentQuestionId
        )
        db.add(new_question)
        db.flush()
        for step_data in question_data.goldSolutionSteps:
            new_step = models.GoldSolutionStep(
                question_id=new_question.id,
                step_number=step_data.stepNumber,
                description=step_data.description,
                expression=step_data.expression,
                latex=step_data.latex,
                points=step_data.points,
                required=step_data.required
            )
            db.add(new_step)
    
    db.commit()
    db.refresh(exam)
    return get_exam(exam_id=exam_id, current_user=current_user, db=db)


@app.post("/api/exams/{exam_id}/publish", response_model=schemas.ExamResponse)
def publish_exam(
    exam_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    course = db.query(models.Course).filter(models.Course.id == exam.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.professor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to publish this exam")
    exam.is_published = True
    exam.published_at = func.now()
    db.commit()
    db.refresh(exam)
    
    return get_exam(exam_id=exam_id, current_user=current_user, db=db)


@app.post("/api/exams/{exam_id}/unpublish", response_model=schemas.ExamResponse)
def unpublish_exam(
    exam_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Check if user owns the course
    course = db.query(models.Course).filter(models.Course.id == exam.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.professor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to unpublish this exam")
    
    exam.is_published = False
    exam.published_at = None
    db.commit()
    db.refresh(exam)
    
    return get_exam(exam_id=exam_id, current_user=current_user, db=db)


@app.get("/api/exams/{exam_id}/download")
def download_exam_pdf(
    exam_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from fastapi.responses import HTMLResponse
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    course = db.query(models.Course).filter(models.Course.id == exam.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if current_user.role == models.UserRole.STUDENT and not exam.is_published:
        raise HTTPException(status_code=403, detail="This exam is not available")
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{exam.title}</title>
        <style>
            @media print {{
                @page {{ margin: 1in; }}
            }}
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{
                text-align: center;
                color: #333;
                border-bottom: 2px solid #333;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #555;
                margin-top: 30px;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
            }}
            .exam-info {{
                margin: 20px 0;
                padding: 15px;
                background-color: #f5f5f5;
                border-radius: 5px;
            }}
            .question {{
                margin: 25px 0;
                padding: 15px;
                border-left: 4px solid #6366f1;
                background-color: #fafafa;
            }}
            .question-text {{
                margin: 10px 0;
            }}
            .points {{
                color: #6366f1;
                font-weight: bold;
            }}
            .solution-steps {{
                margin-top: 15px;
                padding: 10px;
                background-color: #fff;
                border: 1px solid #ddd;
                border-radius: 3px;
            }}
            .step {{
                margin: 8px 0;
                padding-left: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>{exam.title}</h1>
        
        <div class="exam-info">
            <p><strong>Course:</strong> {course.code} - {course.name}</p>
            <p><strong>Total Points:</strong> {exam.total_points}</p>
    """
    
    if exam.description:
        html_content += f'<p><strong>Description:</strong> {exam.description}</p>'
    
    if exam.due_date:
        html_content += f'<p><strong>Due Date:</strong> {exam.due_date.strftime("%Y-%m-%d %H:%M")}</p>'
    
    html_content += "</div>"
    for question in exam.questions:
        question_text = question.text.replace('\n', '<br>').replace('<', '&lt;').replace('>', '&gt;')
        html_content += f"""
        <div class="question">
            <h2>Question {question.number} <span class="points">({question.points} points)</span></h2>
            <div class="question-text">{question_text}</div>
        """
        if question.gold_steps:
            html_content += '<div class="solution-steps"><strong>Solution Steps:</strong>'
            for step in question.gold_steps:
                step_desc = step.description.replace('<', '&lt;').replace('>', '&gt;')
                html_content += f'<div class="step"><strong>Step {step.step_number}:</strong> {step_desc}</div>'
            html_content += '</div>'
        
        html_content += '</div>'
    
    html_content += """
    </body>
    </html>
    """
    
    return HTMLResponse(
        content=html_content,
        headers={"Content-Disposition": f"inline; filename={exam.title.replace(' ', '_')}.html"}
    )


@app.post("/api/submissions")
async def submit_exam(
    exam_id: str = Form(...),
    images: Optional[List[UploadFile]] = File(None),
    answers: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    has_images = images and len(images) > 0
    has_answers = answers and answers.strip()
    
    if not has_images and not has_answers:
        raise HTTPException(status_code=400, detail="At least one answer (typed or image) must be provided")
    new_submission = models.Submission(
        exam_id=exam_id,
        student_id=current_user.id,
        status=models.SubmissionStatus.PENDING,
        max_score=exam.total_points
    )
    db.add(new_submission)
    db.flush()
    if has_images and images:
        submission_dir = UPLOAD_DIR / new_submission.id
        submission_dir.mkdir(exist_ok=True)
        for idx, image_file in enumerate(images, start=1):
            file_ext = Path(image_file.filename).suffix
            image_path = submission_dir / f"page_{idx}{file_ext}"
            
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            submission_image = models.SubmissionImage(
                submission_id=new_submission.id,
                image_path=str(image_path),
                page_number=idx
            )
            db.add(submission_image)
    if answers:
        try:
            answers_data = json.loads(answers)
            new_submission.typed_answers = answers
        except json.JSONDecodeError:
            pass
    
    db.commit()
    db.refresh(new_submission)
    
    return {
        "id": new_submission.id,
        "status": "success",
        "message": "Submission created successfully. Processing will begin shortly."
    }


@app.get("/api/submissions", response_model=List[schemas.SubmissionResponse])
def get_submissions(
    exam_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Submission)
    if current_user.role == models.UserRole.STUDENT:
        query = query.filter(models.Submission.student_id == current_user.id)
    elif current_user.role == models.UserRole.PROFESSOR:
        query = query.join(models.Exam).join(models.Course).filter(
            models.Course.professor_id == current_user.id
        )
    
    if exam_id:
        query = query.filter(models.Submission.exam_id == exam_id)
    
    if status:
        query = query.filter(models.Submission.status == status)
    
    submissions = query.order_by(models.Submission.submitted_at.desc()).all()
    
    result = []
    for submission in submissions:
        student = db.query(models.User).filter(models.User.id == submission.student_id).first()
        answers = []
        for grading_result in submission.grading_results:
            step_results = [
                schemas.StepResultResponse(
                    stepNumber=step.step_number,
                    isCorrect=step.is_correct,
                    score=step.score,
                    maxScore=step.max_score,
                    feedback=step.feedback or "",
                    expected=step.expected,
                    received=step.received
                )
                for step in grading_result.step_results
            ]
            
            question = db.query(models.Question).filter(
                models.Question.id == grading_result.question_id
            ).first()
            
            answers.append(
                schemas.SubmittedAnswerResponse(
                    questionId=grading_result.question_id,
                    questionNumber=question.number if question else 0,
                    extractedText=grading_result.extracted_text,
                    extractedLatex=grading_result.extracted_latex,
                    extractedSteps=[],
                    gradingResult=schemas.GradingResultResponse(
                        score=grading_result.score,
                        maxScore=grading_result.max_score,
                        feedback=grading_result.feedback or "",
                        stepResults=step_results,
                        isCorrect=grading_result.is_correct
                    ) if submission.status == models.SubmissionStatus.GRADED else None
                )
            )
        
        result.append(
            schemas.SubmissionResponse(
                id=submission.id,
                examId=submission.exam_id,
                studentId=submission.student_id,
                studentName=student.name if student else "Unknown",
                submittedAt=submission.submitted_at,
                status=submission.status,
                answers=answers,
                totalScore=submission.total_score,
                maxScore=submission.max_score
            )
        )
    
    return result


@app.get("/api/submissions/{submission_id}", response_model=schemas.SubmissionResponse)
def get_submission(
    submission_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    submission = db.query(models.Submission).filter(
        models.Submission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if current_user.role == models.UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.role == models.UserRole.PROFESSOR:
        exam = db.query(models.Exam).filter(models.Exam.id == submission.exam_id).first()
        if exam:
            course = db.query(models.Course).filter(models.Course.id == exam.course_id).first()
            if not course or course.professor_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")
    student = db.query(models.User).filter(models.User.id == submission.student_id).first()
    answers = []
    for grading_result in submission.grading_results:
        step_results = [
            schemas.StepResultResponse(
                stepNumber=step.step_number,
                isCorrect=step.is_correct,
                score=step.score,
                maxScore=step.max_score,
                feedback=step.feedback or "",
                expected=step.expected,
                received=step.received
            )
            for step in grading_result.step_results
        ]
        
        question = db.query(models.Question).filter(
            models.Question.id == grading_result.question_id
        ).first()
        
        answers.append(
            schemas.SubmittedAnswerResponse(
                questionId=grading_result.question_id,
                questionNumber=question.number if question else 0,
                extractedText=grading_result.extracted_text,
                extractedLatex=grading_result.extracted_latex,
                extractedSteps=[],
                gradingResult=schemas.GradingResultResponse(
                    score=grading_result.score,
                    maxScore=grading_result.max_score,
                    feedback=grading_result.feedback or "",
                    stepResults=step_results,
                    isCorrect=grading_result.is_correct
                ) if submission.status == models.SubmissionStatus.GRADED else None
            )
        )
    
    return schemas.SubmissionResponse(
        id=submission.id,
        examId=submission.exam_id,
        studentId=submission.student_id,
        studentName=student.name if student else "Unknown",
        submittedAt=submission.submitted_at,
        status=submission.status,
        answers=answers,
        totalScore=submission.total_score,
        maxScore=submission.max_score
    )


@app.post("/api/submissions/{submission_id}/grade")
async def grade_submission(
    submission_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in [models.UserRole.PROFESSOR, models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only professors can grade submissions")
    submission = db.query(models.Submission).filter(
        models.Submission.id == submission_id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    submission.status = models.SubmissionStatus.GRADING
    db.commit()
    
    try:
        exam = db.query(models.Exam).options(
            joinedload(models.Exam.questions).joinedload(models.Question.gold_steps)
        ).filter(models.Exam.id == submission.exam_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        questions = exam.questions
        images = submission.images
        typed_answers_data = None
        if submission.typed_answers:
            try:
                parsed = json.loads(submission.typed_answers)
                if isinstance(parsed, list) and len(parsed) > 0:
                    typed_answers_data = parsed
            except (json.JSONDecodeError, TypeError):
                pass
        
        if not images and not typed_answers_data:
            raise HTTPException(status_code=400, detail="No answers found for submission (neither images nor typed answers)")
        total_score = 0.0
        if typed_answers_data:
            for answer_data in typed_answers_data:
                question_id = answer_data.get('questionId')
                question_number = answer_data.get('questionNumber', 0)
                typed_answer = answer_data.get('typedAnswer', '')
                question = None
                if question_id:
                    question = next((q for q in questions if q.id == question_id), None)
                elif question_number > 0:
                    question = next((q for q in questions if q.number == question_number), None)
                
                if not question:
                    continue
                import re
                from html import unescape
                clean_text = re.sub('<[^<]+?>', '', typed_answer)
                clean_text = unescape(clean_text).strip()
                
                if not clean_text or clean_text in ['Type your answer here...', '']:
                    continue
                student_steps = [s.strip() for s in re.split(r'[.\n]', clean_text) if s.strip()]
                if not student_steps:
                    student_steps = [clean_text]
                gold_steps = [
                    GraderStep(
                        content=step.description or step.expression or "",
                        points=float(step.points),
                        required=step.required
                    )
                    for step in question.gold_steps
                ]
                
                if not gold_steps:
                    continue
                grader = MathGrader(gold_steps)
                grading_result = grader.grade(student_steps)
                db_grading_result = models.GradingResult(
                    submission_id=submission.id,
                    question_id=question.id,
                    extracted_text="\n".join(student_steps),
                    score=grading_result['total_score'],
                    max_score=grading_result['max_score'],
                    feedback=f"Scored {grading_result['percentage']:.1f}%",
                    is_correct=grading_result['percentage'] >= 70
                )
                db.add(db_grading_result)
                db.flush()
                for idx, (student_step, evaluation) in enumerate(
                    zip(student_steps, grading_result['evaluations']), start=1
                ):
                    matched_gold = None
                    if evaluation.matched_gold_step is not None and evaluation.matched_gold_step < len(gold_steps):
                        matched_gold = gold_steps[evaluation.matched_gold_step].content
                    
                    step_result = models.StepResult(
                        grading_result_id=db_grading_result.id,
                        step_number=idx,
                        student_text=student_step,
                        is_correct=evaluation.status.value == "Correct",
                        score=evaluation.points_earned,
                        max_score=gold_steps[evaluation.matched_gold_step].points if evaluation.matched_gold_step is not None and evaluation.matched_gold_step < len(gold_steps) else 0,
                        feedback=evaluation.feedback,
                        expected=matched_gold,
                        received=student_step
                    )
                    db.add(step_result)
                
                total_score += grading_result['total_score']
        if images:
            for image in images:
                image_path = Path(image.image_path)
                if not image_path.exists():
                    continue
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                
                ocr_result = ocr_processor.extract_steps_from_file(
                    image_bytes,
                    image_path.name
                )
                
                student_steps = ocr_result.steps
                if image.page_number <= len(questions):
                    question = questions[image.page_number - 1]
                    gold_steps = [
                        GraderStep(
                            content=step.description or step.expression or "",
                            points=float(step.points),
                            required=step.required
                        )
                        for step in question.gold_steps
                    ]
                    grader = MathGrader(gold_steps)
                    grading_result = grader.grade(student_steps)
                    db_grading_result = models.GradingResult(
                        submission_id=submission.id,
                        question_id=question.id,
                        extracted_text="\n".join(student_steps),
                        score=grading_result['total_score'],
                        max_score=grading_result['max_score'],
                        feedback=f"Scored {grading_result['percentage']:.1f}%",
                        is_correct=grading_result['percentage'] >= 70
                    )
                    db.add(db_grading_result)
                    db.flush()
                    for idx, (student_step, evaluation) in enumerate(
                        zip(student_steps, grading_result['evaluations']), start=1
                    ):
                        matched_gold = None
                        if evaluation.matched_gold_step is not None and evaluation.matched_gold_step < len(gold_steps):
                            matched_gold = gold_steps[evaluation.matched_gold_step].content
                        
                        step_result = models.StepResult(
                            grading_result_id=db_grading_result.id,
                            step_number=idx,
                            student_text=student_step,
                            is_correct=evaluation.status.value == "Correct",
                            score=evaluation.points_earned,
                            max_score=gold_steps[evaluation.matched_gold_step].points if evaluation.matched_gold_step is not None and evaluation.matched_gold_step < len(gold_steps) else 0,
                            feedback=evaluation.feedback,
                            expected=matched_gold,
                            received=student_step
                        )
                        db.add(step_result)
                    
                    total_score += grading_result['total_score']
        submission.total_score = total_score
        submission.status = models.SubmissionStatus.GRADED
        submission.graded_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "success",
            "message": "Submission graded successfully",
            "totalScore": total_score,
            "maxScore": exam.total_points
        }
    except HTTPException:
        db.rollback()
        submission.status = models.SubmissionStatus.PENDING
        db.commit()
        raise
    except Exception as e:
        db.rollback()
        submission.status = models.SubmissionStatus.PENDING
        db.commit()
        import traceback
        print(f"Error grading submission {submission_id}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error during grading: {str(e)}"
        )


@app.get("/api/dashboard/stats", response_model=schemas.DashboardStatsResponse)
def get_dashboard_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == models.UserRole.PROFESSOR:
        courses_count = db.query(models.Course).filter(
            models.Course.professor_id == current_user.id
        ).count()
        
        exams_count = db.query(models.Exam).join(models.Course).filter(
            models.Course.professor_id == current_user.id
        ).count()
        
        submissions_count = db.query(models.Submission).join(models.Exam).join(models.Course).filter(
            models.Course.professor_id == current_user.id
        ).count()
        pending_count = db.query(models.Submission).join(models.Exam).join(models.Course).filter(
            models.Course.professor_id == current_user.id,
            models.Submission.status == models.SubmissionStatus.PENDING
        ).count()
        graded_submissions = db.query(models.Submission).join(models.Exam).join(models.Course).filter(
            models.Course.professor_id == current_user.id,
            models.Submission.status == models.SubmissionStatus.GRADED,
            models.Submission.total_score.isnot(None)
        ).all()
        
        if graded_submissions:
            avg_score = sum(
                (s.total_score / s.max_score * 100) for s in graded_submissions
            ) / len(graded_submissions)
        else:
            avg_score = None
    elif current_user.role == models.UserRole.STUDENT:
        courses_count = db.query(models.Course).count()
        exams_count = db.query(models.Exam).count()
        
        submissions_count = db.query(models.Submission).filter(
            models.Submission.student_id == current_user.id
        ).count()
        
        pending_count = db.query(models.Submission).filter(
            models.Submission.student_id == current_user.id,
            models.Submission.status.in_([models.SubmissionStatus.PENDING, models.SubmissionStatus.GRADING])
        ).count()
        
        # Average score
        graded_submissions = db.query(models.Submission).filter(
            models.Submission.student_id == current_user.id,
            models.Submission.status == models.SubmissionStatus.GRADED,
            models.Submission.total_score.isnot(None)
        ).all()
        
        if graded_submissions:
            avg_score = sum(
                (s.total_score / s.max_score * 100) for s in graded_submissions
            ) / len(graded_submissions)
        else:
            avg_score = None
    else:
        courses_count = db.query(models.Course).count()
        exams_count = db.query(models.Exam).count()
        submissions_count = db.query(models.Submission).count()
        pending_count = db.query(models.Submission).filter(
            models.Submission.status == models.SubmissionStatus.PENDING
        ).count()
        
        graded_submissions = db.query(models.Submission).filter(
            models.Submission.status == models.SubmissionStatus.GRADED,
            models.Submission.total_score.isnot(None)
        ).all()
        
        if graded_submissions:
            avg_score = sum(
                (s.total_score / s.max_score * 100) for s in graded_submissions
            ) / len(graded_submissions)
        else:
            avg_score = None
    
    return schemas.DashboardStatsResponse(
        totalCourses=courses_count,
        totalExams=exams_count,
        totalSubmissions=submissions_count,
        pendingGrading=pending_count,
        averageScore=round(avg_score, 1) if avg_score else None
    )


@app.get("/")
def root():
    return {
        "name": "EasyGrade API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

