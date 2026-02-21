"""
FastAPI backend for EasyGrade
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func
from typing import List, Optional, Tuple
import os
import re
import logging
from pathlib import Path
import shutil
from datetime import datetime, timedelta
import jwt
import json

logger = logging.getLogger(__name__)

from database import get_db, init_db, engine
import models
import schemas
from math_grader import Step as GraderStep
from hybrid_grader import HybridGrader
from ocr.ocr_pipeline import OCRProcessor
from exam_parser import ExamParser

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

import bcrypt

# We'll use bcrypt directly (simpler and more reliable)
pwd_context = None  # Not needed anymore

# Security
security = HTTPBearer()

# Create FastAPI app
app = FastAPI(
    title="EasyGrade API",
    description="AI-Powered Math Exam Grading System",
    version="1.0.0"
)

# CORS middleware for React frontend
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8080,http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OCR processor
ocr_processor = OCRProcessor(language="en", dpi=300, psm=6, use_easyocr=False)


def _is_pdf_text_readable(text: str) -> bool:
    """Return True if extracted text looks usable (not empty or OCR garbage)."""
    if not text or len(text.strip()) < 30:
        return False
    word_chars = sum(
        1 for c in text
        if c.isalnum() or c.isspace() or c in ".,;:!?'\"()-+=/^*[]"
    )
    symbol_soup = sum(1 for c in text if c in "|~}{\\<>_")
    ratio = word_chars / max(len(text), 1)
    if ratio < 0.25 or (symbol_soup / max(len(text), 1)) > 0.15:
        return False
    return True


def _extract_text_from_pdf_bytes(file_content: bytes) -> Optional[str]:
    """
    Extract text from PDF so it follows the same structure as .txt (line-by-line).
    Tries, in order: pdftotext (poppler), then pypdf. This gives layout-preserved
    text that the exam parser can read like a plain text file.
    """
    # Marker injected between pages so the exam parser can track page numbers
    _PAGE_BREAK = "<<PAGEBREAK>>"

    # 1. Prefer pdftotext (poppler) - same engine as pdf2image, produces clean line-by-line text
    try:
        import subprocess
        result = subprocess.run(
            ["pdftotext", "-layout", "-", "-"],
            input=file_content,
            capture_output=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout:
            text = result.stdout.decode("utf-8", errors="replace")
            # pdftotext separates pages with form-feed (\x0c) — replace with our marker
            text = re.sub(r'\x0c', f'\n{_PAGE_BREAK}\n', text).strip()
            if _is_pdf_text_readable(text):
                logger.info("PDF text extracted with pdftotext (poppler)")
                return text
    except FileNotFoundError:
        logger.debug("pdftotext not found (install poppler-utils, e.g. brew install poppler)")
    except subprocess.TimeoutExpired:
        logger.warning("pdftotext timed out")
    except Exception as e:
        logger.debug(f"pdftotext failed: {e}")

    # 2. Fallback: pypdf (layout mode when available)
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(file_content))
        parts = []
        for page_num, page in enumerate(reader.pages):
            try:
                t = page.extract_text(extraction_mode="layout")
            except Exception:
                t = page.extract_text()
            if t and t.strip():
                if page_num > 0:
                    parts.append(_PAGE_BREAK)
                parts.append(t.strip())
        if not parts:
            return None
        text = "\n".join(parts).strip()
        if not _is_pdf_text_readable(text):
            return None
        logger.info("PDF text extracted with pypdf")
        return text
    except Exception as e:
        logger.debug(f"pypdf extraction failed: {e}")
        return None



def _extract_pdf_diagrams(pdf_bytes: bytes, questions: list) -> dict:
    """
    Extract diagrams from PDF pages for upload_exam.

    Strategy (never attaches text/gold-solution content):
    1. Use pdfplumber to detect embedded raster image objects and their bounding boxes.
    2. Use pdfplumber to locate the "Gold Solution:" text on each page (y coordinate).
    3. Render the page with pdf2image at 150 dpi.
    4a. If embedded images exist on a page: crop each image bbox from the rendered page
        (skipping any that are below the gold solution line).
    4b. If NO embedded images (vector drawing): crop the entire rendered page above
        the gold solution line (shows the diagram without the answer).

    Returns {page_num: [{'data': bytes, 'name': str}, ...]}
    """
    import io
    result: dict = {}

    # Keywords in question text that indicate a visual element is present
    _DIAGRAM_KW = {
        'diagram', 'graph', 'figure', 'chart', 'plot', 'sketch',
        'image', 'illustration', 'curve', 'draw', 'label', 'arrow',
        'shown', 'below', 'apparatus', 'setup', 'experiment',
    }

    # Solution section markers (lower-case) used to find where answers start on the page
    _SOL_MARKERS = [
        'gold solution', 'model answer', 'expected answer',
        'correct answer', 'answer key', 'solution:',
    ]

    pages_needed = {q.get('page_num', i) for i, q in enumerate(questions)}
    if not pages_needed:
        return result

    # ── Step 1: Gather per-page info with pdfplumber ─────────────────────────
    page_info: dict = {}  # page_num -> {images, gold_top, height, width}
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for pg_num, page in enumerate(pdf.pages):
                if pg_num not in pages_needed:
                    continue

                info = {
                    'images': [],
                    'gold_top': None,
                    'height': page.height,
                    'width': page.width,
                }

                # Embedded raster image bounding boxes
                for img in (page.images or []):
                    x0 = img.get('x0', 0)
                    top = img.get('top', 0)
                    x1 = img.get('x1', page.width)
                    bottom = img.get('bottom', page.height)
                    w = x1 - x0
                    h = bottom - top
                    if w > 40 and h > 40:   # skip tiny decorative icons
                        info['images'].append({'x0': x0, 'top': top, 'x1': x1, 'bottom': bottom})

                # Find gold solution text y-position (pdfplumber coords: top from page top)
                try:
                    text_lower = (page.extract_text() or '').lower()
                    for marker in _SOL_MARKERS:
                        if marker in text_lower:
                            # Find the word's top coordinate
                            words = page.extract_words() or []
                            for wi, word in enumerate(words):
                                wl = word['text'].lower()
                                if 'gold' == wl and wi + 1 < len(words) and 'solution' in words[wi + 1]['text'].lower():
                                    info['gold_top'] = word['top']
                                    break
                                if wl.rstrip(':') in ('solution', 'answer') and wi > 0 and words[wi - 1]['text'].lower() in ('model', 'expected', 'correct', 'gold'):
                                    info['gold_top'] = words[wi - 1]['top']
                                    break
                                if 'solution:' == wl:
                                    info['gold_top'] = word['top']
                                    break
                            if info['gold_top'] is not None:
                                break
                except Exception:
                    pass

                page_info[pg_num] = info
    except Exception as e:
        logger.warning(f"pdfplumber diagram scan failed: {e}")
        return result

    # ── Step 2: Decide which pages need rendering ─────────────────────────────
    pages_to_render: set = set()
    for qi, q in enumerate(questions):
        pg_num = q.get('page_num', qi)
        info = page_info.get(pg_num)
        if info is None:
            continue
        q_text = (q.get('text', '') + ' ' + ' '.join(
            sq.get('text', '') for sq in q.get('sub_questions', [])
        )).lower()
        has_ref = any(kw in q_text for kw in _DIAGRAM_KW)
        if info['images'] or (has_ref and info['gold_top'] is not None):
            pages_to_render.add(pg_num)

    if not pages_to_render:
        return result

    # ── Step 3: Render pages and crop ────────────────────────────────────────
    try:
        from pdf2image import convert_from_bytes
        from PIL import Image as PILImage
        dpi = 150
        rendered = convert_from_bytes(pdf_bytes, dpi=dpi)

        for pg_num in pages_to_render:
            if pg_num >= len(rendered):
                continue

            info = page_info[pg_num]
            page_img = rendered[pg_num]
            pts_h = info['height'] or 792
            pts_w = info['width'] or 612
            sx = page_img.width / pts_w
            sy = page_img.height / pts_h
            gold_top = info.get('gold_top')

            saved: list = []

            if info['images']:
                # Crop each detected image bbox (skip those below gold solution)
                for img_idx, bbox in enumerate(info['images']):
                    if gold_top is not None and bbox['top'] >= gold_top - 5:
                        continue  # this image is in the answer section
                    pad = 8
                    px0 = max(0, int(bbox['x0'] * sx) - pad)
                    ptop = max(0, int(bbox['top'] * sy) - pad)
                    px1 = min(page_img.width, int(bbox['x1'] * sx) + pad)
                    pbot = min(page_img.height, int(bbox['bottom'] * sy) + pad)
                    if px1 - px0 > 40 and pbot - ptop > 40:
                        cropped = page_img.crop((px0, ptop, px1, pbot))
                        buf = io.BytesIO()
                        cropped.convert("RGB").save(buf, format="PNG")
                        saved.append({'data': buf.getvalue(), 'name': f'diagram_p{pg_num + 1}_{img_idx + 1}.png'})

            else:
                # Vector drawing case: crop the page above the gold solution line
                if gold_top is not None:
                    crop_px = max(60, int(gold_top * sy) - 12)
                    cropped = page_img.crop((0, 0, page_img.width, crop_px))
                    buf = io.BytesIO()
                    cropped.convert("RGB").save(buf, format="PNG")
                    saved.append({'data': buf.getvalue(), 'name': f'diagram_p{pg_num + 1}.png'})

            if saved:
                result[pg_num] = saved

    except Exception as e:
        logger.warning(f"PDF diagram render/crop failed: {e}")

    return result


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Hash a password"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
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
    """Get current authenticated user from JWT token"""
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
    """Convert User model to UserResponse schema"""
    return schemas.UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        avatar=user.avatar,
        createdAt=user.created_at
    )


# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
def startup_event():
    """Initialize database on startup"""
    init_db()
    
    # Create demo users if database is empty
    db = next(get_db())
    if db.query(models.User).count() == 0:
        # Create demo professor
        professor = models.User(
            name="Dr. Sarah Chen",
            email="professor@university.edu",
            password_hash=get_password_hash("password"),
            role=models.UserRole.PROFESSOR
        )
        # Create demo student
        student = models.User(
            name="Alex Johnson",
            email="student@university.edu",
            password_hash=get_password_hash("password"),
            role=models.UserRole.STUDENT
        )
        # Create demo admin
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
    """Authenticate user and return JWT token"""
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if role matches (for demo purposes)
    if user.role.value != credentials.role.value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect role selected"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id, "role": user.role.value})
    
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=user_to_response(user)
    )


@app.post("/api/auth/register", response_model=schemas.Token)
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    new_user = models.User(
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token = create_access_token(data={"sub": new_user.id, "role": new_user.role.value})
    
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=user_to_response(new_user)
    )


@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Get current user info"""
    return user_to_response(current_user)



def course_to_response(course: models.Course, db: Session) -> schemas.CourseResponse:
    """Convert Course model to CourseResponse schema"""
    # Get topics with subtopics
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
        ))
    
    # Get enrollments
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
    
    # Count exams and submissions
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
    """Get all courses for current user"""
    query = db.query(models.Course).options(
        joinedload(models.Course.professor),
        selectinload(models.Course.exams).selectinload(models.Exam.submissions)
    )
    
    if current_user.role == models.UserRole.PROFESSOR:
        # Professors see only their courses
        courses = query.filter(models.Course.professor_id == current_user.id).all()
    elif current_user.role == models.UserRole.ADMIN:
        # Admins see all courses
        courses = query.all()
    else:
        # Students see all available courses
        courses = query.all()
    
    return [course_to_response(course, db) for course in courses]


@app.get("/api/courses/enrolled", response_model=List[schemas.CourseResponse])
def get_enrolled_courses(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get courses the current student is enrolled in (approved enrollments only)"""
    if current_user.role != models.UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can access enrolled courses")
    
    # Get approved enrollments
    enrollments = db.query(models.CourseEnrollment).filter(
        models.CourseEnrollment.student_id == current_user.id,
        models.CourseEnrollment.status == models.EnrollmentStatus.APPROVED
    ).all()
    
    course_ids = [e.course_id for e in enrollments]
    courses = db.query(models.Course).filter(models.Course.id.in_(course_ids)).all()
    
    return [course_to_response(course, db) for course in courses]


@app.get("/api/courses/{course_id}", response_model=schemas.CourseResponse)
def get_course(
    course_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single course by ID"""
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
    """Create a new course (professors only)"""
    if current_user.role != models.UserRole.PROFESSOR:
        raise HTTPException(status_code=403, detail="Only professors can create courses")
    
    # Create course
    new_course = models.Course(
        name=course_data.name,
        code=course_data.code,
        description=course_data.description,
        level=course_data.level,
        professor_id=current_user.id
    )
    db.add(new_course)
    db.flush()
    
    # Create topics and subtopics
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
    """Update a course (professor only)"""
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


# Enrollment endpoints
@app.post("/api/courses/{course_id}/enroll")
def request_enrollment(
    course_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request enrollment in a course (students)"""
    if current_user.role != models.UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can request enrollment")
    
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if already enrolled or pending
    existing = db.query(models.CourseEnrollment).filter(
        models.CourseEnrollment.course_id == course_id,
        models.CourseEnrollment.student_id == current_user.id
    ).first()
    
    if existing:
        if existing.status == models.EnrollmentStatus.APPROVED:
            raise HTTPException(status_code=400, detail="Already enrolled in this course")
        elif existing.status == models.EnrollmentStatus.PENDING:
            raise HTTPException(status_code=400, detail="Enrollment request already pending")
    
    # Create enrollment request
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
    """Approve a student enrollment (professor only)"""
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.professor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    enrollment = db.query(models.CourseEnrollment).filter(
        models.CourseEnrollment.id == enrollment_id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    enrollment.status = models.EnrollmentStatus.APPROVED
    enrollment.enrolled_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Student approved"}


@app.post("/api/courses/{course_id}/enrollments/{enrollment_id}/reject")
def reject_enrollment(
    course_id: str,
    enrollment_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject a student enrollment (professor only)"""
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.professor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    enrollment = db.query(models.CourseEnrollment).filter(
        models.CourseEnrollment.id == enrollment_id
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
    """Remove a student from course (professor only)"""
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.professor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    enrollment = db.query(models.CourseEnrollment).filter(
        models.CourseEnrollment.id == enrollment_id
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
    """Get all exams - students only see published exams"""
    query = db.query(models.Exam)
    
    if course_id:
        query = query.filter(models.Exam.course_id == course_id)
    
    # Students only see published exams in courses they're enrolled in
    if current_user.role == models.UserRole.STUDENT:
        query = query.filter(models.Exam.is_published == True)
        # Filter to only enrolled courses
        enrolled_course_ids = db.query(models.CourseEnrollment.course_id).filter(
            models.CourseEnrollment.student_id == current_user.id,
            models.CourseEnrollment.status == models.EnrollmentStatus.APPROVED
        ).all()
        enrolled_course_ids = [c[0] for c in enrolled_course_ids]
        if enrolled_course_ids:
            query = query.filter(models.Exam.course_id.in_(enrolled_course_ids))
        else:
            # No enrolled courses, return empty result
            query = query.filter(models.Exam.id == None)
    
    exams = query.options(
        selectinload(models.Exam.questions).selectinload(models.Question.gold_steps)
    ).all()
    
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
            
            display_text = _display_safe_text(question.text)
            rich_content_val = json.loads(question.rich_content) if question.rich_content and isinstance(question.rich_content, str) else (question.rich_content if question.rich_content else None)
            if display_text.startswith("[Question text could not be displayed") and rich_content_val:
                rich_content_val = {
                    "type": "doc",
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Question text could not be displayed. Re-upload the exam as PDF or .txt to restore content, or edit manually."}]
                    }]
                }
            questions_data.append(
                schemas.QuestionResponse(
                    id=question.id,
                    number=question.number,
                    text=display_text,
                    points=question.points,
                    goldSolution=schemas.GoldSolutionResponse(
                        steps=gold_steps,
                        finalAnswer=question.final_answer or "",
                        finalAnswerLatex=question.final_answer_latex or ""
                    ),
                    goldSolutionSteps=gold_steps,
                    finalAnswer=question.final_answer or "",
                    finalAnswerLatex=question.final_answer_latex or "",
                    questionType=getattr(question, 'question_type', 'standard'),
                    richContent=rich_content_val,
                    outlineLevel=getattr(question, 'outline_level', 1),
                    parentQuestionId=getattr(question, 'parent_question_id', None),
                    subQuestions=[],
                    attachments=[],
                    embeddedContent=[],
                    theories=[]
                )
            )
        
        result.append(
            schemas.ExamResponse(
                id=exam.id,
                courseId=exam.course_id,
                title=_display_safe_text(exam.title),
                description=_display_safe_text(exam.description) if exam.description else None,
                questions=questions_data,
                totalPoints=exam.total_points,
                dueDate=exam.due_date,
                isPublished=exam.is_published,
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
    """Create a new exam with questions and gold solutions"""
    if current_user.role != models.UserRole.PROFESSOR:
        raise HTTPException(status_code=403, detail="Only professors can create exams")
    
    # Calculate total points
    total_points = sum(q.points for q in exam_data.questions)
    
    # Create exam
    new_exam = models.Exam(
        course_id=exam_data.courseId,
        title=exam_data.title,
        description=exam_data.description,
        total_points=total_points,
        due_date=exam_data.dueDate
    )
    db.add(new_exam)
    db.flush()  # Get exam ID
    
    exam_attach_dir = UPLOAD_DIR / "exam_attachments" / new_exam.id
    exam_attach_dir.mkdir(parents=True, exist_ok=True)
    
    # Create questions and gold steps
    for question_data in exam_data.questions:
        new_question = models.Question(
            exam_id=new_exam.id,
            number=question_data.number,
            text=question_data.text,
            points=question_data.points,
            final_answer=question_data.finalAnswer,
            final_answer_latex=question_data.finalAnswerLatex,
            question_type=question_data.questionType,
            rich_content=json.dumps(question_data.richContent) if question_data.richContent else None,
            outline_level=question_data.outlineLevel,
            parent_question_id=question_data.parentQuestionId
        )
        db.add(new_question)
        db.flush()  # Get question ID
        
        # Handle attachments - move from temp location to question folder
        for att_data in question_data.attachments:
            # If attachment has an ID, it was uploaded via /api/attachments/upload
            # Move it from temp to question folder
            if att_data.filePath.startswith("/api/attachments/"):
                att_id = att_data.filePath.split("/")[-2] if "/" in att_data.filePath else None
                if att_id:
                    temp_att = db.query(models.QuestionAttachment).filter(models.QuestionAttachment.id == att_id).first()
                    if temp_att:
                        # Move file from temp to question folder
                        old_path = UPLOAD_DIR / temp_att.file_path
                        if old_path.exists():
                            safe_name = f"q{question_data.number}_{temp_att.filename}"
                            new_path = exam_attach_dir / safe_name
                            shutil.move(str(old_path), str(new_path))
                            rel_path = f"exam_attachments/{new_exam.id}/{safe_name}"
                            temp_att.question_id = new_question.id
                            temp_att.file_path = rel_path
                        else:
                            # File doesn't exist, create new attachment record
                            rel_path = f"exam_attachments/{new_exam.id}/q{question_data.number}_{att_data.filename}"
                            new_att = models.QuestionAttachment(
                                question_id=new_question.id,
                                attachment_type=att_data.attachmentType,
                                file_path=rel_path,
                                filename=att_data.filename,
                                file_size=att_data.fileSize,
                                mime_type=att_data.mimeType
                            )
                            db.add(new_att)
            else:
                # Direct file path (from upload)
                rel_path = f"exam_attachments/{new_exam.id}/q{question_data.number}_{att_data.filename}"
                new_att = models.QuestionAttachment(
                    question_id=new_question.id,
                    attachment_type=att_data.attachmentType,
                    file_path=rel_path,
                    filename=att_data.filename,
                    file_size=att_data.fileSize,
                    mime_type=att_data.mimeType
                )
                db.add(new_att)
        
        # Handle embedded content (tables, shapes, graphs from TipTap)
        if question_data.richContent:
            # Extract tables, shapes, graphs from TipTap JSON
            rich_json = question_data.richContent if isinstance(question_data.richContent, dict) else json.loads(question_data.richContent)
            embedded_items = extract_embedded_content_from_tiptap(rich_json)
            for emb_data in embedded_items:
                new_emb = models.EmbeddedContent(
                    question_id=new_question.id,
                    content_type=emb_data['contentType'],
                    content_data=json.dumps(emb_data['contentData']),
                    position_data=json.dumps(emb_data['positionData']) if emb_data.get('positionData') else None
                )
                db.add(new_emb)
        
        # Also add explicit embedded_content from request
        for emb_data in question_data.embeddedContent:
            new_emb = models.EmbeddedContent(
                question_id=new_question.id,
                content_type=emb_data.contentType,
                content_data=json.dumps(emb_data.contentData),
                position_data=json.dumps(emb_data.positionData) if emb_data.positionData else None
            )
            db.add(new_emb)
        
        # Create gold solution steps
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
        
        # Handle sub-questions recursively
        for sub_q_data in question_data.subQuestions:
            sub_question = models.Question(
                exam_id=new_exam.id,
                number=sub_q_data.number,
                text=sub_q_data.text,
                points=sub_q_data.points,
                final_answer=sub_q_data.finalAnswer,
                final_answer_latex=sub_q_data.finalAnswerLatex,
                question_type=sub_q_data.questionType,
                rich_content=json.dumps(sub_q_data.richContent) if sub_q_data.richContent else None,
                outline_level=sub_q_data.outlineLevel,
                parent_question_id=new_question.id
            )
            db.add(sub_question)
            db.flush()
            
            # Add gold steps for sub-question
            for step_data in sub_q_data.goldSolutionSteps:
                sub_step = models.GoldSolutionStep(
                    question_id=sub_question.id,
                    step_number=step_data.stepNumber,
                    description=step_data.description,
                    expression=step_data.expression,
                    latex=step_data.latex,
                    points=step_data.points,
                    required=step_data.required
                )
                db.add(sub_step)
    
    db.commit()
    db.refresh(new_exam)
    
    # Return created exam
    return get_exam(exam_id=new_exam.id, current_user=current_user, db=db)


@app.post("/api/exams/upload")
async def upload_exam(
    course_id: str = Form(...),
    file: UploadFile = File(...),
    due_date: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload an exam file (text, image, or PDF) and automatically extract questions"""
    if current_user.role != models.UserRole.PROFESSOR:
        raise HTTPException(status_code=403, detail="Only professors can upload exams")
    
    try:
        file_content = await file.read()
        file_ext = Path(file.filename).suffix.lower()

        # Diagrams/images extracted per PDF page (keyed by 0-based page number).
        # Populated AFTER text parsing so we can use parsed question data.
        pdf_embedded_images: dict = {}
        _raw_pdf_bytes: Optional[bytes] = None  # saved for diagram extraction below

        if file_ext in ['.txt']:
            text = file_content.decode('utf-8')
        elif file_ext in ['.jpg', '.jpeg', '.png', '.pdf']:
            try:
                text = ""
                ocr_result = None
                if file_ext == '.pdf':
                    _raw_pdf_bytes = file_content
                    # Prefer direct text extraction for text-based PDFs (no OCR)
                    direct_text = _extract_text_from_pdf_bytes(file_content)
                    if direct_text:
                        text = direct_text
                        logger.info("Using direct PDF text extraction (no OCR)")
                    if not text:
                        ocr_result = ocr_processor.extract_steps_from_file(file_content, file.filename or "upload")
                        text = ocr_result.combined_text
                else:
                    ocr_result = ocr_processor.extract_steps_from_file(file_content, file.filename or "upload")
                    text = ocr_result.combined_text
                    # For a standalone image upload treat the image itself as an attachment
                    try:
                        import io as _io
                        from PIL import Image as _PILImg
                        _pil = _PILImg.open(_io.BytesIO(file_content)).convert("RGB")
                        _buf = _io.BytesIO()
                        _pil.save(_buf, format="PNG")
                        pdf_embedded_images[0] = [{'data': _buf.getvalue(), 'name': 'question_image.png'}]
                    except Exception:
                        pass

                if not text and file_ext == '.pdf':
                    raise HTTPException(
                        status_code=400,
                        detail="Could not extract text from PDF. For best results install poppler (e.g. brew install poppler on macOS). You can also upload the exam as a .txt file."
                    )
            except HTTPException:
                raise
            except Exception as ocr_err:
                logger.warning(f"OCR failed for exam upload: {ocr_err}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Error processing exam file: {ocr_err}"
                )
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use .txt, .jpg, .png, or .pdf")

        parser = ExamParser()
        parsed_exam = parser.parse_exam(text)

        # Extract diagrams from PDF using pdfplumber + pdf2image now that we
        # know which questions are on which pages (and can find "Gold Solution:" positions)
        if _raw_pdf_bytes and parsed_exam.get('questions') and not pdf_embedded_images:
            try:
                pdf_embedded_images = _extract_pdf_diagrams(_raw_pdf_bytes, parsed_exam['questions'])
                logger.info(f"Diagram extraction: found images on {len(pdf_embedded_images)} page(s)")
            except Exception as _de:
                logger.warning(f"Diagram extraction failed: {_de}")

        if not parsed_exam['questions']:
            if text.strip() and file_ext in ['.jpg', '.jpeg', '.png', '.pdf']:
                parsed_exam['questions'] = [{
                    'number': 1,
                    'text': text.strip()[:10000],
                    'points': 10,
                    'page_num': 0,
                    'sub_questions': [],
                    'gold_solution_steps': [{
                        'step_number': 1,
                        'description': 'Solution',
                        'expression': '',
                        'points': 10,
                        'required': True
                    }]
                }]
                parsed_exam['total_points'] = 10
            else:
                raise HTTPException(status_code=400, detail="No questions found in the uploaded file. Please check the format.")

        new_exam = models.Exam(
            course_id=course_id,
            title=_display_safe_text(parsed_exam['title']),
            description=_display_safe_text(parsed_exam.get('description') or ''),
            total_points=parsed_exam['total_points'],
            due_date=datetime.fromisoformat(due_date) if due_date else None
        )
        db.add(new_exam)
        db.flush()

        exam_attach_dir = UPLOAD_DIR / "exam_attachments" / new_exam.id
        exam_attach_dir.mkdir(parents=True, exist_ok=True)

        for q_idx, question_data in enumerate(parsed_exam['questions']):
            new_question = models.Question(
                exam_id=new_exam.id,
                number=question_data['number'],
                text=_normalize_text_for_storage(question_data.get('text') or ''),
                points=question_data['points'],
                outline_level=1,
                parent_question_id=None,
            )
            db.add(new_question)
            db.flush()

            # Attach diagram images that belong to this question's page
            q_page_num = question_data.get('page_num', q_idx)
            if q_page_num in pdf_embedded_images:
                import io as _io
                from PIL import Image as _PILImg
                for img_idx, img_info in enumerate(pdf_embedded_images[q_page_num]):
                    try:
                        raw_data = img_info['data']
                        # Normalise to PNG via PIL so we always serve a valid image
                        pil_img = _PILImg.open(_io.BytesIO(raw_data)).convert("RGB")
                        out_buf = _io.BytesIO()
                        pil_img.save(out_buf, format="PNG")
                        png_bytes = out_buf.getvalue()

                        safe_name = f"q{question_data['number']}_diagram{img_idx + 1}.png"
                        out_path = exam_attach_dir / safe_name
                        with open(out_path, "wb") as _f:
                            _f.write(png_bytes)
                        rel_path = f"exam_attachments/{new_exam.id}/{safe_name}"
                        att = models.QuestionAttachment(
                            question_id=new_question.id,
                            attachment_type="image",
                            file_path=rel_path,
                            filename=safe_name,
                            mime_type="image/png",
                        )
                        db.add(att)
                    except Exception as _e:
                        logger.warning(f"Could not save diagram for Q{question_data['number']}: {_e}")

            for step_data in question_data['gold_solution_steps']:
                new_step = models.GoldSolutionStep(
                    question_id=new_question.id,
                    step_number=step_data['step_number'],
                    description=step_data['description'],
                    expression=step_data['expression'],
                    points=step_data['points'],
                    required=step_data['required']
                )
                db.add(new_step)

            # Create sub-questions (a), (b), (c) if parsed
            for sub_idx, sub_data in enumerate(question_data.get('sub_questions') or [], start=1):
                sub_q = models.Question(
                    exam_id=new_exam.id,
                    number=sub_idx,
                    text=_normalize_text_for_storage(sub_data.get('text') or ''),
                    points=sub_data.get('points', 1),
                    outline_level=2,
                    parent_question_id=new_question.id,
                )
                db.add(sub_q)
                db.flush()
                for step_data in sub_data.get('gold_solution_steps') or []:
                    new_step = models.GoldSolutionStep(
                        question_id=sub_q.id,
                        step_number=step_data['step_number'],
                        description=step_data['description'],
                        expression=step_data['expression'],
                        points=step_data['points'],
                        required=step_data['required'],
                    )
                    db.add(new_step)

        db.commit()
        db.refresh(new_exam)

        return {
            "message": "Exam uploaded and parsed successfully",
            "exam_id": new_exam.id,
            "title": new_exam.title,
            "questions_found": len(parsed_exam['questions']),
            "total_points": parsed_exam['total_points']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading exam: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing exam file: {str(e)}")


security_optional = HTTPBearer(auto_error=False)


@app.post("/api/attachments/upload")
async def upload_attachment(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload an attachment file (image, etc.) and return attachment info. Can be linked to questions later."""
    if current_user.role != models.UserRole.PROFESSOR:
        raise HTTPException(status_code=403, detail="Only professors can upload attachments")
    
    try:
        file_content = await file.read()
        file_ext = Path(file.filename or "file").suffix.lower()
        
        # Determine attachment type and mime type
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
            attachment_type = "image"
            mime_type = f"image/{file_ext[1:]}" if file_ext != '.jpg' else "image/jpeg"
        elif file_ext == '.pdf':
            attachment_type = "document"
            mime_type = "application/pdf"
        else:
            attachment_type = "document"
            mime_type = "application/octet-stream"
        
        # Save file to temporary location (will be moved when question is created)
        temp_dir = UPLOAD_DIR / "temp_attachments"
        temp_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = f"{current_user.id}_{datetime.utcnow().timestamp()}_{file.filename or 'file'}"
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._-")
        temp_path = temp_dir / safe_filename
        
        with open(temp_path, "wb") as f:
            f.write(file_content)
        
        rel_path = f"temp_attachments/{safe_filename}"
        
        # Create attachment record (question_id will be set later)
        new_attachment = models.QuestionAttachment(
            question_id="",  # Will be set when question is created
            attachment_type=attachment_type,
            file_path=rel_path,
            filename=file.filename or "file",
            file_size=len(file_content),
            mime_type=mime_type,
        )
        db.add(new_attachment)
        db.flush()
        db.refresh(new_attachment)
        
        return schemas.AttachmentResponse(
            id=new_attachment.id,
            attachmentType=new_attachment.attachment_type,
            filePath=f"/api/attachments/{new_attachment.id}/file",
            filename=new_attachment.filename,
            mimeType=new_attachment.mime_type,
        )
    except Exception as e:
        logger.error(f"Error uploading attachment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload attachment: {str(e)}")


@app.get("/api/attachments/{attachment_id}/file")
def serve_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
):
    """Serve a question attachment file (image, etc.). Public for published exam attachments."""
    att = db.query(models.QuestionAttachment).filter(models.QuestionAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    allowed = False
    if credentials:
        try:
            get_current_user(credentials, db)
            allowed = True
        except Exception:
            pass
    if not allowed:
        # For temp attachments (no question_id), allow if user uploaded it
        if not att.question_id:
            raise HTTPException(status_code=403, detail="Access denied")
        question = db.query(models.Question).filter(models.Question.id == att.question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="Not found")
        exam = db.query(models.Exam).filter(models.Exam.id == question.exam_id).first()
        if not exam or not exam.is_published:
            raise HTTPException(status_code=403, detail="Access denied")
    path = UPLOAD_DIR / att.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type=att.mime_type or "application/octet-stream", filename=att.filename)


@app.get("/api/exams/{exam_id}", response_model=schemas.ExamResponse)
def get_exam(
    exam_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific exam by ID"""
    exam = db.query(models.Exam).options(
        selectinload(models.Exam.questions).options(
            selectinload(models.Question.gold_steps),
            selectinload(models.Question.attachments),
            selectinload(models.Question.embedded_content),
        )
    ).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Build question tree: only top-level questions in list, with subQuestions nested
    all_questions = list(exam.questions)
    top_level = [q for q in all_questions if not getattr(q, 'parent_question_id', None)]
    children_by_parent = {}
    for q in all_questions:
        pid = getattr(q, 'parent_question_id', None)
        if pid:
            children_by_parent.setdefault(pid, []).append(q)

    def _question_to_response(question, sub_responses=None):
        gold_steps = [
            schemas.GoldSolutionStepResponse(
                stepNumber=step.step_number,
                description=step.description or "",
                expression=step.expression,
                latex=step.latex or "",
                points=step.points,
                required=getattr(step, 'required', True)
            )
            for step in question.gold_steps
        ]
        attachments_data = [
            schemas.AttachmentResponse(
                id=a.id,
                attachmentType=a.attachment_type,
                filePath=f"/api/attachments/{a.id}/file",
                filename=a.filename,
                mimeType=a.mime_type,
            )
            for a in question.attachments
        ]
        embedded_data = []
        for ec in question.embedded_content:
            try:
                content_data = json.loads(ec.content_data) if isinstance(ec.content_data, str) else (ec.content_data or {})
                position_data = json.loads(ec.position_data) if isinstance(ec.position_data, str) and ec.position_data else None
            except Exception:
                content_data = {}
                position_data = None
            embedded_data.append(
                schemas.EmbeddedContentResponse(
                    id=ec.id,
                    contentType=ec.content_type,
                    contentData=content_data,
                    positionData=position_data,
                )
            )
        display_text = _display_safe_text(question.text)
        rich_content_val = json.loads(question.rich_content) if question.rich_content and isinstance(question.rich_content, str) else (question.rich_content if question.rich_content else None)
        if display_text.startswith("[Question text could not be displayed") and rich_content_val:
            rich_content_val = {
                "type": "doc",
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Question text could not be displayed. Re-upload the exam as PDF or .txt to restore content, or edit manually."}]
                }]
            }
        return schemas.QuestionResponse(
            id=question.id,
            number=question.number,
            text=display_text,
            points=question.points,
            goldSolution=schemas.GoldSolutionResponse(
                steps=gold_steps,
                finalAnswer=question.final_answer or "",
                finalAnswerLatex=question.final_answer_latex or ""
            ),
            goldSolutionSteps=gold_steps,
            finalAnswer=question.final_answer or "",
            finalAnswerLatex=question.final_answer_latex or "",
            questionType=getattr(question, 'question_type', 'standard'),
            richContent=rich_content_val,
            outlineLevel=getattr(question, 'outline_level', 1),
            parentQuestionId=getattr(question, 'parent_question_id', None),
            subQuestions=sub_responses or [],
            attachments=attachments_data,
            embeddedContent=embedded_data,
            theories=[]
        )

    questions_data = []
    for question in sorted(top_level, key=lambda q: q.number):
        children = sorted(children_by_parent.get(question.id, []), key=lambda q: q.number)
        sub_responses = [_question_to_response(c) for c in children]
        questions_data.append(_question_to_response(question, sub_responses))
    
    return schemas.ExamResponse(
        id=exam.id,
        courseId=exam.course_id,
        title=_display_safe_text(exam.title),
        description=_display_safe_text(exam.description) if exam.description else None,
        questions=questions_data,
        totalPoints=exam.total_points,
        dueDate=exam.due_date,
        isPublished=exam.is_published,
        publishedAt=exam.published_at,
        createdAt=exam.created_at
    )


@app.delete("/api/exams/{exam_id}")
def delete_exam(
    exam_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an exam (professor only). Removes exam, questions, and submissions for that exam."""
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if current_user.role != models.UserRole.PROFESSOR:
        raise HTTPException(status_code=403, detail="Only professors can delete exams")
    # Delete submissions first (they reference exam_id)
    db.query(models.Submission).filter(models.Submission.exam_id == exam_id).delete()
    db.delete(exam)
    db.commit()
    # Remove attachment folder if present
    exam_attach_dir = UPLOAD_DIR / "exam_attachments" / exam_id
    if exam_attach_dir.exists():
        try:
            shutil.rmtree(exam_attach_dir)
        except OSError as e:
            logger.warning(f"Could not remove exam attachment dir {exam_attach_dir}: {e}")
    return {"deleted": True}


@app.put("/api/exams/{exam_id}", response_model=schemas.ExamResponse)
def update_exam(
    exam_id: str,
    exam_data: schemas.ExamCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing exam"""
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Check authorization
    if current_user.role != models.UserRole.PROFESSOR:
        raise HTTPException(status_code=403, detail="Only professors can update exams")
    
    # Update exam basic info
    exam.course_id = exam_data.courseId
    exam.title = exam_data.title
    exam.description = exam_data.description
    exam.due_date = exam_data.dueDate
    
    # Calculate total points
    total_points = sum(q.points for q in exam_data.questions)
    exam.total_points = total_points
    
    # Delete existing questions (cascade will delete gold steps, attachments, embedded_content)
    for question in exam.questions:
        db.delete(question)
    db.flush()
    
    exam_attach_dir = UPLOAD_DIR / "exam_attachments" / exam.id
    exam_attach_dir.mkdir(parents=True, exist_ok=True)
    
    # Create new questions and gold steps
    for question_data in exam_data.questions:
        new_question = models.Question(
            exam_id=exam.id,
            number=question_data.number,
            text=question_data.text,
            points=question_data.points,
            final_answer=question_data.finalAnswer,
            final_answer_latex=question_data.finalAnswerLatex,
            question_type=question_data.questionType,
            rich_content=json.dumps(question_data.richContent) if question_data.richContent else None,
            outline_level=question_data.outlineLevel,
            parent_question_id=question_data.parentQuestionId
        )
        db.add(new_question)
        db.flush()
        
        # Handle attachments - move from temp location to question folder
        for att_data in question_data.attachments:
            if att_data.filePath.startswith("/api/attachments/"):
                att_id = att_data.filePath.split("/")[-2] if "/" in att_data.filePath else None
                if att_id:
                    temp_att = db.query(models.QuestionAttachment).filter(models.QuestionAttachment.id == att_id).first()
                    if temp_att:
                        old_path = UPLOAD_DIR / temp_att.file_path
                        if old_path.exists():
                            safe_name = f"q{question_data.number}_{temp_att.filename}"
                            new_path = exam_attach_dir / safe_name
                            shutil.move(str(old_path), str(new_path))
                            rel_path = f"exam_attachments/{exam.id}/{safe_name}"
                            temp_att.question_id = new_question.id
                            temp_att.file_path = rel_path
                        else:
                            rel_path = f"exam_attachments/{exam.id}/q{question_data.number}_{att_data.filename}"
                            new_att = models.QuestionAttachment(
                                question_id=new_question.id,
                                attachment_type=att_data.attachmentType,
                                file_path=rel_path,
                                filename=att_data.filename,
                                file_size=att_data.fileSize,
                                mime_type=att_data.mimeType
                            )
                            db.add(new_att)
            else:
                rel_path = f"exam_attachments/{exam.id}/q{question_data.number}_{att_data.filename}"
                new_att = models.QuestionAttachment(
                    question_id=new_question.id,
                    attachment_type=att_data.attachmentType,
                    file_path=rel_path,
                    filename=att_data.filename,
                    file_size=att_data.fileSize,
                    mime_type=att_data.mimeType
                )
                db.add(new_att)
        
        # Handle embedded content (tables, shapes, graphs from TipTap)
        if question_data.richContent:
            rich_json = question_data.richContent if isinstance(question_data.richContent, dict) else json.loads(question_data.richContent)
            embedded_items = extract_embedded_content_from_tiptap(rich_json)
            for emb_data in embedded_items:
                new_emb = models.EmbeddedContent(
                    question_id=new_question.id,
                    content_type=emb_data['contentType'],
                    content_data=json.dumps(emb_data['contentData']),
                    position_data=json.dumps(emb_data['positionData']) if emb_data.get('positionData') else None
                )
                db.add(new_emb)
        
        # Also add explicit embedded_content from request
        for emb_data in question_data.embeddedContent:
            new_emb = models.EmbeddedContent(
                question_id=new_question.id,
                content_type=emb_data.contentType,
                content_data=json.dumps(emb_data.contentData),
                position_data=json.dumps(emb_data.positionData) if emb_data.positionData else None
            )
            db.add(new_emb)
        
        # Create gold solution steps
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
        
        # Handle sub-questions
        for sub_q_data in question_data.subQuestions:
            sub_question = models.Question(
                exam_id=exam.id,
                number=sub_q_data.number,
                text=sub_q_data.text,
                points=sub_q_data.points,
                final_answer=sub_q_data.finalAnswer,
                final_answer_latex=sub_q_data.finalAnswerLatex,
                question_type=sub_q_data.questionType,
                rich_content=json.dumps(sub_q_data.richContent) if sub_q_data.richContent else None,
                outline_level=sub_q_data.outlineLevel,
                parent_question_id=new_question.id
            )
            db.add(sub_question)
            db.flush()
            
            for step_data in sub_q_data.goldSolutionSteps:
                sub_step = models.GoldSolutionStep(
                    question_id=sub_question.id,
                    step_number=step_data.stepNumber,
                    description=step_data.description,
                    expression=step_data.expression,
                    latex=step_data.latex,
                    points=step_data.points,
                    required=step_data.required
                )
                db.add(sub_step)
    
    db.commit()
    db.refresh(exam)
    
    # Return updated exam
    return get_exam(exam_id=exam_id, current_user=current_user, db=db)


@app.post("/api/exams/{exam_id}/publish")
def publish_exam(
    exam_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Publish an exam to make it available to students"""
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Check authorization - only professor who owns the course can publish
    course = db.query(models.Course).filter(models.Course.id == exam.course_id).first()
    if current_user.role != models.UserRole.PROFESSOR or course.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the course professor can publish exams")
    
    exam.is_published = True
    exam.published_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Exam published successfully", "exam_id": exam_id}


@app.post("/api/exams/{exam_id}/unpublish")
def unpublish_exam(
    exam_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unpublish an exam to hide it from students"""
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Check authorization
    course = db.query(models.Course).filter(models.Course.id == exam.course_id).first()
    if current_user.role != models.UserRole.PROFESSOR or course.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the course professor can unpublish exams")
    
    exam.is_published = False
    db.commit()
    
    return {"message": "Exam unpublished successfully", "exam_id": exam_id}


# ============================================================================
# Submission Endpoints (Next part will continue...)
# ============================================================================



def extract_embedded_content_from_tiptap(tiptap_json: dict) -> List[dict]:
    """Extract tables, shapes, graphs from TipTap JSON and convert to EmbeddedContent format."""
    embedded_items = []
    
    def traverse(node: dict):
        if not isinstance(node, dict):
            return
        
        node_type = node.get('type', '')
        
        # Extract tables
        if node_type == 'table':
            rows = []
            for child in node.get('content', []):
                if child.get('type') == 'tableRow':
                    row = []
                    for cell in child.get('content', []):
                        cell_text = ''
                        if cell.get('type') == 'tableCell' or cell.get('type') == 'tableHeader':
                            for para in cell.get('content', []):
                                if para.get('type') == 'paragraph':
                                    for text_node in para.get('content', []):
                                        if text_node.get('type') == 'text':
                                            cell_text += text_node.get('text', '')
                        row.append(cell_text)
                    if row:
                        rows.append(row)
            
            if rows:
                embedded_items.append({
                    'contentType': 'table',
                    'contentData': {'rows': rows},
                    'positionData': None
                })
        
        # Extract images (shapes/graphs embedded as SVG data URLs)
        elif node_type == 'image':
            src = node.get('attrs', {}).get('src', '')
            if src.startswith('data:image/svg+xml'):
                # This is a shape
                embedded_items.append({
                    'contentType': 'shape',
                    'contentData': {'src': src, 'alt': node.get('attrs', {}).get('alt', '')},
                    'positionData': None
                })
        
        # Recursively traverse children
        if 'content' in node:
            for child in node['content']:
                traverse(child)
    
    if isinstance(tiptap_json, dict):
        if 'content' in tiptap_json:
            for child in tiptap_json['content']:
                traverse(child)
        else:
            traverse(tiptap_json)
    
    return embedded_items


def extract_math_from_html(html_content: str) -> Tuple[str, Optional[str]]:
    """
    Extract mathematical content from HTML.
    Returns (text_content, latex_content)
    """
    from html import unescape
    import re
    
    if not html_content or not html_content.strip():
        return '', None
    
    # Extract LaTeX from math nodes (if present)
    latex_content = None
    latex_patterns = [
        r'<span[^>]*data-type="math"[^>]*>(.*?)</span>',
        r'<span[^>]*class="[^"]*math[^"]*"[^>]*>(.*?)</span>',
        r'\$\$(.*?)\$\$',
        r'\$(.*?)\$',
        r'\\\[(.*?)\\\]',
        r'\\\((.*?)\\\)',
    ]
    
    all_latex = []
    for pattern in latex_patterns:
        matches = re.findall(pattern, html_content, re.DOTALL)
        if matches:
            all_latex.extend(matches)
    
    if all_latex:
        # Join all LaTeX expressions, separated by spaces
        latex_content = ' '.join([m.strip() for m in all_latex if m.strip()])
    
    # Extract plain text content (strip HTML tags)
    text_content = re.sub(r'<[^>]+>', '', html_content)
    text_content = unescape(text_content).strip()
    
    # Remove placeholder text
    if text_content.lower() in ['type your answer here...', '']:
        text_content = ''
    
    # If we have LaTeX but no text, use LaTeX as text (it will be parsed)
    if not text_content and latex_content:
        text_content = latex_content
    
    return text_content, latex_content


def parse_answer_into_steps(answer_text: str) -> List[str]:
    """
    Parse a student's answer into individual steps.
    Enhanced to detect steps from single-line typed answers.
    """
    if not answer_text or not answer_text.strip():
        return []
    
    text = answer_text.strip()
    
    # Split by newlines first
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Single line - try multiple strategies
    if len(lines) <= 1:
        single_line = text
        
        # Strategy 1: Split by = signs (math equations)
        if '=' in single_line:
            parts = re.split(r'(?<![<>=!])=(?!=)', single_line)
            if len(parts) > 1:
                steps = []
                if parts[0].strip():
                    steps.append(parts[0].strip())
                for i in range(1, len(parts)):
                    step = '=' + parts[i].strip()
                    if step.strip() != '=':
                        steps.append(step)
                if steps:
                    return steps
        
        # Strategy 2: Split by semicolons (common separator)
        if ';' in single_line:
            parts = [p.strip() for p in single_line.split(';') if p.strip()]
            if len(parts) > 1:
                return parts
        
        # Strategy 3: Split by "then" or "and" (natural language)
        if re.search(r'\s+(then|and|next|after|followed by)\s+', single_line, re.IGNORECASE):
            parts = re.split(r'\s+(?:then|and|next|after|followed by)\s+', single_line, flags=re.IGNORECASE)
            if len(parts) > 1:
                return [p.strip() for p in parts if p.strip()]
        
        # Strategy 4: Split by numbered patterns (1), 2), etc.
        numbered = re.split(r'\s+\(?\d+\)\s+', single_line)
        if len(numbered) > 1:
            return [p.strip() for p in numbered if p.strip()]
        
        return [single_line] if single_line else []
    
    # Multiple lines - enhanced detection
    steps = []
    current_step = []
    
    for line in lines:
        # Check if line starts a new step
        is_new_step = False
        
        # Pattern 1: Step markers
        if re.match(r'^(step\s*\d+|step|solution|answer|\(?\d+[\.\)])\s*:?\s*', line, re.IGNORECASE):
            is_new_step = True
        # Pattern 2: Starts with =
        elif line.startswith('='):
            is_new_step = True
        # Pattern 3: Starts with number followed by punctuation
        elif re.match(r'^\d+[\.\)]\s+', line):
            is_new_step = True
        # Pattern 4: Empty line (double newline)
        elif not line.strip() and current_step:
            is_new_step = True
        
        if is_new_step and current_step:
            step_text = ' '.join(current_step).strip()
            if step_text:
                steps.append(step_text)
            current_step = [line] if line.strip() else []
        else:
            if line.strip():
                current_step.append(line)
    
    # Add last step
    if current_step:
        step_text = ' '.join(current_step).strip()
        if step_text:
            steps.append(step_text)
    
    # Fallback: split by double newlines
    if len(steps) <= 1:
        double_newline_split = [s.strip() for s in text.split('\n\n') if s.strip()]
        if len(double_newline_split) > 1:
            steps = double_newline_split
        else:
            steps = [text.strip()]
    
    return steps if steps else [text.strip()]


async def grade_submission_automatically(submission_id: str, db: Session):
    """Automatically grade a submission after it's submitted"""
    import json
    import re
    from html import unescape
    
    submission = db.query(models.Submission).filter(
        models.Submission.id == submission_id
    ).first()
    if not submission:
        return
    
    submission.status = models.SubmissionStatus.GRADING
    db.commit()
    
    exam = db.query(models.Exam).filter(models.Exam.id == submission.exam_id).first()
    questions = exam.questions
    
    total_score = 0.0
    
    has_typed_answers = submission.typed_answers is not None and submission.typed_answers.strip()
    has_images = len(submission.images) > 0
    
    if not has_typed_answers and not has_images:
        submission.status = models.SubmissionStatus.PENDING
        db.commit()
        return
    
    # Process typed answers with proper mathematical evaluation
    if has_typed_answers:
        try:
            typed_answers_data = json.loads(submission.typed_answers)
            
            for answer_data in typed_answers_data:
                question_id = answer_data.get('questionId')
                question_number = answer_data.get('questionNumber')
                typed_answer = answer_data.get('typedAnswer', '')
                
                if not typed_answer or typed_answer.strip() == '':
                    continue
                
                # Find the corresponding question
                question = next(
                    (q for q in questions if q.id == question_id or (question_number and q.number == question_number)), 
                    None
                )
                if not question:
                    continue
                
                # Extract math content from HTML
                text_content, latex_content = extract_math_from_html(typed_answer)
                
                if not text_content and not latex_content:
                    continue
                
                # Use LaTeX if available, otherwise use text
                answer_to_grade = latex_content if latex_content else text_content
                
                # Parse answer into steps
                student_steps = parse_answer_into_steps(answer_to_grade)
                
                if not student_steps:
                    continue
                
                # Get gold solution steps
                gold_steps = []
                for step in question.gold_steps:
                    # Prefer latex if available, otherwise use expression
                    content = step.latex if step.latex and step.latex.strip() else (step.expression if step.expression else '')
                    if content.strip():  # Only add non-empty steps
                        gold_steps.append(GraderStep(
                            content=content.strip(),
                            points=float(step.points),
                            required=step.required
                        ))
                
                if not gold_steps:
                    # No gold steps defined, skip grading
                    print(f"Warning: Question {question.id} has no valid gold steps")
                    continue
                
                # Debug logging
                print(f"Grading question {question.id}:")
                print(f"  Gold steps ({len(gold_steps)}): {[gs.content for gs in gold_steps]}")
                print(f"  Student steps ({len(student_steps)}): {student_steps}")
                
                grader = HybridGrader(gold_steps, use_ml=True, use_symbolic=True)
                grading_result = grader.grade(student_steps)
                
                print(f"  Grading result: {grading_result['total_score']}/{grading_result['max_score']} ({grading_result['percentage']:.1f}%)")
                # Print evaluation details
                for idx, eval_obj in enumerate(grading_result['evaluations']):
                    print(f"    Step {idx+1}: {eval_obj.status.value}, {eval_obj.points_earned} pts - {eval_obj.feedback}")
                
                # Store grading result
                db_grading_result = models.GradingResult(
                    submission_id=submission.id,
                    question_id=question.id,
                    extracted_text=text_content,
                    extracted_latex=latex_content,
                    score=grading_result['total_score'],
                    max_score=grading_result['max_score'],
                    feedback=f"Auto-graded: {grading_result['percentage']:.1f}%",
                    is_correct=grading_result['percentage'] >= 70
                )
                db.add(db_grading_result)
                db.flush()
                
                # Store step results
                for idx, (student_step, evaluation) in enumerate(
                    zip(student_steps, grading_result['evaluations']), start=1
                ):
                    matched_gold = None
                    if evaluation.matched_gold_step is not None:
                        matched_gold_step_obj = gold_steps[evaluation.matched_gold_step]
                        matched_gold = matched_gold_step_obj.content
                    
                    step_result = models.StepResult(
                        grading_result_id=db_grading_result.id,
                        step_number=idx,
                        student_text=student_step,
                        is_correct=evaluation.status.value == "Correct",
                        score=evaluation.points_earned,
                        max_score=gold_steps[evaluation.matched_gold_step].points if evaluation.matched_gold_step is not None else 0,
                        feedback=evaluation.feedback,
                        expected=matched_gold,
                        received=student_step
                    )
                    db.add(step_result)
                
                total_score += grading_result['total_score']
                
        except Exception as e:
            print(f"Error grading typed answers: {e}")
            import traceback
            traceback.print_exc()
    
    # Process images with OCR and MathGrader
    if has_images:
        for image_record in submission.images:
            try:
                image_path = Path(image_record.image_path)
                if not image_path.exists():
                    continue
                
                # Run OCR to extract steps
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                
                ocr_result = ocr_processor.extract_steps_from_file(
                    image_bytes,
                    image_path.name
                )
                
                student_steps = ocr_result.steps
                
                if not student_steps:
                    continue
                
                # Determine which question this image corresponds to
                # Assuming one question per image based on page number
                question = None
                if image_record.page_number <= len(questions):
                    question = questions[image_record.page_number - 1]
                else:
                    # Try to find question by matching content or use first question
                    question = questions[0] if questions else None
                
                if not question:
                    continue
                
                # Get gold solution steps
                gold_steps = [
                    GraderStep(
                        content=step.expression or step.latex or '',
                        points=float(step.points),
                        required=step.required
                    )
                    for step in question.gold_steps
                ]
                
                if not gold_steps:
                    continue
                
                grader = HybridGrader(gold_steps, use_ml=True, use_symbolic=True)
                grading_result = grader.grade(student_steps)
                
                # Store grading result
                db_grading_result = models.GradingResult(
                    submission_id=submission.id,
                    question_id=question.id,
                    extracted_text="\n".join(student_steps),
                    extracted_latex=None,
                    score=grading_result['total_score'],
                    max_score=grading_result['max_score'],
                    feedback=f"Auto-graded (OCR): {grading_result['percentage']:.1f}%",
                    is_correct=grading_result['percentage'] >= 70
                )
                db.add(db_grading_result)
                db.flush()
                
                # Store step results
                for idx, (student_step, evaluation) in enumerate(
                    zip(student_steps, grading_result['evaluations']), start=1
                ):
                    matched_gold = None
                    if evaluation.matched_gold_step is not None:
                        matched_gold_step_obj = gold_steps[evaluation.matched_gold_step]
                        matched_gold = matched_gold_step_obj.content
                    
                    step_result = models.StepResult(
                        grading_result_id=db_grading_result.id,
                        step_number=idx,
                        student_text=student_step,
                        is_correct=evaluation.status.value == "Correct",
                        score=evaluation.points_earned,
                        max_score=gold_steps[evaluation.matched_gold_step].points if evaluation.matched_gold_step is not None else 0,
                        feedback=evaluation.feedback,
                        expected=matched_gold,
                        received=student_step
                    )
                    db.add(step_result)
                
                total_score += grading_result['total_score']
                
            except Exception as e:
                print(f"Error grading image: {e}")
                import traceback
                traceback.print_exc()
    
    submission.total_score = total_score
    submission.graded_at = datetime.utcnow()
    submission.status = models.SubmissionStatus.AWAITING_APPROVAL
    db.commit()


@app.post("/api/submissions")
async def submit_exam(
    exam_id: str = Form(...),
    images: List[UploadFile] = File(default=[]),
    answers: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit an exam with optional image uploads and/or typed answers"""
    # Verify exam exists
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Validate that at least one submission method is provided
    if not images and not answers:
        raise HTTPException(status_code=400, detail="At least one submission method (images or typed answers) is required")
    
    # Create submission
    new_submission = models.Submission(
        exam_id=exam_id,
        student_id=current_user.id,
        status=models.SubmissionStatus.PENDING,
        max_score=exam.total_points,
        typed_answers=answers  # Store JSON string of typed answers
    )
    db.add(new_submission)
    db.flush()
    
    # Save uploaded images if provided
    if images:
        submission_dir = UPLOAD_DIR / new_submission.id
        submission_dir.mkdir(exist_ok=True)
        
        for idx, image_file in enumerate(images, start=1):
            # Save image
            file_ext = Path(image_file.filename).suffix
            image_path = submission_dir / f"page_{idx}{file_ext}"
            
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            
            # Create image record
            submission_image = models.SubmissionImage(
                submission_id=new_submission.id,
                image_path=str(image_path),
                page_number=idx
            )
            db.add(submission_image)
    
    db.commit()
    db.refresh(new_submission)
    
    # Automatically trigger AI grading
    try:
        await grade_submission_automatically(new_submission.id, db)
    except Exception as e:
        print(f"Auto-grading failed: {e}")
        # Don't fail the submission if auto-grading fails
    
    return {
        "id": new_submission.id,
        "status": "success",
        "message": "Submission created successfully. AI grading in progress."
    }


@app.get("/api/submissions", response_model=List[schemas.SubmissionResponse])
def get_submissions(
    exam_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all submissions"""
    query = db.query(models.Submission)
    
    # Filter based on user role
    if current_user.role == models.UserRole.STUDENT:
        # Students only see their own submissions
        query = query.filter(models.Submission.student_id == current_user.id)
    elif current_user.role == models.UserRole.PROFESSOR:
        # Professors see submissions from exams in their courses
        # Join with Exam and Course to filter by professor_id
        query = query.join(models.Exam).join(models.Course).filter(
            models.Course.professor_id == current_user.id
        )
    # Admins see all submissions (no filter)
    
    if exam_id:
        query = query.filter(models.Submission.exam_id == exam_id)
    
    if status:
        query = query.filter(models.Submission.status == status)
    
    submissions = query.order_by(models.Submission.submitted_at.desc()).all()
    
    result = []
    import json
    
    for submission in submissions:
        # Get student info
        student = db.query(models.User).filter(models.User.id == submission.student_id).first()
        
        # Get exam to access questions
        exam = db.query(models.Exam).filter(models.Exam.id == submission.exam_id).first()
        questions_by_id = {q.id: q for q in exam.questions} if exam else {}
        
        # Build answers
        answers = []
        graded_question_ids = set()
        
        # First, add answers from grading results (if any)
        for grading_result in submission.grading_results:
            graded_question_ids.add(grading_result.question_id)
            step_results = [
                schemas.StepResultResponse(
                    id=step.id,
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
            
            question = questions_by_id.get(grading_result.question_id)
            
            answers.append(
                schemas.SubmittedAnswerResponse(
                    questionId=grading_result.question_id,
                    questionNumber=question.number if question else 0,
                    extractedText=grading_result.extracted_text,
                    extractedLatex=grading_result.extracted_latex,
                    extractedSteps=[],
                    gradingResult=schemas.GradingResultResponse(
                        id=grading_result.id,
                        score=grading_result.score,
                        maxScore=grading_result.max_score,
                        feedback=grading_result.feedback or "",
                        stepResults=step_results,
                        isCorrect=grading_result.is_correct
                    ) if submission.status in [models.SubmissionStatus.GRADED, models.SubmissionStatus.APPROVED, models.SubmissionStatus.AWAITING_APPROVAL] else None
                )
            )
        
        # Also include typed answers from submission (for pending/grading submissions)
        if submission.typed_answers:
            try:
                typed_answers_data = json.loads(submission.typed_answers)
                for answer_data in typed_answers_data:
                    question_id = answer_data.get('questionId')
                    question_number = answer_data.get('questionNumber')
                    typed_answer = answer_data.get('typedAnswer', '')
                    
                    # Skip if already added from grading results
                    if question_id in graded_question_ids:
                        continue
                    
                    question = questions_by_id.get(question_id)
                    if not question and question_number:
                        # Try to find by number
                        question = next((q for q in questions_by_id.values() if q.number == question_number), None)
                    
                    if question:
                        # Extract text from HTML
                        from html import unescape
                        import re
                        text_content = re.sub(r'<[^>]+>', '', typed_answer)
                        text_content = unescape(text_content).strip()
                        
                        answers.append(
                            schemas.SubmittedAnswerResponse(
                                questionId=question_id or question.id,
                                questionNumber=question_number or question.number,
                                extractedText=text_content,
                                extractedLatex=None,
                                extractedSteps=[],
                                gradingResult=None
                            )
                        )
            except:
                pass
        
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
    """Get a specific submission by ID"""
    submission = db.query(models.Submission).filter(
        models.Submission.id == submission_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Check permissions
    if current_user.role == models.UserRole.STUDENT and submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get student info
    student = db.query(models.User).filter(models.User.id == submission.student_id).first()
    
    # Build answers
    answers = []
    import json
    
    # Get exam to access questions
    exam = db.query(models.Exam).filter(models.Exam.id == submission.exam_id).first()
    questions_by_id = {q.id: q for q in exam.questions} if exam else {}
    
    # First, add answers from grading results (if any)
    graded_question_ids = set()
    for grading_result in submission.grading_results:
        graded_question_ids.add(grading_result.question_id)
        step_results = [
            schemas.StepResultResponse(
                id=step.id,
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
        
        question = questions_by_id.get(grading_result.question_id)
        
        answers.append(
            schemas.SubmittedAnswerResponse(
                questionId=grading_result.question_id,
                questionNumber=question.number if question else 0,
                extractedText=grading_result.extracted_text,
                extractedLatex=grading_result.extracted_latex,
                extractedSteps=[],
                gradingResult=schemas.GradingResultResponse(
                    id=grading_result.id,
                    score=grading_result.score,
                    maxScore=grading_result.max_score,
                    feedback=grading_result.feedback or "",
                    stepResults=step_results,
                    isCorrect=grading_result.is_correct
                ) if submission.status in [models.SubmissionStatus.GRADED, models.SubmissionStatus.APPROVED, models.SubmissionStatus.AWAITING_APPROVAL] else None
            )
        )
    
    # Also include typed answers from submission (for pending/grading submissions)
    if submission.typed_answers:
        try:
            typed_answers_data = json.loads(submission.typed_answers)
            for answer_data in typed_answers_data:
                question_id = answer_data.get('questionId')
                question_number = answer_data.get('questionNumber')
                typed_answer = answer_data.get('typedAnswer', '')
                
                # Skip if already added from grading results
                if question_id in graded_question_ids:
                    continue
                
                question = questions_by_id.get(question_id)
                if not question and question_number:
                    # Try to find by number
                    question = next((q for q in questions_by_id.values() if q.number == question_number), None)
                
                if question:
                    # Extract text from HTML
                    from html import unescape
                    import re
                    text_content = re.sub(r'<[^>]+>', '', typed_answer)
                    text_content = unescape(text_content).strip()
                    
                    answers.append(
                        schemas.SubmittedAnswerResponse(
                            questionId=question_id or question.id,
                            questionNumber=question_number or question.number,
                            extractedText=text_content,
                            extractedLatex=None,
                            extractedSteps=[],
                            gradingResult=None
                        )
                    )
        except:
            pass
    
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
    """Grade a submission using typed answers or OCR and the math grader"""
    import json
    
    if current_user.role not in [models.UserRole.PROFESSOR, models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only professors can grade submissions")
    
    # Get submission
    submission = db.query(models.Submission).filter(
        models.Submission.id == submission_id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Update status
    submission.status = models.SubmissionStatus.GRADING
    db.commit()
    
    # Get exam and questions
    exam = db.query(models.Exam).filter(models.Exam.id == submission.exam_id).first()
    questions = exam.questions
    
    total_score = 0.0
    
    # Check if there are typed answers
    has_typed_answers = submission.typed_answers is not None and submission.typed_answers.strip()
    has_images = len(submission.images) > 0
    
    if not has_typed_answers and not has_images:
        raise HTTPException(status_code=400, detail="No answers found for submission (neither typed nor images)")
    
    # Process typed answers if available
    if has_typed_answers:
        try:
            typed_answers_data = json.loads(submission.typed_answers)
            
            for answer_data in typed_answers_data:
                question_id = answer_data.get('questionId')
                question_number = answer_data.get('questionNumber')
                typed_answer = answer_data.get('typedAnswer', '')
                
                # Find the corresponding question
                question = next(
                    (q for q in questions if q.id == question_id or (question_number and q.number == question_number)), 
                    None
                )
                
                if not question:
                    continue
                
                # Extract math content from HTML
                text_content, latex_content = extract_math_from_html(typed_answer)
                
                if not text_content and not latex_content:
                    continue
                
                # Use LaTeX if available, otherwise use text
                answer_to_grade = latex_content if latex_content else text_content
                
                # Parse answer into steps
                student_steps = parse_answer_into_steps(answer_to_grade)
                
                if not student_steps:
                    continue
                
                # Get gold solution steps
                gold_steps = [
                    GraderStep(
                        content=step.expression or step.latex or '',
                        points=float(step.points),
                        required=step.required
                    )
                    for step in question.gold_steps
                ]
                
                if not gold_steps:
                    continue
                
                grader = HybridGrader(gold_steps, use_ml=True, use_symbolic=True)
                grading_result = grader.grade(student_steps)
                
                # Store grading result
                db_grading_result = models.GradingResult(
                    submission_id=submission.id,
                    question_id=question.id,
                    extracted_text=text_content,
                    extracted_latex=latex_content,
                    score=grading_result['total_score'],
                    max_score=grading_result['max_score'],
                    feedback=f"Graded: {grading_result['percentage']:.1f}%",
                    is_correct=grading_result['percentage'] >= 70
                )
                db.add(db_grading_result)
                db.flush()
                
                # Store step results
                for idx, (student_step, evaluation) in enumerate(
                    zip(student_steps, grading_result['evaluations']), start=1
                ):
                    matched_gold = None
                    if evaluation.matched_gold_step is not None:
                        matched_gold_step_obj = gold_steps[evaluation.matched_gold_step]
                        matched_gold = matched_gold_step_obj.content
                    
                    step_result = models.StepResult(
                        grading_result_id=db_grading_result.id,
                        step_number=idx,
                        student_text=student_step,
                        is_correct=evaluation.status.value == "Correct",
                        score=evaluation.points_earned,
                        max_score=gold_steps[evaluation.matched_gold_step].points if evaluation.matched_gold_step is not None else 0,
                        feedback=evaluation.feedback,
                        expected=matched_gold,
                        received=student_step
                    )
                    db.add(step_result)
                
                total_score += grading_result['total_score']
                
        except Exception as e:
            print(f"Error grading typed answers: {e}")
            import traceback
            traceback.print_exc()
    
    # Process images with OCR if available
    if has_images:
        for image in submission.images:
            image_path = Path(image.image_path)
            if not image_path.exists():
                continue
            
            # Run OCR
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            ocr_result = ocr_processor.extract_steps_from_file(
                image_bytes,
                image_path.name
            )
            
            student_steps = ocr_result.steps
            
            # Grade each question (assuming one question per image for now)
            if image.page_number <= len(questions):
                question = questions[image.page_number - 1]
                
                # Get gold solution steps
                gold_steps = [
                    GraderStep(
                        content=step.expression,
                        points=float(step.points),
                        required=step.required
                    )
                    for step in question.gold_steps
                ]
                
                grader = HybridGrader(gold_steps, use_ml=True, use_symbolic=True)
                grading_result = grader.grade(student_steps)
                
                # Store grading result
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
                
                # Store step results
                for idx, (student_step, evaluation) in enumerate(
                    zip(student_steps, grading_result['evaluations']), start=1
                ):
                    matched_gold = None
                    if evaluation.matched_gold_step is not None:
                        matched_gold = gold_steps[evaluation.matched_gold_step].content
                    
                    step_result = models.StepResult(
                        grading_result_id=db_grading_result.id,
                        step_number=idx,
                        student_text=student_step,
                        is_correct=evaluation.status.value == "Correct",
                        score=evaluation.points_earned,
                        max_score=gold_steps[evaluation.matched_gold_step].points if evaluation.matched_gold_step is not None else 0,
                        feedback=evaluation.feedback,
                        expected=matched_gold,
                        received=student_step
                    )
                    db.add(step_result)
                
                total_score += grading_result['total_score']
    
    # Update submission
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


@app.put("/api/submissions/{submission_id}/adjust-grades")
async def adjust_grades(
    submission_id: str,
    adjustments: schemas.GradeAdjustmentRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adjust grades and add feedback before approval"""
    if current_user.role not in [models.UserRole.PROFESSOR, models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only professors can adjust grades")
    
    submission = db.query(models.Submission).filter(
        models.Submission.id == submission_id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    total_score = 0
    
    for adj in adjustments.adjustments:
        grading_result = db.query(models.GradingResult).filter(
            models.GradingResult.id == adj.gradingResultId
        ).first()
        
        if not grading_result:
            continue
        
        if adj.score is not None:
            grading_result.score = adj.score
        if adj.feedback:
            grading_result.feedback = adj.feedback
        
        if adj.stepAdjustments:
            for step_adj in adj.stepAdjustments:
                step_result = db.query(models.StepResult).filter(
                    models.StepResult.id == step_adj.stepResultId
                ).first()
                
                if step_result:
                    if step_adj.score is not None:
                        step_result.score = step_adj.score
                    if step_adj.feedback:
                        step_result.feedback = step_adj.feedback
        
        total_score += grading_result.score
    
    submission.total_score = total_score
    submission.status = models.SubmissionStatus.AWAITING_APPROVAL
    db.commit()
    
    return {
        "status": "success",
        "message": "Grades adjusted successfully",
        "totalScore": total_score
    }


@app.post("/api/submissions/{submission_id}/approve")
async def approve_submission(
    submission_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve a graded submission"""
    if current_user.role not in [models.UserRole.PROFESSOR, models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only professors can approve submissions")
    
    submission = db.query(models.Submission).filter(
        models.Submission.id == submission_id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.status != models.SubmissionStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Submission is not awaiting approval")
    
    submission.status = models.SubmissionStatus.APPROVED
    submission.approved_at = datetime.utcnow()
    submission.approved_by = current_user.id
    db.commit()
    
    return {
        "status": "success",
        "message": "Submission approved successfully"
    }


@app.post("/api/submissions/{submission_id}/reject")
async def reject_submission(
    submission_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject a graded submission and allow resubmission"""
    if current_user.role not in [models.UserRole.PROFESSOR, models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only professors can reject submissions")
    
    submission = db.query(models.Submission).filter(
        models.Submission.id == submission_id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.status != models.SubmissionStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Submission is not awaiting approval")
    
    submission.status = models.SubmissionStatus.PENDING
    submission.total_score = None
    submission.graded_at = None
    
    for grading_result in submission.grading_results:
        db.delete(grading_result)
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Submission rejected. Student can resubmit."
    }


@app.get("/api/dashboard/stats", response_model=schemas.DashboardStatsResponse)
def get_dashboard_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for current user"""
    if current_user.role == models.UserRole.PROFESSOR:
        # Professor stats
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
        
        # Average score
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
        # Student stats
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
        # Admin stats
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


# ============================================================================
# Health Check
# ============================================================================

@app.get("/")
def root():
    """Root endpoint - API health check"""
    return {
        "name": "EasyGrade API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


def _pdf_safe_text(s) -> str:
    """Make text safe for ReportLab Paragraph (default font is Latin-1 only)."""
    if s is None:
        return ""
    if isinstance(s, bytes):
        try:
            s = s.decode("utf-8")
        except UnicodeDecodeError:
            s = s.decode("utf-8", errors="replace")
    if not isinstance(s, str) or not s:
        return ""
    try:
        s = s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    import unicodedata
    s = unicodedata.normalize("NFKD", s)
    out = []
    for c in s:
        if ord(c) < 128:
            out.append(c)
        else:
            if c in "\u2018\u2019":
                out.append("'")
            elif c in "\u201c\u201d":
                out.append('"')
            elif c in "\u2014\u2013":
                out.append("-")
            elif c == "\u00d7":
                out.append("x")
            elif c == "\u00f7":
                out.append("/")
            elif c == "\u00b0":
                out.append(" deg ")
            elif c == "\u00b2":
                out.append("^2")
            elif c == "\u00b3":
                out.append("^3")
            elif c == "\u00bd":
                out.append("1/2")
            else:
                out.append(" ")
    result = "".join(out)
    result = result.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # If text looks like encoding garbage (symbol soup), don't show it
    if result and len(result) > 25:
        word_chars = sum(1 for c in result if c.isalnum() or c in " .,;:?!'-/")
        symbol_soup = sum(1 for c in result if c in "|~=}{\\<>_-+")
        ratio = word_chars / len(result)
        # Replace if: low word ratio, or high density of symbol-soup characters
        if ratio < 0.40 or (symbol_soup / len(result)) > 0.12:
            return "[Question text could not be displayed. Re-upload the exam as PDF or .txt to restore content, or edit manually.]"
    return result


def _normalize_text_for_storage(s) -> str:
    """Normalize encoding for storing in DB. Does NOT replace content with placeholder (use only when saving)."""
    if s is None:
        return ""
    if isinstance(s, bytes):
        try:
            s = s.decode("utf-8")
        except UnicodeDecodeError:
            s = s.decode("utf-8", errors="replace")
    if not isinstance(s, str) or not s:
        return ""
    import unicodedata
    s = unicodedata.normalize("NFKD", s)
    # Remove null bytes and other control chars
    s = "".join(c for c in s if c != "\x00" and (ord(c) >= 32 or c in "\n\r\t"))
    return s

def _display_safe_text(s) -> str:
    """Clean text for display (fix encoding/garble). Same as _pdf_safe_text but no HTML escape."""
    if s is None:
        return ""
    if isinstance(s, bytes):
        try:
            s = s.decode("utf-8")
        except UnicodeDecodeError:
            s = s.decode("utf-8", errors="replace")
    if not isinstance(s, str) or not s:
        return ""
    try:
        s = s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    import unicodedata
    s = unicodedata.normalize("NFKD", s)
    out = []
    for c in s:
        if ord(c) < 128:
            out.append(c)
        elif c in "\u2018\u2019":
            out.append("'")
        elif c in "\u201c\u201d":
            out.append('"')
        elif c in "\u2014\u2013":
            out.append("-")
        elif c == "\u00d7":
            out.append("x")
        elif c == "\u00f7":
            out.append("/")
        elif c == "\u00b0":
            out.append(" deg ")
        elif c == "\u00b2":
            out.append("^2")
        elif c == "\u00b3":
            out.append("^3")
        elif c == "\u00bd":
            out.append("1/2")
        else:
            out.append(" ")
    result = "".join(out)
    # If text looks like encoding garbage (symbol soup), don't show it
    if result and len(result) > 25:
        word_chars = sum(1 for c in result if c.isalnum() or c in " .,;:?!'-/")
        symbol_soup = sum(1 for c in result if c in "|~=}{\\<>_-+")
        ratio = word_chars / len(result)
        # Don't hide content that clearly looks like exam text (has "Question" and "Solution"/"Gold"/numbers)
        sample = result[:600].lower()
        looks_like_exam = (
            "question" in sample and ("solution" in sample or "gold" in sample or "answer" in sample)
        ) or ("question" in sample and any(c.isdigit() for c in sample))
        if looks_like_exam and ratio >= 0.25 and (symbol_soup / len(result)) <= 0.20:
            return result
        if ratio < 0.40 or (symbol_soup / len(result)) > 0.12:
            return "[Question text could not be displayed. Re-upload the exam as PDF or .txt to restore content, or edit manually.]"
    return result


@app.get("/api/exams/{exam_id}/download")
async def download_exam_pdf(
    exam_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download exam as PDF"""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO
    
    if current_user.role not in [models.UserRole.PROFESSOR, models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only professors can download exams")
    
    exam = db.query(models.Exam).options(
        selectinload(models.Exam.questions).options(
            selectinload(models.Question.attachments),
            selectinload(models.Question.embedded_content),
            selectinload(models.Question.gold_steps),
        )
    ).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    course = db.query(models.Course).filter(models.Course.id == exam.course_id).first()
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    from reportlab.platypus import Image as RLImage, Table as RLTable, TableStyle
    from reportlab.lib.utils import ImageReader
    styles = getSampleStyleSheet()
    
    def add_image_to_story(path, story, max_w=6.5*inch, max_h=8*inch):
        try:
            reader = ImageReader(str(path))
            iw, ih = reader.getSize()
            if iw <= 0 or ih <= 0:
                return
            aspect = ih / float(iw)
            w, h = max_w, max_w * aspect
            if h > max_h:
                h = max_h
                w = max_h / aspect
            img = RLImage(str(path), width=w, height=h)
            story.append(Spacer(1, 0.15*inch))
            story.append(img)
            story.append(Spacer(1, 0.15*inch))
        except Exception as e:
            logger.warning(f"Could not add image to PDF: {e}")
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor='black',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='black',
        spaceAfter=12,
    )
    normal_style = styles["Normal"]
    
    story = []
    
    story.append(Paragraph(_pdf_safe_text(exam.title), title_style))
    story.append(Spacer(1, 0.2*inch))
    
    if course:
        story.append(Paragraph(f"<b>Course:</b> {_pdf_safe_text(course.name)}", normal_style))
    if exam.description:
        story.append(Paragraph(f"<b>Description:</b> {_pdf_safe_text(exam.description)}", normal_style))
    if exam.due_date:
        story.append(Paragraph(f"<b>Due Date:</b> {exam.due_date.strftime('%Y-%m-%d %H:%M')}", normal_style))
    story.append(Paragraph(f"<b>Total Points:</b> {exam.total_points}", normal_style))
    story.append(Spacer(1, 0.4*inch))
    
    if not exam.questions:
        story.append(Paragraph("No questions available.", normal_style))
    else:
        for question in sorted(exam.questions, key=lambda q: q.number):
            story.append(Paragraph(f"<b>Question {question.number}</b> ({question.points} points)", heading_style))
            
            question_text = question.text or ""
            if question_text:
                story.append(Paragraph(_pdf_safe_text(question_text), normal_style))
            for att in getattr(question, "attachments", []) or []:
                if getattr(att, "attachment_type", "") != "image":
                    continue
                path = UPLOAD_DIR / att.file_path
                if path.exists():
                    add_image_to_story(path, story)
            for ec in getattr(question, "embedded_content", []) or []:
                ct = getattr(ec, "content_type", "") or ""
                content_data = getattr(ec, "content_data", None)
                if ct == "table" and content_data:
                    try:
                        import json
                        data = json.loads(content_data) if isinstance(content_data, str) else content_data
                        raw_rows = data.get("rows") or data.get("data") or []
                        if raw_rows:
                            rows = [[str(c) for c in (row if isinstance(row, (list, tuple)) else [row])] for row in raw_rows]
                            table = RLTable(rows)
                            table.setStyle(TableStyle([
                                ("BACKGROUND", (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
                                ("TEXTCOLOR", (0, 0), (-1, 0), (0, 0, 0)),
                                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                ("FONTSIZE", (0, 0), (-1, -1), 9),
                                ("GRID", (0, 0), (-1, -1), 0.5, (0.5, 0.5, 0.5)),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ]))
                            story.append(Spacer(1, 0.2*inch))
                            story.append(table)
                            story.append(Spacer(1, 0.2*inch))
                    except Exception as e:
                        logger.warning(f"Could not add table to PDF: {e}")
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("Answer:", normal_style))
            story.append(Spacer(1, 0.5*inch))
            gold_steps = list(getattr(question, "gold_steps", []) or [])
            if gold_steps:
                story.append(Paragraph("<b>Solution (reference):</b>", heading_style))
                for gs in sorted(gold_steps, key=lambda x: getattr(x, "step_number", 0)):
                    step_text = _pdf_safe_text(getattr(gs, "expression", "") or getattr(gs, "latex", "") or "")
                    if step_text:
                        story.append(Paragraph(f"Step {getattr(gs, 'step_number', 0)}: {step_text}", normal_style))
                story.append(Spacer(1, 0.4*inch))
            else:
                final_ans = getattr(question, "final_answer", None) or getattr(question, "final_answer_latex", None)
                if final_ans and str(final_ans).strip():
                    story.append(Paragraph("<b>Solution (reference):</b>", heading_style))
                    story.append(Paragraph(_pdf_safe_text(str(final_ans).strip()), normal_style))
                    story.append(Spacer(1, 0.4*inch))
                else:
                    story.append(Paragraph("<b>Solution (reference):</b>", heading_style))
                    story.append(Paragraph("<i>No reference solution stored for this question.</i>", normal_style))
                    story.append(Spacer(1, 0.4*inch))
    
    try:
        doc.build(story)
        buffer.seek(0)
    except Exception as e:
        logger.error(f"Error building PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
    
    from fastapi.responses import StreamingResponse
    safe_filename = _pdf_safe_text(exam.title).replace(" ", "_").replace("/", "_").replace("\\", "_")[:100]
    if not safe_filename:
        safe_filename = "exam"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={safe_filename}.pdf"}
    )


@app.get("/api/exams/{exam_id}/view-pdf")
async def view_exam_pdf(
    exam_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View/download exam PDF - available to both teachers and students"""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO
    
    exam = db.query(models.Exam).options(
        selectinload(models.Exam.questions).options(
            selectinload(models.Question.attachments),
            selectinload(models.Question.embedded_content),
            selectinload(models.Question.gold_steps),
        )
    ).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    course = db.query(models.Course).filter(models.Course.id == exam.course_id).first()
    
    if current_user.role == models.UserRole.STUDENT:
        if not exam.is_published:
            raise HTTPException(status_code=403, detail="Exam is not published")
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    from reportlab.platypus import Image as RLImage, Table as RLTable, TableStyle
    from reportlab.lib.utils import ImageReader
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor='black',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='black',
        spaceAfter=12,
    )
    normal_style = styles["Normal"]
    
    def add_image_to_story_v(path, story, max_w=6.5*inch, max_h=8*inch):
        try:
            reader = ImageReader(str(path))
            iw, ih = reader.getSize()
            if iw <= 0 or ih <= 0:
                return
            aspect = ih / float(iw)
            w, h = max_w, max_w * aspect
            if h > max_h:
                h = max_h
                w = max_h / aspect
            img = RLImage(str(path), width=w, height=h)
            story.append(Spacer(1, 0.15*inch))
            story.append(img)
            story.append(Spacer(1, 0.15*inch))
        except Exception as e:
            logger.warning(f"Could not add image to PDF: {e}")
    
    story = []
    story.append(Paragraph(_pdf_safe_text(exam.title), title_style))
    story.append(Spacer(1, 0.2*inch))
    
    if course:
        story.append(Paragraph(f"<b>Course:</b> {_pdf_safe_text(course.name)}", normal_style))
    if exam.description:
        story.append(Paragraph(f"<b>Description:</b> {_pdf_safe_text(exam.description)}", normal_style))
    if exam.due_date:
        story.append(Paragraph(f"<b>Due Date:</b> {exam.due_date.strftime('%Y-%m-%d %H:%M')}", normal_style))
    story.append(Paragraph(f"<b>Total Points:</b> {exam.total_points}", normal_style))
    story.append(Spacer(1, 0.4*inch))
    
    if not exam.questions:
        story.append(Paragraph("No questions available.", normal_style))
    else:
        for question in sorted(exam.questions, key=lambda q: q.number):
            story.append(Paragraph(f"<b>Question {question.number}</b> ({question.points} points)", heading_style))
            
            question_text = question.text or ""
            if question_text:
                story.append(Paragraph(_pdf_safe_text(question_text), normal_style))
            for att in getattr(question, "attachments", []) or []:
                if getattr(att, "attachment_type", "") != "image":
                    continue
                path = UPLOAD_DIR / att.file_path
                if path.exists():
                    add_image_to_story_v(path, story)
            for ec in getattr(question, "embedded_content", []) or []:
                ct = getattr(ec, "content_type", "") or ""
                content_data = getattr(ec, "content_data", None)
                if ct == "table" and content_data:
                    try:
                        import json
                        data = json.loads(content_data) if isinstance(content_data, str) else content_data
                        raw_rows = data.get("rows") or data.get("data") or []
                        if raw_rows:
                            rows = [[str(c) for c in (row if isinstance(row, (list, tuple)) else [row])] for row in raw_rows]
                            table = RLTable(rows)
                            table.setStyle(TableStyle([
                                ("BACKGROUND", (0, 0), (-1, 0), (0.8, 0.8, 0.8)),
                                ("TEXTCOLOR", (0, 0), (-1, 0), (0, 0, 0)),
                                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                ("FONTSIZE", (0, 0), (-1, -1), 9),
                                ("GRID", (0, 0), (-1, -1), 0.5, (0.5, 0.5, 0.5)),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ]))
                            story.append(Spacer(1, 0.2*inch))
                            story.append(table)
                            story.append(Spacer(1, 0.2*inch))
                    except Exception as e:
                        logger.warning(f"Could not add table to PDF: {e}")
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("Answer:", normal_style))
            story.append(Spacer(1, 0.5*inch))
            gold_steps = list(getattr(question, "gold_steps", []) or [])
            if gold_steps:
                story.append(Paragraph("<b>Solution (reference):</b>", heading_style))
                for gs in sorted(gold_steps, key=lambda x: getattr(x, "step_number", 0)):
                    step_text = _pdf_safe_text(getattr(gs, "expression", "") or getattr(gs, "latex", "") or "")
                    if step_text:
                        story.append(Paragraph(f"Step {getattr(gs, 'step_number', 0)}: {step_text}", normal_style))
                story.append(Spacer(1, 0.4*inch))
            else:
                final_ans = getattr(question, "final_answer", None) or getattr(question, "final_answer_latex", None)
                if final_ans and str(final_ans).strip():
                    story.append(Paragraph("<b>Solution (reference):</b>", heading_style))
                    story.append(Paragraph(_pdf_safe_text(str(final_ans).strip()), normal_style))
                    story.append(Spacer(1, 0.4*inch))
                else:
                    story.append(Paragraph("<b>Solution (reference):</b>", heading_style))
                    story.append(Paragraph("<i>No reference solution stored for this question.</i>", normal_style))
                    story.append(Spacer(1, 0.4*inch))
    
    try:
        doc.build(story)
        buffer.seek(0)
    except Exception as e:
        logger.error(f"Error building PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
    
    from fastapi.responses import StreamingResponse
    safe_filename = _pdf_safe_text(exam.title).replace(" ", "_").replace("/", "_").replace("\\", "_")[:100]
    if not safe_filename:
        safe_filename = "exam"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={safe_filename}.pdf"}
    )



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

