"""
FastAPI backend for EasyGrade
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func
from typing import List, Optional, Tuple, Any
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
_default_origins = "http://localhost:8080,http://localhost:5173,http://localhost:3000"
allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()]
# Optional: Railway hostnames can include a random segment (e.g. ...-production-aa10...).
# Set e.g. https://distinguished-charm-production-.*\.up\.railway\.app to match that frontend.
_cors_origin_regex = os.getenv("ALLOWED_ORIGIN_REGEX", "").strip() or None
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=_cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info(
    "CORS: allow_origins=%s allow_origin_regex=%s",
    allowed_origins,
    _cors_origin_regex or "(none)",
)

# Serve uploaded files (exam assets, profile photos, etc.)
app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOAD_DIR.resolve())),
    name="uploads",
)

# Initialize OCR processor
ocr_processor = OCRProcessor(language="en", dpi=300, psm=6, use_easyocr=False)


def _include_grading_in_submission_payload(submission: models.Submission, viewer: models.User) -> bool:
    """
    Whether API clients should receive per-question grading (scores, steps).
    Students only receive scores/feedback after the instructor approves (published).
    Professors see grading whenever it exists (graded, awaiting approval, or pending with rows).
    """
    st = submission.status
    if viewer.role == models.UserRole.STUDENT:
        return st == models.SubmissionStatus.APPROVED
    if st in (
        models.SubmissionStatus.GRADED,
        models.SubmissionStatus.APPROVED,
        models.SubmissionStatus.AWAITING_APPROVAL,
    ):
        return True
    if viewer.role in (models.UserRole.PROFESSOR, models.UserRole.ADMIN):
        if st in (models.SubmissionStatus.PENDING, models.SubmissionStatus.GRADING):
            return bool(submission.grading_results)
    return False


def _submission_total_score_for_api(
    submission: models.Submission, viewer: models.User, include_grading: bool
):
    """Hide total score from students until grades are approved and released."""
    if viewer.role == models.UserRole.STUDENT and not include_grading:
        return None
    return submission.total_score


def _step_result_max_score(evaluation: Any, gold_steps: List[GraderStep], step_number: int) -> int:
    """
    Points cap shown for each step row. When no rubric step matched (e.g. extra
    OCR line), use the gold step at the same position so the UI does not show 0/0.
    """
    mi = evaluation.matched_gold_step
    if mi is not None and 0 <= mi < len(gold_steps):
        return int(round(gold_steps[mi].points))
    if not gold_steps:
        return 0
    hint_idx = min(max(step_number - 1, 0), len(gold_steps) - 1)
    return int(round(gold_steps[hint_idx].points))


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


def _optional_str(value) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def user_to_response(user: models.User) -> schemas.UserResponse:
    """Convert User model to UserResponse schema"""
    return schemas.UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        avatar=user.avatar,
        createdAt=user.created_at,
        institution=user.institution,
        country=user.country,
        majorDepartment=user.major_department,
        yearOfStudy=user.year_of_study,
        gender=user.gender,
        studentId=user.student_id,
        dateOfBirth=user.date_of_birth,
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
        name=user_data.name.strip(),
        email=str(user_data.email).strip().lower(),
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        institution=_optional_str(user_data.institution),
        country=_optional_str(user_data.country),
        major_department=_optional_str(user_data.majorDepartment),
        year_of_study=user_data.yearOfStudy,
        gender=_optional_str(user_data.gender),
        student_id=_optional_str(user_data.studentId),
        date_of_birth=user_data.dateOfBirth,
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


@app.put("/api/auth/me", response_model=schemas.UserResponse)
def update_me(
    body: schemas.UserProfileUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update profile (name, email, and/or password) for the signed-in user."""
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Name cannot be empty")
        current_user.name = name

    if body.email is not None:
        email_norm = str(body.email).strip().lower()
        existing = db.query(models.User).filter(models.User.email == email_norm).first()
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = email_norm

    if body.new_password:
        if not body.current_password:
            raise HTTPException(status_code=400, detail="Current password required to set a new password")
        if not verify_password(body.current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        if len(body.new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
        current_user.password_hash = get_password_hash(body.new_password)
    elif body.current_password is not None and body.new_password is None:
        raise HTTPException(status_code=400, detail="Provide new_password when sending current_password")

    # Demographics: only update keys the client sent (supports clearing with null / "")
    _prof = body.model_dump(exclude_unset=True)
    if "institution" in _prof:
        current_user.institution = _optional_str(_prof["institution"])
    if "country" in _prof:
        current_user.country = _optional_str(_prof["country"])
    if "majorDepartment" in _prof:
        current_user.major_department = _optional_str(_prof["majorDepartment"])
    if "yearOfStudy" in _prof:
        current_user.year_of_study = _prof["yearOfStudy"]
    if "gender" in _prof:
        current_user.gender = _optional_str(_prof["gender"])
    if "studentId" in _prof:
        current_user.student_id = _optional_str(_prof["studentId"])
    if "dateOfBirth" in _prof:
        current_user.date_of_birth = _prof["dateOfBirth"]

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return user_to_response(current_user)


_AVATAR_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
_AVATAR_ALLOWED_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif"}
)


@app.post("/api/auth/me/avatar", response_model=schemas.UserResponse)
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a profile picture (JPEG, PNG, WebP, or GIF; max 2 MB)."""
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct not in _AVATAR_ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Please upload a JPEG, PNG, WebP, or GIF image",
        )
    raw = await file.read()
    if len(raw) > _AVATAR_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Image must be 2 MB or smaller")

    ext_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    ext = ext_map.get(ct, ".jpg")
    av_dir = UPLOAD_DIR / "avatars"
    av_dir.mkdir(parents=True, exist_ok=True)
    for old in av_dir.glob(f"{current_user.id}.*"):
        try:
            old.unlink()
        except OSError:
            pass
    dest_name = f"{current_user.id}{ext}"
    dest = av_dir / dest_name
    with open(dest, "wb") as f:
        f.write(raw)

    rel = f"/uploads/avatars/{dest_name}"
    current_user.avatar = rel[:500]
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return user_to_response(current_user)


@app.delete("/api/auth/me/avatar", response_model=schemas.UserResponse)
def delete_my_avatar(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove profile photo."""
    av_dir = UPLOAD_DIR / "avatars"
    if av_dir.is_dir():
        for old in av_dir.glob(f"{current_user.id}.*"):
            try:
                old.unlink(missing_ok=True)
            except OSError:
                pass
    current_user.avatar = None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
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
            # Never replace real richContent with the placeholder — the frontend renders it properly
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
        # Never replace real richContent with the placeholder — the frontend renders it properly
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


@app.post("/api/exams/{exam_id}/preview-answer-pdf")
async def preview_exam_answer_pdf(
    exam_id: str,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Preview how a full-answer PDF will be routed to questions (no submission created).
    """
    fn = (file.filename or "").lower()
    if not fn.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    exam = (
        db.query(models.Exam)
        .options(selectinload(models.Exam.questions))
        .filter(models.Exam.id == exam_id)
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    pdf_bytes = await file.read()
    max_b = 25 * 1024 * 1024
    if len(pdf_bytes) > max_b:
        raise HTTPException(
            status_code=400,
            detail="PDF is too large for preview (max 25 MB).",
        )

    preview = build_answer_pdf_preview(pdf_bytes, exam, ocr_processor)
    return preview


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
    
    # ── Before cascade-deleting questions, protect attachments referenced by image
    # nodes inside rich content (otherwise the cascade wipes them and their files
    # become un-findable when the PDF is generated later). ──────────────────────
    import re as _re_att
    _protected_att_paths: dict[str, str] = {}  # {att_id: file_path}

    def _collect_rich_image_att_ids(node) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "image":
            src = node.get("attrs", {}).get("src", "")
            m = _re_att.search(r'/api/attachments/([^/]+)/file', src)
            if m:
                _protected_att_paths[m.group(1)] = ""  # value filled below
        for child in node.get("content") or []:
            _collect_rich_image_att_ids(child)

    for _q in exam.questions:
        if _q.rich_content:
            try:
                _rc = json.loads(_q.rich_content) if isinstance(_q.rich_content, str) else _q.rich_content
                _collect_rich_image_att_ids(_rc)
            except Exception:
                pass

    # Unlink protected attachments from their question so they survive cascade-delete
    for _att_id in list(_protected_att_paths.keys()):
        _att = db.query(models.QuestionAttachment).filter(
            models.QuestionAttachment.id == _att_id
        ).first()
        if _att:
            _protected_att_paths[_att_id] = _att.file_path  # remember where the file lives
            _att.question_id = ""  # detach → won't be cascade-deleted
    db.flush()

    # Delete existing questions (cascade will delete gold steps, non-protected attachments, embedded_content)
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

        # Re-link any protected (rich-content) attachments whose IDs appear in this question
        if question_data.richContent:
            _qrc = json.dumps(question_data.richContent) if isinstance(question_data.richContent, dict) else question_data.richContent
            for _pid, _ppath in list(_protected_att_paths.items()):
                if _pid in (_qrc or "") and _ppath:
                    _patt = db.query(models.QuestionAttachment).filter(
                        models.QuestionAttachment.id == _pid
                    ).first()
                    if _patt:
                        _patt.question_id = new_question.id

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
    # TipTap Mathematics: data-type="inline-math" or "block-math", LaTeX in data-latex attribute
    latex_content = None
    all_latex = []
    # data-latex="..." (TipTap and similar)
    for attr_match in re.finditer(r'data-latex="([^"]*)"', html_content):
        if attr_match.group(1).strip():
            all_latex.append(attr_match.group(1).strip())
    # Legacy / markdown-style patterns
    latex_patterns = [
        r'<span[^>]*data-type="(?:inline-)?math"[^>]*>(.*?)</span>',
        r'<div[^>]*data-type="block-math"[^>]*>(.*?)</div>',
        r'<span[^>]*class="[^"]*math[^"]*"[^>]*>(.*?)</span>',
        r'\$\$(.*?)\$\$',
        r'\$(.*?)\$',
        r'\\\[(.*?)\\\]',
        r'\\\((.*?)\\\)',
    ]
    for pattern in latex_patterns:
        matches = re.findall(pattern, html_content, re.DOTALL)
        if matches:
            all_latex.extend([m.strip() for m in matches if m and m.strip()])
    
    if all_latex:
        # Newlines keep separate math fields as separate lines so
        # parse_answer_into_steps can treat each TipTap math node as its own step.
        latex_content = "\n".join([m.strip() for m in all_latex if m.strip()])
    
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


def _typed_answer_for_api_display(typed_answer: str) -> Tuple[str, Optional[str]]:
    """
    Stored TipTap/HTML → fields for SubmittedAnswerResponse.
    Reuses extract_math_from_html so answers that are mostly math nodes (data-latex)
    are not reduced to empty strings by naive tag stripping.
    """
    if not typed_answer or not str(typed_answer).strip():
        return "", None
    raw = str(typed_answer)
    text_content, latex_content = extract_math_from_html(raw)
    display = (text_content or "").strip()
    if not display and latex_content:
        display = latex_content.strip()
    if not display:
        display = raw.strip()
    return display, latex_content


def _merge_typed_answers_into_responses(
    answers: List[schemas.SubmittedAnswerResponse],
    typed_answers_json: Optional[str],
    questions_by_id: dict,
    graded_question_ids: set,
) -> None:
    """Append one SubmittedAnswerResponse per typed row; never drop rows with content."""
    if not typed_answers_json or not typed_answers_json.strip():
        return
    import json as _json_merge

    try:
        typed_answers_data = _json_merge.loads(typed_answers_json)
    except Exception:
        return
    if not isinstance(typed_answers_data, list):
        return

    graded_set = {str(x) for x in graded_question_ids}

    for answer_data in typed_answers_data:
        if not isinstance(answer_data, dict):
            continue
        question_id = answer_data.get("questionId")
        question_number = answer_data.get("questionNumber")
        typed_answer = answer_data.get("typedAnswer", "")
        if typed_answer is None or not str(typed_answer).strip():
            continue

        qid_key = str(question_id) if question_id is not None else None
        if qid_key and qid_key in graded_set:
            continue

        question = None
        if question_id is not None:
            question = questions_by_id.get(question_id) or questions_by_id.get(str(question_id))
        if not question and question_number is not None:
            try:
                qn = int(question_number)
            except (TypeError, ValueError):
                qn = None
            if qn is not None:
                question = next((q for q in questions_by_id.values() if q.number == qn), None)

        display, latex_vis = _typed_answer_for_api_display(str(typed_answer))

        if question:
            answers.append(
                schemas.SubmittedAnswerResponse(
                    questionId=str(question_id or question.id),
                    questionNumber=int(question_number if question_number is not None else question.number),
                    extractedText=display,
                    extractedLatex=latex_vis,
                    extractedSteps=[],
                    gradingResult=None,
                )
            )
        else:
            # Question id/number no longer on exam — still return the payload so instructors see work
            try:
                qnum = int(question_number) if question_number is not None else 0
            except (TypeError, ValueError):
                qnum = 0
            answers.append(
                schemas.SubmittedAnswerResponse(
                    questionId=str(question_id or "unknown"),
                    questionNumber=qnum,
                    extractedText=display,
                    extractedLatex=latex_vis,
                    extractedSteps=[],
                    gradingResult=None,
                )
            )


def _top_level_equals_indices(s: str) -> List[int]:
    """
    Indices of '=' that sit at LaTeX depth 0 (outside {...} and outside \\left/\\right groups).
    Ignores '=' that are part of <=, >=, != when written with ASCII.
    """
    bi = 0
    pi = 0
    i = 0
    n = len(s)
    out: List[int] = []
    while i < n:
        if s.startswith("\\left", i):
            pi += 1
            i += 5
            if i < n:
                i += 1
            continue
        if s.startswith("\\right", i):
            if pi > 0:
                pi -= 1
            i += 6
            while i < n and s[i].isspace():
                i += 1
            if i < n and s[i] in ")}]|.":
                i += 1
            continue
        c = s[i]
        if c == "\\":
            i += 1
            if i < n and s[i].isalpha():
                while i < n and s[i].isalpha():
                    i += 1
            elif i < n:
                i += 1
            continue
        if c == "{":
            bi += 1
        elif c == "}" and bi > 0:
            bi -= 1
        elif c == "=" and bi == 0 and pi == 0:
            if i > 0 and s[i - 1] in "<>!":
                i += 1
                continue
            out.append(i)
        i += 1
    return out


def _latex_chain_equations(s: str) -> List[str]:
    """
    If s has k top-level '=' signs, treat it as a chain P0=P1=...=Pk and emit
    k equations P0=P1, P1=P2, ... (standard for glued work like A=B=C).
    """
    idx = _top_level_equals_indices(s)
    if len(idx) < 2:
        return [s.strip()] if s.strip() else []
    parts: List[str] = []
    prev = 0
    for pos in idx:
        parts.append(s[prev:pos])
        prev = pos + 1
    parts.append(s[prev:])
    out: List[str] = []
    for i in range(len(idx)):
        lhs = parts[i].strip()
        rhs = parts[i + 1].strip()
        joined = f"{lhs}={rhs}".strip()
        if joined and "=" in joined:
            out.append(joined)
    return out if out else [s.strip()]


def _split_glued_digit_then_latex(s: str) -> List[str]:
    """
    Split '...=1 \\frac{...}' (digit directly touching a following LaTeX command) into
    separate segments so each equation can be graded.
    """
    s = s.strip()
    if not s:
        return []
    out: List[str] = []
    remaining = s
    while remaining:
        m = re.match(r"^(.+?)=(\d+)\s+(\\[a-zA-Z].*)$", remaining, re.DOTALL)
        if m:
            out.append(f"{m.group(1)}={m.group(2)}".strip())
            remaining = m.group(3).strip()
            continue
        m2 = re.match(r"^(.+?)=(\d+)(\\[a-zA-Z].*)$", remaining, re.DOTALL)
        if m2:
            out.append(f"{m2.group(1)}={m2.group(2)}".strip())
            remaining = m2.group(3).strip()
            continue
        out.append(remaining)
        break
    return out


def _finalize_latex_step_segments(blob: str) -> List[str]:
    """Apply glued-number splits, then chain-split any segment with 2+ top-level '='."""
    blob = blob.strip()
    if not blob:
        return []
    final: List[str] = []
    for piece in _split_glued_digit_then_latex(blob):
        if not piece:
            continue
        if len(_top_level_equals_indices(piece)) >= 2:
            final.extend(_latex_chain_equations(piece))
        else:
            final.append(piece)
    return [x for x in final if x.strip()]


def parse_answer_into_steps(answer_text: str) -> List[str]:
    """
    Parse a student's answer into individual steps.
    Uses multiple strategies so step-by-step grading works even when the student
    doesn't use explicit "Step 1" labels (e.g. numbered lines, newlines, = or ;).
    """
    if not answer_text or not answer_text.strip():
        return []

    text = answer_text.strip()
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # ---- 1) Single line: try to split into steps ----
    if len(lines) <= 1:
        single_line = text
        # Glue fix: "=1\\frac" → "=1 \\frac" so boundaries are visible.
        single_line = re.sub(r"=(\d+)(\\[a-zA-Z])", r"=\1 \2", single_line)

        # 1a) Numbered steps in one line: "1. foo 2. bar" or "(1) foo (2) bar"
        numbered_dot = re.split(r'\s+(?=\d+\.\s+)', single_line)
        if len(numbered_dot) > 1:
            out = [s.strip() for s in numbered_dot if s.strip()]
            if out:
                return out
        numbered_paren = re.split(r'\s+(?=\(\d+\)\s+)', single_line)
        if len(numbered_paren) > 1:
            out = [s.strip() for s in numbered_paren if s.strip()]
            if out:
                return out

        # 1b) LaTeX / algebra one line: split before "\\frac", "\\lim", etc. When the
        # line has backslashes, ONLY split at "\\command" boundaries — otherwise a
        # pattern like (?=[a-zA-Z]) fires on the space inside "\\sin x".
        if "=" in single_line:
            if "\\" in single_line:
                split_re = r"\s+(?=\\[a-zA-Z])"
            else:
                split_re = r"\s+(?=(?:[a-zA-Z(]|\d+[a-zA-Z]))"
            chunks = re.split(split_re, single_line)
            eq_chunks = [c.strip() for c in chunks if c.strip() and "=" in c]
            if len(eq_chunks) >= 2:
                expanded: List[str] = []
                for ch in eq_chunks:
                    expanded.extend(_finalize_latex_step_segments(ch))
                if len(expanded) >= 2:
                    return expanded
            # No whitespace boundaries (e.g. one long LaTeX string): still try glue + chain.
            merged = _finalize_latex_step_segments(single_line)
            if len(merged) >= 2:
                return merged

        # 1b2) Single equation or rare patterns — split by = only when it produces
        # sensible fragments (legacy path; avoid for multi-eq lines handled above).
        if '=' in single_line and single_line.count('=') == 1:
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

        # 1c) Semicolons
        if ';' in single_line:
            parts = [p.strip() for p in single_line.split(';') if p.strip()]
            if len(parts) > 1:
                return parts

        # 1d) "then" / "and" / "next"
        if re.search(r'\s+(then|and|next|after|followed by)\s+', single_line, re.IGNORECASE):
            parts = re.split(r'\s+(?:then|and|next|after|followed by)\s+', single_line, flags=re.IGNORECASE)
            if len(parts) > 1:
                return [p.strip() for p in parts if p.strip()]

        return [single_line] if single_line else []

    # ---- 2) Multiple lines: treat each line as a potential step, merge only when needed ----
    steps = []
    current_step = []

    for line in lines:
        is_new_step = False
        # Explicit step markers
        if re.match(r'^(step\s*\d+|step|solution|answer)\s*:?\s*', line, re.IGNORECASE):
            is_new_step = True
        elif re.match(r'^\(?\d+[\.\)]\s+', line):
            is_new_step = True
        elif line.startswith('='):
            is_new_step = True
        elif re.match(r'^\d+[\.\)]\s+', line):
            is_new_step = True

        if is_new_step and current_step:
            step_text = ' '.join(current_step).strip()
            if step_text:
                steps.append(step_text)
            current_step = [line]
        else:
            # If this line looks like a new equation/step on its own (e.g. LaTeX block or short line after blank), treat as new step
            if current_step and line and re.match(r'^(\$\$|\\\[|\\\(|\d+[\.\)]\s+)', line):
                step_text = ' '.join(current_step).strip()
                if step_text:
                    steps.append(step_text)
                current_step = [line]
            else:
                current_step.append(line)

    if current_step:
        step_text = ' '.join(current_step).strip()
        if step_text:
            steps.append(step_text)

    # ---- 3) If we still have only one step, try double-newline and "one step per line" ----
    if len(steps) <= 1:
        double_newline = [s.strip() for s in text.split('\n\n') if s.strip()]
        if len(double_newline) > 1:
            return double_newline
        # One step per non-empty line (good when student writes one equation per line)
        if len(lines) > 1:
            return lines
        return [text.strip()] if text else []

    return steps


def _ordered_top_level_questions(questions: List[models.Question]) -> List[models.Question]:
    """Parents only, in exam order (by question number)."""
    return sorted(
        (q for q in questions if q.parent_question_id is None),
        key=lambda q: q.number,
    )


def _sorted_subquestions(parent: models.Question) -> List[models.Question]:
    subs = list(parent.sub_questions or [])
    return sorted(subs, key=lambda q: q.number)


def _split_multipart_page_text(page_text: str, sub_count: int) -> List[str]:
    """Split one page into (a), (b), … sections when possible."""
    if sub_count <= 1:
        t = (page_text or "").strip()
        return [t] if t else []
    text = (page_text or "").strip()
    if not text:
        return [""] * sub_count
    pattern = re.compile(r"(?mi)^\s*\(([a-z])\)\s*")
    matches = list(pattern.finditer(text))
    if len(matches) >= sub_count:
        parts: List[str] = []
        for i in range(sub_count):
            start = matches[i].start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            parts.append(text[start:end].strip())
        return parts
    alt = re.compile(r"(?mi)^\s*([a-z])\)\s+")
    matches2 = list(alt.finditer(text))
    if len(matches2) >= sub_count:
        parts = []
        for i in range(sub_count):
            start = matches2[i].start()
            end = matches2[i + 1].start() if i + 1 < len(matches2) else len(text)
            parts.append(text[start:end].strip())
        return parts
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    if len(paras) >= sub_count:
        return paras[:sub_count]
    return [text] + [""] * (sub_count - 1)


def _split_monolithic_solution_text(
    text: str, top_level: List[models.Question]
) -> Optional[List[str]]:
    """
    When one PDF page contains every question, split on headings like
    '1.', '2.', 'Question 3', etc. Returns one chunk per top-level question or None if unreliable.
    """
    ordered = sorted(top_level, key=lambda q: q.number)
    if len(ordered) <= 1:
        return [(text or "").strip()]
    want = {q.number for q in ordered}
    hits: List[Tuple[int, int]] = []
    for m in re.finditer(
        r"(?mi)^\s*(?:question|q\.?)\s*(\d+)\s*[\.\):]\s+",
        text,
    ):
        num = int(m.group(1))
        if num in want:
            hits.append((m.start(), num))
    if len(hits) < 2:
        for m in re.finditer(r"(?mi)^\s*Q\s*(\d+)\s*[\.\):]?\s+", text):
            num = int(m.group(1))
            if num in want:
                hits.append((m.start(), num))
    if len(hits) < 2:
        for m in re.finditer(r"(?mi)^\s*(\d+)\s*[\.\)]\s+\S", text):
            num = int(m.group(1))
            if num in want:
                hits.append((m.start(), num))
    hits.sort(key=lambda x: x[0])
    dedup: List[Tuple[int, int]] = []
    seen_pos: set = set()
    for pos, num in hits:
        if pos in seen_pos:
            continue
        seen_pos.add(pos)
        dedup.append((pos, num))
    hits = dedup
    if len(hits) < 2:
        return None
    by_num: dict = {}
    for i, (pos, num) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        by_num[num] = text[pos:end].strip()
    out: List[str] = []
    for q in ordered:
        out.append(by_num.get(q.number, "").strip())
    if sum(1 for c in out if c) < 2:
        return None
    return out


def _append_typed_for_question(
    extra: List[dict],
    question: models.Question,
    body: str,
) -> None:
    body = (body or "").strip()
    if not body:
        return
    extra.append(
        {
            "questionId": question.id,
            "questionNumber": question.number,
            "typedAnswer": body,
        }
    )


def _process_answer_page_for_top_level_question(
    page_text: str,
    top_q: models.Question,
    pdf_bytes: bytes,
    page_idx: int,
    ocr: OCRProcessor,
    extra_typed_answers: List[dict],
    extra_image_records: List[dict],
) -> None:
    """
    Route one PDF page (or OCR'd text) to the correct leaf questions (sub-parts or parent).
    """
    subs = _sorted_subquestions(top_q)
    if ocr._text_is_clean(page_text):
        if subs:
            chunks = _split_multipart_page_text(page_text, len(subs))
            for sub_q, chunk in zip(subs, chunks):
                _append_typed_for_question(extra_typed_answers, sub_q, chunk)
        else:
            _append_typed_for_question(extra_typed_answers, top_q, page_text)
        return
    try:
        import io as _io
        from pdf2image import convert_from_bytes as _c2b
        from pypdf import PdfReader as _PR, PdfWriter as _PW

        reader = _PR(_io.BytesIO(pdf_bytes))
        if page_idx >= len(reader.pages):
            return
        writer = _PW()
        writer.add_page(reader.pages[page_idx])
        page_buf = _io.BytesIO()
        writer.write(page_buf)
        page_buf.seek(0)
        imgs = _c2b(page_buf.read(), dpi=200)
        if not imgs:
            return
        img_buf = _io.BytesIO()
        imgs[0].save(img_buf, format="PNG")
        png_bytes = img_buf.getvalue()
        ocr_result = ocr.extract_steps_from_file(png_bytes, f"page{page_idx}.png")
        combined = (ocr_result.combined_text or "").strip() or "\n".join(
            s for s in ocr_result.steps if s.strip()
        )
        if subs and combined and len(combined) > 30:
            chunks = _split_multipart_page_text(combined, len(subs))
            for sub_q, chunk in zip(subs, chunks):
                _append_typed_for_question(extra_typed_answers, sub_q, chunk)
            return
        target = subs[0] if subs else top_q
        safe_name = f"q_{target.id}_pdf{page_idx}.png"
        extra_image_records.append({"filename": safe_name, "data": png_bytes})
    except Exception as ex:
        logger.warning("Could not render/scanned PDF page %s: %s", page_idx, ex)


def _ingest_full_answer_pdf(
    pdf_bytes: bytes,
    exam: models.Exam,
    ocr: OCRProcessor,
) -> Tuple[List[dict], List[dict]]:
    """Map PDF pages → top-level exam questions; split multi-part pages onto sub-questions."""
    extra_typed: List[dict] = []
    extra_img: List[dict] = []
    pdf_pages = ocr.extract_pdf_text_pages(pdf_bytes)
    tls = _ordered_top_level_questions(list(exam.questions))
    if not tls:
        return extra_typed, extra_img

    if len(pdf_pages) == 1 and len(tls) > 1:
        sole = pdf_pages[0]
        chunks = _split_monolithic_solution_text(sole, tls)
        if chunks and len(chunks) == len(tls):
            for top_q, chunk in zip(tls, chunks):
                if not (chunk or "").strip():
                    continue
                _process_answer_page_for_top_level_question(
                    chunk, top_q, pdf_bytes, 0, ocr, extra_typed, extra_img
                )
            return extra_typed, extra_img

    for page_idx, top_q in enumerate(tls):
        if page_idx >= len(pdf_pages):
            break
        page_text = pdf_pages[page_idx]
        _process_answer_page_for_top_level_question(
            page_text, top_q, pdf_bytes, page_idx, ocr, extra_typed, extra_img
        )
    return extra_typed, extra_img


def _preview_sub_parts_for_page(
    subs: List[models.Question],
    page_text: str,
    ocr: OCRProcessor,
) -> List[dict]:
    """Describe how one page maps to sub-parts (or single leaf) for UI preview."""
    raw = page_text or ""
    if not subs:
        clean = ocr._text_is_clean(raw)
        st = raw.strip()
        return [
            {
                "part": None,
                "chars": len(st),
                "hasContent": bool(st),
                "delivery": "typed_text" if clean else "ocr_image",
            }
        ]
    if not ocr._text_is_clean(raw):
        return [
            {
                "part": chr(97 + i),
                "chars": None,
                "hasContent": None,
                "delivery": "ocr_image",
            }
            for i in range(len(subs))
        ]
    chunks = _split_multipart_page_text(raw, len(subs))
    out: List[dict] = []
    for i, _sq in enumerate(subs):
        ch = (chunks[i] if i < len(chunks) else "") or ""
        st = ch.strip()
        out.append(
            {
                "part": chr(97 + i),
                "chars": len(st),
                "hasContent": bool(st),
                "delivery": "typed_text",
            }
        )
    return out


def build_answer_pdf_preview(pdf_bytes: bytes, exam: models.Exam, ocr: OCRProcessor) -> dict:
    """
    Dry-run routing for the full-answer PDF (no DB writes). Used by the take-exam UI.
    """
    pdf_pages = ocr.extract_pdf_text_pages(pdf_bytes)
    tls = _ordered_top_level_questions(list(exam.questions))
    n_pages = len(pdf_pages)
    n_tl = len(tls)
    warnings: List[str] = []
    rows: List[dict] = []

    if n_tl == 0:
        return {
            "strategy": "none",
            "pdfPageCount": n_pages,
            "topLevelCount": 0,
            "rows": [],
            "warnings": ["This exam has no questions."],
            "monolithicDetected": False,
            "summary": "No questions to map.",
        }

    if n_pages == 0:
        warnings.append("Could not read any pages from this PDF (corrupt or empty).")
        return {
            "strategy": "empty_pdf",
            "pdfPageCount": 0,
            "topLevelCount": n_tl,
            "rows": [],
            "warnings": warnings,
            "monolithicDetected": False,
            "summary": "No pages detected.",
        }

    if n_pages == 1 and n_tl > 1:
        sole = pdf_pages[0]
        chunks = (
            _split_monolithic_solution_text(sole, tls) if ocr._text_is_clean(sole) else None
        )
        if chunks and len(chunks) == n_tl:
            for top_q, chunk in zip(tls, chunks):
                subs = _sorted_subquestions(top_q)
                rows.append(
                    {
                        "questionNumber": top_q.number,
                        "questionLabel": f"Q{top_q.number}",
                        "source": "single_page_numbered_sections",
                        "subParts": _preview_sub_parts_for_page(subs, chunk, ocr),
                    }
                )
            return {
                "strategy": "monolithic",
                "pdfPageCount": n_pages,
                "topLevelCount": n_tl,
                "rows": rows,
                "warnings": warnings,
                "monolithicDetected": True,
                "summary": f"One PDF page split into {n_tl} main questions via headings (1., Question 2, Q3, …).",
            }

    for page_idx, top_q in enumerate(tls):
        if page_idx >= n_pages:
            rows.append(
                {
                    "questionNumber": top_q.number,
                    "questionLabel": f"Q{top_q.number}",
                    "source": "missing_page",
                    "subParts": [],
                    "note": f"No page {page_idx + 1} in PDF — nothing routed here.",
                }
            )
            continue
        page_text = pdf_pages[page_idx]
        subs = _sorted_subquestions(top_q)
        rows.append(
            {
                "questionNumber": top_q.number,
                "questionLabel": f"Q{top_q.number}",
                "source": f"pdf_page_{page_idx + 1}",
                "subParts": _preview_sub_parts_for_page(subs, page_text, ocr),
            }
        )

    if n_pages > n_tl:
        warnings.append(
            f"{n_pages - n_tl} extra PDF page(s) after page {n_tl} will be ignored."
        )
    if n_pages == 1 and n_tl > 1:
        warnings.append(
            "Single page without clear numbered section headings: only Q1 receives text unless you add headings like “1.” or “Question 2” on new lines, or use one page per question."
        )

    if n_tl == 1:
        summary = f"{n_pages} PDF page(s) → the only main question (Q{tls[0].number})."
    elif n_pages > 1:
        summary = (
            f"{n_pages} PDF page(s) → {n_tl} main questions, in order (page 1 = Q{tls[0].number}, …)."
        )
    else:
        summary = (
            f"1 PDF page → only Q{tls[0].number} received text; use headings or one page per question to cover all {n_tl} questions."
        )

    return {
        "strategy": "per_page",
        "pdfPageCount": n_pages,
        "topLevelCount": n_tl,
        "rows": rows,
        "warnings": warnings,
        "monolithicDetected": False,
        "summary": summary,
    }


def _ingest_multi_page_pdf_attached_to_question(
    pdf_bytes: bytes,
    filename: str,
    exam: models.Exam,
    ocr: OCRProcessor,
) -> Optional[Tuple[List[dict], List[dict]]]:
    """
    Student attached a multi-page PDF under one question slot (filename q_<id>_0.pdf).
    If it looks like a full paper, fan out pages across top-level questions starting at the hinted index.
    """
    stem = Path(filename).stem
    if not stem.startswith("q_"):
        return None
    parts = stem.split("_", 2)
    if len(parts) < 2:
        return None
    hint_qid = parts[1]
    tls = _ordered_top_level_questions(list(exam.questions))
    if not tls:
        return None
    try:
        import io as _io
        from pypdf import PdfReader as _PR

        n_pages = len(_PR(_io.BytesIO(pdf_bytes)).pages)
    except Exception:
        n_pages = len(ocr.extract_pdf_text_pages(pdf_bytes)) or 1
    if n_pages <= 1:
        return None
    start = next((i for i, t in enumerate(tls) if t.id == hint_qid), 0)
    if n_pages == len(tls):
        start = 0
    elif start + n_pages > len(tls):
        return None
    extra_typed: List[dict] = []
    extra_img: List[dict] = []
    pdf_pages = ocr.extract_pdf_text_pages(pdf_bytes)
    for j in range(n_pages):
        qi = start + j
        if qi >= len(tls):
            break
        page_text = pdf_pages[j] if j < len(pdf_pages) else ""
        _process_answer_page_for_top_level_question(
            page_text, tls[qi], pdf_bytes, j, ocr, extra_typed, extra_img
        )
    return (extra_typed, extra_img)


def _ingest_single_page_pdf_as_full_exam_if_detected(
    pdf_bytes: bytes,
    filename: str,
    exam: models.Exam,
    ocr: OCRProcessor,
) -> Optional[Tuple[List[dict], List[dict]]]:
    """
    One-page PDF uploaded under a question slot but containing numbered sections
    for every top-level question (e.g. '1.', '2.', …).
    """
    stem = Path(filename).stem
    if not stem.startswith("q_"):
        return None
    tls = _ordered_top_level_questions(list(exam.questions))
    if len(tls) <= 1:
        return None
    pages = ocr.extract_pdf_text_pages(pdf_bytes)
    if len(pages) != 1:
        return None
    sole = pages[0]
    if not ocr._text_is_clean(sole):
        return None
    chunks = _split_monolithic_solution_text(sole, tls)
    if not chunks or len(chunks) != len(tls):
        return None
    extra_typed: List[dict] = []
    extra_img: List[dict] = []
    for top_q, chunk in zip(tls, chunks):
        if not (chunk or "").strip():
            continue
        _process_answer_page_for_top_level_question(
            chunk, top_q, pdf_bytes, 0, ocr, extra_typed, extra_img
        )
    return (extra_typed, extra_img)


async def grade_submission_automatically(submission_id: str, db: Session):
    """Automatically grade a submission after it's submitted"""
    import json
    import re
    from html import unescape
    
    submission = (
        db.query(models.Submission)
        .options(selectinload(models.Submission.images))
        .filter(models.Submission.id == submission_id)
        .first()
    )
    if not submission:
        return
    
    submission.status = models.SubmissionStatus.GRADING
    db.commit()
    
    exam = db.query(models.Exam).filter(models.Exam.id == submission.exam_id).first()
    questions = exam.questions
    top_level_ordered = _ordered_top_level_questions(list(questions))
    
    total_score = 0.0
    
    has_typed_answers = submission.typed_answers is not None and submission.typed_answers.strip()
    has_images = len(submission.images) > 0
    
    if not has_typed_answers and not has_images:
        submission.status = models.SubmissionStatus.PENDING
        db.commit()
        return
    
    # Track which question IDs have already been graded (to avoid duplicates)
    graded_question_ids: set = set()

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
                steps_for_results = grading_result.get("student_steps_for_storage") or student_steps

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

                # Mark this question as graded so we don't double-count via images
                graded_question_ids.add(question.id)

                # Store step results
                for idx, (student_step, evaluation) in enumerate(
                    zip(steps_for_results, grading_result['evaluations']), start=1
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
                        max_score=_step_result_max_score(evaluation, gold_steps, idx),
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

    # ── Process image uploads with OCR ────────────────────────────────────────
    if has_images:
        for image_record in submission.images:
            try:
                image_path = Path(image_record.image_path)
                if not image_path.exists():
                    continue

                # ── Recover which question this image belongs to ──────────────
                # Filename format written by the frontend: q_{questionId}_{idx}.ext
                question = None
                stem = image_path.stem  # e.g. "q_abc-123_0"
                if stem.startswith('q_'):
                    parts = stem.split('_', 2)  # ['q', questionId, idx]
                    if len(parts) >= 2:
                        candidate_qid = parts[1]
                        question = next(
                            (q for q in questions if q.id == candidate_qid), None
                        )

                # Fallback: match by 1-based page number → top-level questions only
                if question is None:
                    pg = image_record.page_number
                    if 1 <= pg <= len(top_level_ordered):
                        question = top_level_ordered[pg - 1]
                    else:
                        question = top_level_ordered[0] if top_level_ordered else None

                if not question:
                    continue

                # ── Skip if this question already has a typed-answer grade ────
                if question.id in graded_question_ids:
                    logger.info(
                        f"Skipping image for Q{question.number} — already graded via typed answer"
                    )
                    continue

                # ── Run OCR ──────────────────────────────────────────────────
                with open(image_path, "rb") as f:
                    image_bytes = f.read()

                ocr_result = ocr_processor.extract_steps_from_file(
                    image_bytes,
                    image_path.name
                )

                student_steps = ocr_result.steps
                if not student_steps:
                    logger.warning(f"OCR returned no steps for {image_path.name}")
                    continue

                # ── Grade ─────────────────────────────────────────────────────
                gold_steps = []
                for step in question.gold_steps:
                    content = (
                        step.latex if step.latex and step.latex.strip()
                        else (step.expression or '')
                    )
                    if content.strip():
                        gold_steps.append(GraderStep(
                            content=content.strip(),
                            points=float(step.points),
                            required=step.required
                        ))

                if not gold_steps:
                    continue

                grader = HybridGrader(gold_steps, use_ml=True, use_symbolic=True)
                grading_result = grader.grade(student_steps)
                steps_for_results = grading_result.get("student_steps_for_storage") or student_steps

                logger.info(
                    f"OCR grading Q{question.number}: "
                    f"{grading_result['total_score']}/{grading_result['max_score']} "
                    f"({grading_result['percentage']:.1f}%)"
                )

                # ── Store result ──────────────────────────────────────────────
                db_grading_result = models.GradingResult(
                    submission_id=submission.id,
                    question_id=question.id,
                    extracted_text=ocr_result.combined_text or "\n".join(student_steps),
                    extracted_latex=None,
                    score=grading_result['total_score'],
                    max_score=grading_result['max_score'],
                    feedback=f"Auto-graded (handwriting): {grading_result['percentage']:.1f}%",
                    is_correct=grading_result['percentage'] >= 70
                )
                db.add(db_grading_result)
                db.flush()

                graded_question_ids.add(question.id)

                for idx, (student_step, evaluation) in enumerate(
                    zip(steps_for_results, grading_result['evaluations']), start=1
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
                        max_score=_step_result_max_score(evaluation, gold_steps, idx),
                        feedback=evaluation.feedback,
                        expected=matched_gold,
                        received=student_step
                    )
                    db.add(step_result)

                total_score += grading_result['total_score']

            except Exception as e:
                print(f"Error grading image {image_record.image_path}: {e}")
                import traceback
                traceback.print_exc()

    db.flush()
    graded_rows = (
        db.query(models.GradingResult)
        .filter(models.GradingResult.submission_id == submission.id)
        .count()
    )
    if graded_rows == 0:
        submission.status = models.SubmissionStatus.PENDING
        submission.total_score = None
        submission.graded_at = None
    else:
        submission.total_score = total_score
        submission.graded_at = datetime.utcnow()
        submission.status = models.SubmissionStatus.AWAITING_APPROVAL
    db.commit()


@app.post("/api/submissions")
async def submit_exam(
    exam_id: str = Form(...),
    images: List[UploadFile] = File(default=[]),
    answers: Optional[str] = Form(None),
    answer_pdf: Optional[UploadFile] = File(default=None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit an exam with optional image uploads, typed answers, or a full-exam answer PDF."""
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if not images and not answers and not answer_pdf:
        raise HTTPException(
            status_code=400,
            detail="At least one submission method (typed answers, images, or answer PDF) is required"
        )

    # ── Process full-exam answer PDF ─────────────────────────────────────────
    # Pages map to top-level questions only (Q1, Q2, …). Multi-part questions
    # get (a)(b) splits onto sub-question rows. Single-page “wall of solutions”
    # PDFs are split on headings like "1.", "Question 2", etc. when detected.
    extra_typed_answers: list = []      # [{questionId, questionNumber, typedAnswer}]
    extra_image_records: list = []      # [{filename, bytes}]  for scanned pages

    if answer_pdf and answer_pdf.filename:
        try:
            pdf_bytes = await answer_pdf.read()
            t_extra, img_extra = _ingest_full_answer_pdf(
                pdf_bytes, exam, ocr_processor
            )
            extra_typed_answers.extend(t_extra)
            extra_image_records.extend(img_extra)
        except Exception as e:
            logger.exception("Failed to process answer PDF: %s", e)

    # ── Fan out mistaken multi-page (or monolithic single-page) PDFs on one slot ─
    skip_upload_indices: set = set()
    image_payloads: List[Tuple[int, bytes, str]] = []
    for i, uf in enumerate(images):
        try:
            raw = await uf.read()
        except Exception as ex:
            logger.warning("Could not read upload %s: %s", uf.filename, ex)
            continue
        image_payloads.append((i, raw, uf.filename or f"upload_{i}"))

    for i, raw, fname in image_payloads:
        if not (fname or "").lower().endswith(".pdf"):
            continue
        try:
            expanded = _ingest_multi_page_pdf_attached_to_question(
                raw, fname, exam, ocr_processor
            )
            if not expanded:
                expanded = _ingest_single_page_pdf_as_full_exam_if_detected(
                    raw, fname, exam, ocr_processor
                )
            if expanded:
                t2, img2 = expanded
                extra_typed_answers.extend(t2)
                extra_image_records.extend(img2)
                skip_upload_indices.add(i)
        except Exception as ex:
            logger.warning("PDF expansion skipped for %s: %s", fname, ex)

    # ── Merge typed answers ───────────────────────────────────────────────────
    merged_answers = extra_typed_answers[:]
    if answers:
        try:
            import json as _json
            existing = _json.loads(answers)
            # Existing typed answers take precedence (student typed them manually)
            existing_qids = {a.get('questionId') for a in existing}
            for ea in extra_typed_answers:
                if ea['questionId'] not in existing_qids:
                    existing.append(ea)
            merged_answers = existing
        except Exception:
            merged_answers = extra_typed_answers

    merged_answers_json = None
    if merged_answers:
        import json as _json
        merged_answers_json = _json.dumps(merged_answers)
    elif answers:
        merged_answers_json = answers

    # ── Create submission record ──────────────────────────────────────────────
    new_submission = models.Submission(
        exam_id=exam_id,
        student_id=current_user.id,
        status=models.SubmissionStatus.PENDING,
        max_score=exam.total_points,
        typed_answers=merged_answers_json
    )
    db.add(new_submission)
    db.flush()

    submission_dir = UPLOAD_DIR / new_submission.id

    # ── Save per-question image uploads (bytes pre-read; PDFs may be skipped) ─
    if image_payloads or extra_image_records:
        submission_dir.mkdir(exist_ok=True)

        page_seq = 0
        for i, raw, original_name in image_payloads:
            if i in skip_upload_indices:
                continue
            page_seq += 1
            safe_name = Path(original_name).name or f"page_{page_seq}.jpg"
            image_path = submission_dir / safe_name
            image_path.write_bytes(raw)

            submission_image = models.SubmissionImage(
                submission_id=new_submission.id,
                image_path=str(image_path),
                page_number=page_seq,
            )
            db.add(submission_image)

        base_count = page_seq
        for rec_idx, rec in enumerate(extra_image_records):
            image_path = submission_dir / rec["filename"]
            with open(image_path, "wb") as f:
                f.write(rec["data"])
            submission_image = models.SubmissionImage(
                submission_id=new_submission.id,
                image_path=str(image_path),
                page_number=base_count + rec_idx + 1,
            )
            db.add(submission_image)
    
    db.commit()
    db.refresh(new_submission)
    
    # Automatically trigger AI grading (same path as manual "Auto-grade")
    try:
        await grade_submission_automatically(new_submission.id, db)
    except Exception:
        logger.exception("Auto-grading failed after submit for submission %s", new_submission.id)
    
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
    
    show_grading = _include_grading_in_submission_payload

    for submission in submissions:
        # Get student info
        student = db.query(models.User).filter(models.User.id == submission.student_id).first()
        
        # Get exam to access questions
        exam = db.query(models.Exam).filter(models.Exam.id == submission.exam_id).first()
        questions_by_id = {q.id: q for q in exam.questions} if exam else {}
        _show_grading = show_grading(submission, current_user)
        
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
                    ) if _show_grading else None
                )
            )
        
        _merge_typed_answers_into_responses(
            answers, submission.typed_answers, questions_by_id, graded_question_ids
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
                totalScore=_submission_total_score_for_api(submission, current_user, _show_grading),
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
    _show_grading = _include_grading_in_submission_payload(submission, current_user)
    
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
                ) if _show_grading else None
            )
        )
    
    _merge_typed_answers_into_responses(
        answers, submission.typed_answers, questions_by_id, graded_question_ids
    )

    return schemas.SubmissionResponse(
        id=submission.id,
        examId=submission.exam_id,
        studentId=submission.student_id,
        studentName=student.name if student else "Unknown",
        submittedAt=submission.submitted_at,
        status=submission.status,
        answers=answers,
        totalScore=_submission_total_score_for_api(submission, current_user, _show_grading),
        maxScore=submission.max_score
    )


@app.get("/api/submissions/{submission_id}/marked-pdf")
async def download_marked_submission_pdf(
    submission_id: str,
    paper: str = "letter",
    include_reference_solutions: bool = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    PDF: exam questions, student responses, scores and step feedback.
    Optional `include_reference_solutions=true` (professors/admins only) appends model answers.
    `paper=a4|letter|legal`
    """
    from io import BytesIO
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from fastapi.responses import StreamingResponse

    submission = (
        db.query(models.Submission)
        .options(
            selectinload(models.Submission.grading_results).selectinload(
                models.GradingResult.step_results
            ),
        )
        .filter(models.Submission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    exam = (
        db.query(models.Exam)
        .options(
            selectinload(models.Exam.questions).selectinload(models.Question.attachments),
            selectinload(models.Exam.questions).selectinload(models.Question.gold_steps),
        )
        .filter(models.Exam.id == submission.exam_id)
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    course = db.query(models.Course).filter(models.Course.id == exam.course_id).first()
    student = db.query(models.User).filter(models.User.id == submission.student_id).first()

    # Access control (same idea as get_submission + course ownership for professors)
    if current_user.role == models.UserRole.STUDENT:
        if submission.student_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.role == models.UserRole.PROFESSOR:
        if not course or course.professor_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    # ADMIN: allowed

    allow_ref = include_reference_solutions and current_user.role in (
        models.UserRole.PROFESSOR,
        models.UserRole.ADMIN,
    )
    if include_reference_solutions and not allow_ref:
        include_reference_solutions = False

    st_val = (
        submission.status.value
        if isinstance(submission.status, models.SubmissionStatus)
        else str(submission.status or "")
    )
    # Students only get the marked PDF after the instructor approves (published grades)
    if current_user.role == models.UserRole.STUDENT and st_val != models.SubmissionStatus.APPROVED.value:
        raise HTTPException(
            status_code=403,
            detail="Marked PDF is available after your instructor approves and publishes your grade.",
        )

    by_qid = {gr.question_id: gr for gr in submission.grading_results}
    typed_map = _typed_answers_by_question_id(submission)

    buffer = BytesIO()
    pagesize = _pdf_pagesize(paper)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "MarkedTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor="black",
        spaceAfter=24,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        "MarkedHeading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor="black",
        spaceAfter=10,
    )
    normal_style = styles["Normal"]
    sub_style = ParagraphStyle("MarkedSub", parent=normal_style, fontSize=10, spaceAfter=4)
    banner_style = ParagraphStyle(
        "MarkedBanner",
        parent=normal_style,
        fontSize=10,
        textColor="white",
        backColor=(0.35, 0.22, 0.55),
        borderPadding=6,
        spaceAfter=12,
        alignment=TA_CENTER,
    )

    story = []
    story.append(Paragraph("MARKED SUBMISSION REPORT", banner_style))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(_pdf_safe_text(exam.title), title_style))
    story.append(Spacer(1, 0.15 * inch))
    if course:
        story.append(Paragraph(f"<b>Course:</b> {_pdf_safe_text(course.name)}", normal_style))
    story.append(
        Paragraph(
            f"<b>Student:</b> {_pdf_safe_text(student.name if student else 'Unknown')}",
            normal_style,
        )
    )
    story.append(
        Paragraph(
            f"<b>Submitted:</b> {submission.submitted_at.strftime('%Y-%m-%d %H:%M')}",
            normal_style,
        )
    )
    story.append(
        Paragraph(
            f"<b>Status:</b> {_pdf_safe_text(st_val)}",
            normal_style,
        )
    )
    if submission.total_score is not None:
        story.append(
            Paragraph(
                f"<b>Total score:</b> {_pdf_safe_text(str(submission.total_score))} / "
                f"{_pdf_safe_text(str(submission.max_score))} pts",
                normal_style,
            )
        )
    story.append(Spacer(1, 0.35 * inch))

    sub_style_tree = ParagraphStyle("MarkedSubQ", parent=normal_style, leftIndent=18, spaceAfter=2)
    sub_heading_tree = ParagraphStyle(
        "MarkedSubQH", parent=heading_style, leftIndent=18, fontSize=11
    )

    alphabet = "abcdefghijklmnopqrstuvwxyz"
    tree = _build_question_tree(exam.questions)
    if not exam.questions:
        story.append(Paragraph("No questions on this exam.", normal_style))
    else:
        for q_num, (top_q, subs) in enumerate(tree, 1):
            gr = by_qid.get(top_q.id)
            typed_fb = typed_map.get(top_q.id, "")
            _append_marked_response_block(
                top_q,
                story,
                f"Question {q_num}",
                gr,
                typed_fb,
                normal_style,
                heading_style,
                sub_style,
                inch,
                UPLOAD_DIR,
                allow_ref,
            )
            for s_num, sub_q in enumerate(subs):
                letter = alphabet[s_num] if s_num < len(alphabet) else str(s_num + 1)
                grs = by_qid.get(sub_q.id)
                tf = typed_map.get(sub_q.id, "")
                _append_marked_response_block(
                    sub_q,
                    story,
                    f"Question {q_num} ({letter})",
                    grs,
                    tf,
                    sub_style_tree,
                    sub_heading_tree,
                    sub_style_tree,
                    inch,
                    UPLOAD_DIR,
                    allow_ref,
                )

    try:
        doc.build(story)
        buffer.seek(0)
    except Exception as e:
        logger.error(f"Marked submission PDF failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

    safe_student = _pdf_safe_text(student.name if student else "student").replace(" ", "_")[:40]
    safe_exam = _pdf_safe_text(exam.title).replace(" ", "_").replace("/", "_")[:60]
    fname = f"marked_{safe_exam}_{safe_student}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"',
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
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
    top_level_ordered = _ordered_top_level_questions(list(questions))
    
    total_score = 0.0
    
    # Check if there are typed answers
    has_typed_answers = submission.typed_answers is not None and submission.typed_answers.strip()
    has_images = len(submission.images) > 0
    
    if not has_typed_answers and not has_images:
        raise HTTPException(status_code=400, detail="No answers found for submission (neither typed nor images)")
    
    # Track questions already graded (e.g. from typed answers) to avoid double-counting when we also have images
    graded_question_ids: set = set()
    
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
                steps_for_results = grading_result.get("student_steps_for_storage") or student_steps
                
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
                    zip(steps_for_results, grading_result['evaluations']), start=1
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
                        max_score=_step_result_max_score(evaluation, gold_steps, idx),
                        feedback=evaluation.feedback,
                        expected=matched_gold,
                        received=student_step
                    )
                    db.add(step_result)
                
                total_score += grading_result['total_score']
                graded_question_ids.add(question.id)
                
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
            if not student_steps:
                continue

            stem = image_path.stem
            question = None
            if stem.startswith("q_"):
                parts = stem.split("_", 2)
                if len(parts) >= 2:
                    candidate_qid = parts[1]
                    question = next(
                        (q for q in questions if q.id == candidate_qid), None
                    )
            if question is None:
                pg = image.page_number
                if 1 <= pg <= len(top_level_ordered):
                    question = top_level_ordered[pg - 1]
                else:
                    question = top_level_ordered[0] if top_level_ordered else None

            if not question or question.id in graded_question_ids:
                continue

            # Get gold solution steps
            gold_steps = [
                GraderStep(
                    content=(
                        (step.latex if step.latex and step.latex.strip() else step.expression)
                        or ""
                    ).strip(),
                    points=float(step.points),
                    required=step.required,
                )
                for step in question.gold_steps
                if (step.latex and step.latex.strip()) or (step.expression and step.expression.strip())
            ]

            if not gold_steps:
                continue

            grader = HybridGrader(gold_steps, use_ml=True, use_symbolic=True)
            grading_result = grader.grade(student_steps)
            steps_for_results = grading_result.get("student_steps_for_storage") or student_steps

            # Store grading result
            db_grading_result = models.GradingResult(
                submission_id=submission.id,
                question_id=question.id,
                extracted_text="\n".join(student_steps),
                extracted_latex=None,
                score=grading_result['total_score'],
                max_score=grading_result['max_score'],
                feedback=f"Scored {grading_result['percentage']:.1f}%",
                is_correct=grading_result['percentage'] >= 70
            )
            db.add(db_grading_result)
            db.flush()

            # Store step results
            for idx, (student_step, evaluation) in enumerate(
                zip(steps_for_results, grading_result['evaluations']), start=1
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
                    max_score=_step_result_max_score(evaluation, gold_steps, idx),
                    feedback=evaluation.feedback,
                    expected=matched_gold,
                    received=student_step
                )
                db.add(step_result)

            total_score += grading_result['total_score']
            graded_question_ids.add(question.id)
    
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
    
    if submission.status == models.SubmissionStatus.PENDING:
        if not submission.grading_results:
            raise HTTPException(
                status_code=400,
                detail="Nothing to approve — run grading or add scores first",
            )
    elif submission.status not in (
        models.SubmissionStatus.AWAITING_APPROVAL,
        models.SubmissionStatus.GRADED,
    ):
        raise HTTPException(status_code=400, detail="Submission cannot be approved in its current state")

    if submission.total_score is None and submission.grading_results:
        submission.total_score = float(sum(gr.score for gr in submission.grading_results))
    if submission.graded_at is None:
        submission.graded_at = datetime.utcnow()

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
    """
    Return submission to pending: student no longer sees scores until re-approved.
    Grading rows (OCR text, steps, draft scores) are kept so instructors can review
    the same attempt and adjust grades or ask the student to resubmit.
    """
    if current_user.role not in [models.UserRole.PROFESSOR, models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only professors can reject submissions")
    
    submission = db.query(models.Submission).filter(
        models.Submission.id == submission_id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    rejectable = {
        models.SubmissionStatus.AWAITING_APPROVAL,
        models.SubmissionStatus.GRADED,
        models.SubmissionStatus.APPROVED,
    }
    if submission.status not in rejectable:
        raise HTTPException(status_code=400, detail="Submission cannot be rejected in its current state")

    submission.status = models.SubmissionStatus.PENDING
    submission.total_score = None
    submission.graded_at = None
    submission.approved_at = None
    submission.approved_by = None

    db.commit()

    return {
        "status": "success",
        "message": "Submission returned for review. The student no longer sees grades until you approve. You can still view their work and edit scores below.",
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


def _extract_text_from_rich_content(rich_content) -> str:
    """
    Recursively extract plain text from TipTap JSON (richContent).
    Handles text nodes, math nodes (blockMath / inlineMath), paragraphs, lists, etc.
    Returns a human-readable string suitable for PDF output.
    """
    if not rich_content:
        return ""
    if isinstance(rich_content, str):
        try:
            import json as _json
            rich_content = _json.loads(rich_content)
        except Exception:
            return rich_content

    _PLACEHOLDER = "[Question text could not be displayed"

    def _node_text(node) -> str:
        if not isinstance(node, dict):
            return ""
        ntype = node.get("type", "")
        # Plain text leaf — skip injected placeholder messages
        if ntype == "text":
            t = node.get("text", "")
            if t.startswith(_PLACEHOLDER):
                return ""
            return t
        # Math nodes — show latex in brackets so it's human-readable in PDF
        if ntype in ("blockMath", "mathBlock"):
            latex = node.get("attrs", {}).get("latex", "")
            return f"\n[{latex}]\n" if latex else ""
        if ntype in ("inlineMath", "mathInline"):
            latex = node.get("attrs", {}).get("latex", "")
            return f"[{latex}]" if latex else ""
        # Recurse into children
        parts = []
        children = node.get("content") or []
        for child in children:
            parts.append(_node_text(child))
        text = "".join(parts)
        # Add line breaks after block-level nodes
        if ntype in ("paragraph", "heading", "listItem", "blockquote"):
            text = text + "\n"
        if ntype in ("bulletList", "orderedList"):
            text = text + "\n"
        return text

    return _node_text(rich_content).strip()


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


def _pdf_pagesize(paper: str):
    """ReportLab page size tuple for exam PDFs. `paper`: a4, letter, legal (case-insensitive)."""
    from reportlab.lib.pagesizes import letter, A4, legal
    key = (paper or "letter").lower().strip()
    if key == "a4":
        return A4
    if key == "legal":
        return legal
    return letter


def _strip_html_to_plain(s: str) -> str:
    """Strip tags for PDF text; preserve line breaks from block elements."""
    import re
    from html import unescape
    if not s or not isinstance(s, str):
        return ""
    t = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    t = re.sub(r"</p\s*>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


def _typed_answers_by_question_id(submission) -> dict:
    """Map question_id -> plain text from stored JSON typed answers."""
    import json
    raw = getattr(submission, "typed_answers", None)
    if not raw:
        return {}
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        out = {}
        for a in data or []:
            qid = a.get("questionId")
            if qid:
                out[qid] = _strip_html_to_plain(a.get("typedAnswer", "") or "")
        return out
    except Exception:
        return {}


def _append_question_stem_to_story(q, story, q_label, normal_style, heading_style, sub_style, inch, UPLOAD_DIR):
    """Question heading + rich/plain text + image attachments (no answer area)."""
    import json as _json
    from reportlab.platypus import Paragraph, Spacer, Image as RLImage
    from reportlab.lib.utils import ImageReader

    pts = getattr(q, "points", 0)
    story.append(Paragraph(f"<b>{_pdf_safe_text(q_label)} ({pts} pts)</b>", heading_style))

    rich = getattr(q, "rich_content", None)
    if rich:
        try:
            rc = _json.loads(rich) if isinstance(rich, str) else rich
            rich_elements = _rich_content_to_story_elements(
                rc, normal_style, sub_style, inch, upload_dir=UPLOAD_DIR
            )
            story.extend(rich_elements)
        except Exception as _e:
            logger.warning(f"Marked PDF rich content error: {_e}")
            fallback = getattr(q, "text", "") or ""
            if fallback:
                story.append(Paragraph(_pdf_safe_text(fallback[:2000]), normal_style))
    else:
        plain = getattr(q, "text", "") or ""
        if plain:
            story.append(Paragraph(_pdf_safe_text(plain[:2000]), normal_style))

    for att in getattr(q, "attachments", []) or []:
        if getattr(att, "attachment_type", "") != "image":
            continue
        path = UPLOAD_DIR / att.file_path
        if path.exists():
            try:
                reader = ImageReader(str(path))
                iw, ih = reader.getSize()
                if iw > 0 and ih > 0:
                    aspect = ih / float(iw)
                    max_w = 5.2 * inch
                    w, h = max_w, max_w * aspect
                    if h > 5 * inch:
                        h = 5 * inch
                        w = h / aspect
                    story.append(Spacer(1, 0.1 * inch))
                    story.append(RLImage(str(path), width=w, height=h))
                    story.append(Spacer(1, 0.1 * inch))
            except Exception as e:
                logger.warning(f"Marked PDF attachment skipped: {e}")


def _append_reference_solution_only(q, story, sub_style, inch):
    """Append instructor reference solution (gold steps + final answer) to story."""
    import re as _re_q
    from reportlab.platypus import Paragraph, Spacer

    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph("<b>Reference solution (instructor)</b>", sub_style))
    story.append(Spacer(1, 0.06 * inch))
    gold_steps = list(getattr(q, "gold_steps", []) or [])
    if gold_steps:
        story.append(Paragraph("<i>Model steps:</i>", sub_style))
        for idx, gs in enumerate(sorted(gold_steps, key=lambda x: getattr(x, "step_number", 0)), 1):
            step_text = _pdf_safe_text(_clean_step_for_pdf(gs))
            if step_text:
                story.append(Paragraph(f"{idx}. {step_text}", sub_style))
        final_lat = getattr(q, "final_answer_latex", None) or getattr(q, "final_answer", None)
        if final_lat and str(final_lat).strip():
            fa = _re_q.sub(r"\$\$?(.*?)\$\$?", r"\1", str(final_lat), flags=_re_q.DOTALL).strip()
            if fa:
                fa_img = _render_latex_to_flowable(fa, inch, max_width_inch=3.0)
                if fa_img:
                    story.append(Paragraph("<b>Final Answer:</b>", sub_style))
                    story.append(fa_img)
                else:
                    story.append(Paragraph(f"<b>Final Answer:</b> {_pdf_safe_text(fa)}", sub_style))
    else:
        final_ans = getattr(q, "final_answer_latex", None) or getattr(q, "final_answer", None)
        if final_ans and str(final_ans).strip():
            fa = _re_q.sub(r"\$\$?(.*?)\$\$?", r"\1", str(final_ans), flags=_re_q.DOTALL).strip()
            fa_img = _render_latex_to_flowable(fa, inch, max_width_inch=3.0)
            if fa_img:
                story.append(Paragraph("<b>Final Answer:</b>", sub_style))
                story.append(fa_img)
            else:
                story.append(Paragraph(f"<b>Final Answer:</b> {_pdf_safe_text(fa)}", sub_style))
        else:
            story.append(Paragraph("<i>No reference solution stored.</i>", sub_style))


def _append_marked_response_block(
    q,
    story,
    q_label,
    grading_result,
    typed_fallback_plain: str,
    normal_style,
    heading_style,
    sub_style,
    inch,
    UPLOAD_DIR,
    include_reference_solutions: bool,
):
    """One question: stem, student work, scores/feedback, optional reference solution."""
    from reportlab.platypus import Paragraph, Spacer, Table as RLTable, TableStyle
    from reportlab.lib import colors as _colors

    _append_question_stem_to_story(
        q, story, q_label, normal_style, heading_style, sub_style, inch, UPLOAD_DIR
    )

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("<b>Student response</b>", sub_style))
    story.append(Spacer(1, 0.06 * inch))

    answer_plain = ""
    if grading_result:
        ext = grading_result.extracted_text or ""
        if ext.strip():
            answer_plain = _strip_html_to_plain(ext) or _pdf_safe_text(ext[:4000])
        elif grading_result.extracted_latex:
            answer_plain = _pdf_safe_text(str(grading_result.extracted_latex))
    if not answer_plain.strip() and typed_fallback_plain:
        answer_plain = _pdf_safe_text(typed_fallback_plain[:4000])

    if answer_plain.strip():
        for chunk in [answer_plain[i : i + 900] for i in range(0, len(answer_plain), 900)]:
            story.append(Paragraph(_pdf_safe_text(chunk), normal_style))
    else:
        story.append(Paragraph("<i>No submitted work captured for this question.</i>", sub_style))

    story.append(Spacer(1, 0.12 * inch))

    if grading_result:
        sc = grading_result.score
        mx = grading_result.max_score
        ok = getattr(grading_result, "is_correct", False)
        status_word = "Correct" if ok else "See feedback"
        story.append(
            Paragraph(
                f"<b>Score:</b> {_pdf_safe_text(str(sc))} / {_pdf_safe_text(str(mx))} pts "
                f" | <b>Status:</b> {_pdf_safe_text(status_word)}",
                sub_style,
            )
        )
        fb = grading_result.feedback or ""
        if fb.strip():
            story.append(Spacer(1, 0.05 * inch))
            story.append(Paragraph(f"<b>Feedback:</b> {_pdf_safe_text(fb[:1500])}", normal_style))

        steps = list(grading_result.step_results or [])
        if steps:
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph("<b>Step breakdown</b>", sub_style))
            hdr = [
                Paragraph("<b>Step</b>", sub_style),
                Paragraph("<b>OK</b>", sub_style),
                Paragraph("<b>Points</b>", sub_style),
                Paragraph("<b>Notes</b>", sub_style),
            ]
            rows = [hdr]
            for st in sorted(steps, key=lambda x: x.step_number):
                yn = "Yes" if st.is_correct else "No"
                pts = f"{float(st.score):.2f}".rstrip("0").rstrip(".") + f"/{int(st.max_score)}"
                note = (st.feedback or "")[:220]
                rows.append(
                    [
                        Paragraph(str(st.step_number), normal_style),
                        Paragraph(_pdf_safe_text(yn), normal_style),
                        Paragraph(_pdf_safe_text(pts), normal_style),
                        Paragraph(_pdf_safe_text(note), normal_style),
                    ]
                )
            tw = 5.2 * inch
            c1, c2, c3 = 0.5 * inch, 0.55 * inch, 0.85 * inch
            col_w = [c1, c2, c3, tw - c1 - c2 - c3]
            tbl = RLTable(rows, colWidths=col_w, repeatRows=1)
            tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), _colors.Color(0.9, 0.9, 0.95)),
                        ("GRID", (0, 0), (-1, -1), 0.5, _colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(Spacer(1, 0.06 * inch))
            story.append(tbl)
    else:
        story.append(Paragraph("<i>Not auto-graded yet (no grading record).</i>", sub_style))

    if include_reference_solutions:
        _append_reference_solution_only(q, story, sub_style, inch)

    story.append(Spacer(1, 0.28 * inch))


def _render_latex_to_flowable(latex_str, inch, max_width_inch=5.2, fontsize=12):
    """
    Render a LaTeX math string to a ReportLab Image flowable using matplotlib mathtext.
    Returns the flowable, or None on failure (caller can fall back to plain text).
    """
    import io as _io
    import re as _re
    if not latex_str or not str(latex_str).strip():
        return None
    latex_str = str(latex_str).strip()
    # Normalize for mathtext: wrap in $ $ and replace common unicode
    s = latex_str
    s = s.replace("\u221e", "\\infty").replace("\u00b1", "\\pm")
    s = s.replace("\u00d7", "\\times").replace("\u00f7", "\\div")
    if not s.startswith("$"):
        s = "$" + s + "$"
    try:
        from matplotlib.mathtext import math_to_image
        from reportlab.platypus import Image as RLImage
        from reportlab.lib.utils import ImageReader
        buf = _io.BytesIO()
        math_to_image(s, buf, dpi=150, format="png")
        buf.seek(0)
        reader = ImageReader(buf)
        iw, ih = reader.getSize()
        if iw <= 0 or ih <= 0:
            return None
        dpi = 150
        w_pt = iw * 72 / dpi
        h_pt = ih * 72 / dpi
        max_pt = max_width_inch * 72
        scale = min(1.0, max_pt / w_pt)
        w_pt *= scale
        h_pt *= scale
        buf.seek(0)
        return RLImage(buf, width=w_pt, height=h_pt)
    except Exception as e:
        logger.warning(f"PDF LaTeX render failed ({latex_str[:50]}...): {e}")
        return None


def _build_question_tree(questions):
    """
    Given a flat list of Question ORM objects, return a list of
    (top_question, [sub_questions_in_order]) tuples, sorted by question number.
    Sub-questions are those with a non-None parent_question_id.
    """
    top = [q for q in questions if not getattr(q, 'parent_question_id', None)]
    by_parent = {}
    for q in questions:
        pid = getattr(q, 'parent_question_id', None)
        if pid:
            by_parent.setdefault(pid, []).append(q)
    result = []
    for tq in sorted(top, key=lambda q: getattr(q, 'number', 0)):
        subs = sorted(by_parent.get(tq.id, []), key=lambda q: getattr(q, 'number', 0))
        result.append((tq, subs))
    return result


def _rich_content_to_story_elements(rich_content, normal_style, sub_style, inch, upload_dir=None):
    """
    Walk TipTap JSON and return a list of ReportLab flowable objects.
    Handles: paragraphs, headings, bullet/ordered lists, blockquotes,
             math nodes (inline + block), images (base64 + URL), tables.
    upload_dir: Path object pointing to the uploads folder on disk (for resolving URLs).
    """
    import io as _io, base64 as _b64, json as _json
    from reportlab.platypus import Paragraph, Spacer, Image as RLImage, Table as RLTable, TableStyle
    from reportlab.lib import colors as _colors
    from reportlab.lib.utils import ImageReader
    from urllib.parse import urlparse as _urlparse

    _PLACEHOLDER_PREFIX = "[Question text could not be displayed"

    if not rich_content:
        return []
    if isinstance(rich_content, str):
        try:
            rich_content = _json.loads(rich_content)
        except Exception:
            return [Paragraph(rich_content[:500], normal_style)]

    def _xs(text: str) -> str:
        """XML-safe escape for ReportLab Paragraph markup."""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _inline(node) -> str:
        """Recursively convert an inline node (text, marks, math) to ReportLab markup string."""
        if not isinstance(node, dict):
            return ""
        ntype = node.get("type", "")
        if ntype == "text":
            raw = node.get("text", "")
            if raw.startswith(_PLACEHOLDER_PREFIX):
                return ""
            safe = _xs(raw)
            for mark in node.get("marks") or []:
                mt = mark.get("type", "")
                if mt == "bold":
                    safe = f"<b>{safe}</b>"
                elif mt == "italic":
                    safe = f"<i>{safe}</i>"
                elif mt == "underline":
                    safe = f"<u>{safe}</u>"
                elif mt == "strike":
                    safe = f"<strike>{safe}</strike>"
                elif mt == "code":
                    safe = f"<font face='Courier'>{safe}</font>"
            return safe
        if ntype in ("inlineMath", "mathInline"):
            latex = node.get("attrs", {}).get("latex", "")
            return f"<i>[{_xs(latex)}]</i>" if latex else ""
        # Fallback: recurse children as inline
        return "".join(_inline(c) for c in node.get("content") or [])

    def _paragraph_segments(children):
        """Return list of ('text', markup_str) and ('math', latex_str) for inline math rendering."""
        segs = []
        for c in children or []:
            if not isinstance(c, dict):
                continue
            ntype = c.get("type", "")
            if ntype == "text":
                raw = c.get("text", "")
                if raw.startswith(_PLACEHOLDER_PREFIX):
                    continue
                safe = _xs(raw)
                for mark in c.get("marks") or []:
                    mt = mark.get("type", "")
                    if mt == "bold":
                        safe = f"<b>{safe}</b>"
                    elif mt == "italic":
                        safe = f"<i>{safe}</i>"
                    elif mt == "underline":
                        safe = f"<u>{safe}</u>"
                    elif mt == "strike":
                        safe = f"<strike>{safe}</strike>"
                    elif mt == "code":
                        safe = f"<font face='Courier'>{safe}</font>"
                if segs and segs[-1][0] == "text":
                    segs[-1] = ("text", segs[-1][1] + safe)
                else:
                    segs.append(("text", safe))
            elif ntype in ("inlineMath", "mathInline"):
                latex = c.get("attrs", {}).get("latex", "")
                if latex:
                    segs.append(("math", latex))
            else:
                # Recurse (e.g. nested content)
                sub = _paragraph_segments(c.get("content") or [])
                for kind, val in sub:
                    if kind == "text" and segs and segs[-1][0] == "text":
                        segs[-1] = ("text", segs[-1][1] + val)
                    else:
                        segs.append((kind, val))
        return segs

    def _paragraph_flowables(children, style, wrap_bold=False, prefix=""):
        """Build one or more flowables for a paragraph, rendering inline math as images."""
        segs = _paragraph_segments(children)
        if not segs:
            return []
        if prefix and segs and segs[0][0] == "text":
            segs = [("text", prefix + segs[0][1])] + segs[1:]
        math_flowables = []
        for kind, val in segs:
            if kind == "math":
                fl = _render_latex_to_flowable(val, inch, max_width_inch=1.8)
                math_flowables.append(fl if fl else Paragraph(f"<i>[{_xs(val)}]</i>", style))
            else:
                math_flowables.append(None)  # text handled below
        # Build list of flowables: Paragraph for text runs, Image/Paragraph for math
        flowables = []
        text_run = []
        for i, (kind, val) in enumerate(segs):
            if kind == "text":
                text_run.append(val)
            else:
                if text_run:
                    markup = ("<b>" if wrap_bold else "") + "".join(text_run) + ("</b>" if wrap_bold else "")
                    flowables.append(Paragraph(markup, style))
                    text_run = []
                flowables.append(math_flowables[i])
        if text_run:
            markup = ("<b>" if wrap_bold else "") + "".join(text_run) + ("</b>" if wrap_bold else "")
            flowables.append(Paragraph(markup, style))
        if not flowables:
            return []
        if len(flowables) == 1:
            return [flowables[0]]
        # One row table so text and math sit on same line
        from reportlab.platypus import Table as RLTable, TableStyle
        col_w = (5.2 * 72) / len(flowables)  # points
        t = RLTable([flowables], colWidths=[col_w] * len(flowables))
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        return [t]

    def _image_flowable(src: str):
        """Turn an image src (base64 data URL or server URL) into an RLImage, or None."""
        import re as _re_img
        try:
            buf = None

            if src.startswith("data:image"):
                # ── Base64 embedded image ──
                if "svg" in src[:30].lower():
                    # ReportLab cannot render SVG natively; skip silently
                    return None
                _, data = src.split(",", 1)
                buf = _io.BytesIO(_b64.b64decode(data))

            else:
                # ── URL image ──
                parsed = _urlparse(src)
                url_path = parsed.path  # e.g. /api/attachments/{id}/file

                local_file = None

                # Pattern 1: /api/attachments/{uuid}/file  →  look up DB to get file_path
                m = _re_img.search(r'/api/attachments/([^/]+)/file', url_path)
                if m:
                    att_id = m.group(1)
                    try:
                        from database import SessionLocal as _SL
                        _db = _SL()
                        try:
                            att = _db.query(models.QuestionAttachment).filter(
                                models.QuestionAttachment.id == att_id
                            ).first()
                            if att and att.file_path and upload_dir is not None:
                                local_file = upload_dir / att.file_path
                        finally:
                            _db.close()
                    except Exception as db_err:
                        logger.warning(f"PDF: DB lookup failed for attachment {att_id}: {db_err}")

                # Pattern 2: /uploads/... direct path
                if local_file is None and upload_dir is not None:
                    uploads_prefix = "/uploads/"
                    if url_path.startswith(uploads_prefix):
                        local_file = upload_dir / url_path[len(uploads_prefix):]

                if local_file and local_file.exists():
                    buf = _io.BytesIO(local_file.read_bytes())
                else:
                    logger.warning(f"PDF: cannot resolve image to local file: {src[:80]}")
                    return None

            if buf is None:
                return None

            reader = ImageReader(buf)
            iw, ih = reader.getSize()
            if iw <= 0 or ih <= 0:
                return None
            max_w = 5.2 * inch
            w = min(max_w, float(iw))
            h = w * (ih / iw)
            if h > 5 * inch:
                h = 5 * inch
                w = h * (iw / ih)
            buf.seek(0)
            return RLImage(buf, width=w, height=h)
        except Exception as e:
            logger.warning(f"PDF image skipped ({src[:60]}): {e}")
            return None

    elements = []

    def process(node):
        if not isinstance(node, dict):
            return
        ntype = node.get("type", "")
        children = node.get("content") or []

        if ntype in ("doc",):
            for c in children:
                process(c)

        elif ntype == "paragraph":
            flowables = _paragraph_flowables(children, normal_style)
            for fl in flowables:
                elements.append(fl)

        elif ntype == "heading":
            flowables = _paragraph_flowables(children, normal_style, wrap_bold=True)
            for fl in flowables:
                elements.append(fl)

        elif ntype == "bulletList":
            for item in children:
                flowables = _paragraph_flowables(item.get("content") or [], normal_style, prefix="• ")
                for fl in flowables:
                    elements.append(fl)

        elif ntype == "orderedList":
            for idx, item in enumerate(children, 1):
                flowables = _paragraph_flowables(item.get("content") or [], normal_style, prefix=f"{idx}. ")
                for fl in flowables:
                    elements.append(fl)

        elif ntype == "blockquote":
            from reportlab.lib.styles import ParagraphStyle
            qs = ParagraphStyle('quote', parent=normal_style, leftIndent=18, textColor=_colors.grey)
            flowables = _paragraph_flowables(children, qs)
            for fl in flowables:
                elements.append(fl)

        elif ntype == "codeBlock":
            from reportlab.lib.styles import ParagraphStyle
            cs = ParagraphStyle('code', parent=sub_style, fontName='Courier', fontSize=8,
                                backColor=_colors.Color(0.94, 0.94, 0.94))
            raw = "".join(c.get("text", "") for c in children if c.get("type") == "text")
            if raw:
                elements.append(Spacer(1, 0.05 * inch))
                elements.append(Paragraph(_xs(raw[:1000]), cs))
                elements.append(Spacer(1, 0.05 * inch))

        elif ntype in ("blockMath", "mathBlock"):
            latex = node.get("attrs", {}).get("latex", "")
            if latex:
                elements.append(Spacer(1, 0.08 * inch))
                img = _render_latex_to_flowable(latex, inch, max_width_inch=5.2)
                if img:
                    elements.append(img)
                else:
                    elements.append(Paragraph(f"<i>[ {_xs(latex)} ]</i>", sub_style))
                elements.append(Spacer(1, 0.08 * inch))

        elif ntype == "image":
            src = node.get("attrs", {}).get("src", "")
            if src:
                img = _image_flowable(src)
                if img:
                    elements.append(Spacer(1, 0.1 * inch))
                    elements.append(img)
                    elements.append(Spacer(1, 0.1 * inch))

        elif ntype == "table":
            # Build 2-D list of Paragraph cells
            tbl_data = []
            is_first_row = True
            for row_node in children:
                row = []
                for cell_node in row_node.get("content") or []:
                    markup = "".join(_inline(c) for c in (cell_node.get("content") or [])).strip()
                    cell_style = sub_style if is_first_row else normal_style
                    if is_first_row:
                        markup = f"<b>{markup}</b>"
                    row.append(Paragraph(markup or " ", cell_style))
                if row:
                    tbl_data.append(row)
                is_first_row = False

            if tbl_data:
                num_cols = max(len(r) for r in tbl_data)
                col_w = (5.2 * inch) / num_cols
                tbl = RLTable(tbl_data, colWidths=[col_w] * num_cols, repeatRows=1)
                tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), _colors.Color(0.88, 0.88, 0.95)),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, _colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                     [_colors.white, _colors.Color(0.96, 0.96, 0.96)]),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(tbl)
                elements.append(Spacer(1, 0.1 * inch))

        else:
            # Generic fallback: recurse
            for c in children:
                process(c)

    process(rich_content)
    return elements


def _render_question_block(q, story, q_label, normal_style, heading_style, sub_style,
                            include_solutions, inch, UPLOAD_DIR):
    """Render one question (or sub-question) block into story."""
    import re as _re_q, json as _json
    from reportlab.platypus import Paragraph, Spacer, Image as RLImage
    from reportlab.lib.utils import ImageReader

    pts = getattr(q, 'points', 0)
    story.append(Paragraph(f"<b>{q_label} ({pts} pts)</b>", heading_style))

    # ── Question content (rich text: paragraphs, math, images, tables) ──
    rich = getattr(q, 'rich_content', None)
    if rich:
        try:
            rc = _json.loads(rich) if isinstance(rich, str) else rich
            rich_elements = _rich_content_to_story_elements(
                rc, normal_style, sub_style, inch, upload_dir=UPLOAD_DIR
            )
            story.extend(rich_elements)
        except Exception as _e:
            logger.warning(f"Rich content render error: {_e}")
            fallback = getattr(q, 'text', '') or ''
            if fallback:
                story.append(Paragraph(fallback[:2000], normal_style))
    else:
        plain = getattr(q, 'text', '') or ''
        if plain:
            story.append(Paragraph(plain[:2000], normal_style))

    # ── File attachments (images stored on disk) ──
    for att in getattr(q, 'attachments', []) or []:
        if getattr(att, 'attachment_type', '') != 'image':
            continue
        path = UPLOAD_DIR / att.file_path
        if path.exists():
            try:
                reader = ImageReader(str(path))
                iw, ih = reader.getSize()
                if iw > 0 and ih > 0:
                    aspect = ih / float(iw)
                    max_w = 5.2 * inch
                    w = max_w
                    h = w * aspect
                    if h > 5 * inch:
                        h = 5 * inch
                        w = h / aspect
                    story.append(Spacer(1, 0.1 * inch))
                    story.append(RLImage(str(path), width=w, height=h))
                    story.append(Spacer(1, 0.1 * inch))
            except Exception as e:
                logger.warning(f'Attachment image skipped: {e}')

    # Answer space
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph('<b>Answer:</b>', sub_style))
    if include_solutions:
        story.append(Spacer(1, 0.1 * inch))
        gold_steps = list(getattr(q, 'gold_steps', []) or [])
        if gold_steps:
            story.append(Paragraph('<i>Solution (reference):</i>', sub_style))
            for idx, gs in enumerate(sorted(gold_steps, key=lambda x: getattr(x, 'step_number', 0)), 1):
                step_text = _pdf_safe_text(_clean_step_for_pdf(gs))
                if step_text:
                    story.append(Paragraph(f'{idx}. {step_text}', sub_style))
            final_lat = getattr(q, 'final_answer_latex', None) or getattr(q, 'final_answer', None)
            if final_lat and str(final_lat).strip():
                fa = _re_q.sub(r'\$\$?(.*?)\$\$?', r'\1', str(final_lat), flags=_re_q.DOTALL).strip()
                if fa:
                    fa_img = _render_latex_to_flowable(fa, inch, max_width_inch=3.0)
                    if fa_img:
                        story.append(Paragraph('<b>Final Answer:</b>', sub_style))
                        story.append(fa_img)
                    else:
                        story.append(Paragraph(f'<b>Final Answer:</b> {_pdf_safe_text(fa)}', sub_style))
        else:
            final_ans = getattr(q, 'final_answer_latex', None) or getattr(q, 'final_answer', None)
            if final_ans and str(final_ans).strip():
                fa = _re_q.sub(r'\$\$?(.*?)\$\$?', r'\1', str(final_ans), flags=_re_q.DOTALL).strip()
                fa_img = _render_latex_to_flowable(fa, inch, max_width_inch=3.0)
                if fa_img:
                    story.append(Paragraph('<b>Final Answer:</b>', sub_style))
                    story.append(fa_img)
                else:
                    story.append(Paragraph(f'<b>Final Answer:</b> {_pdf_safe_text(fa)}', sub_style))
            else:
                story.append(Paragraph('<i>No reference solution stored.</i>', sub_style))
        story.append(Spacer(1, 0.3 * inch))
    else:
        dot_line = '_' * 90
        for _ in range(5):
            story.append(Paragraph(dot_line, sub_style))
            story.append(Spacer(1, 0.18 * inch))
        story.append(Spacer(1, 0.15 * inch))


def _clean_step_for_pdf(gs) -> str:
    """Return human-readable text for a gold solution step in PDF.
    Prefers the latex field, strips $/$$ delimiters, falls back to expression.
    Also strips any leading 'Step N:' prefix to avoid duplication with the outer label."""
    import re as _re
    latex = (getattr(gs, "latex", "") or "").strip()
    expression = (getattr(gs, "expression", "") or "").strip()
    desc = (getattr(gs, "description", "") or "").strip()

    def strip_delims(text: str) -> str:
        text = _re.sub(r'^\$\$', '', text)
        text = _re.sub(r'\$\$$', '', text)
        text = _re.sub(r'^\$', '', text)
        text = _re.sub(r'\$$', '', text)
        text = _re.sub(r'\$\$(.*?)\$\$', r'\1', text, flags=_re.DOTALL)
        text = _re.sub(r'\$(.*?)\$', r'\1', text)
        return text.strip()

    def strip_step_prefix(text: str) -> str:
        """Remove 'Step N', 'Step N:', 'Step N.' prefixes stored by the UI."""
        # Standalone "Step N" with nothing after = whole string is the prefix
        cleaned = _re.sub(r'^Step\s*\d+\s*$', '', text, flags=_re.IGNORECASE).strip()
        # "Step N: content" or "Step N. content" → "content"
        cleaned = _re.sub(r'^Step\s*\d+\s*[:.]\s*', '', cleaned, flags=_re.IGNORECASE).strip()
        return cleaned

    desc = strip_step_prefix(desc)

    if latex:
        content = strip_delims(latex)
    elif expression:
        content = strip_step_prefix(strip_delims(expression))
    else:
        content = ""

    if desc and content and desc.lower() not in ('solution', 'answer', ''):
        return f"{desc}: {content}"
    # If desc is generic ("Solution") and we have real content, prefer content
    if content and desc.lower() in ('solution', 'answer'):
        return content
    return desc or content


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
    include_solutions: bool = False,
    paper: str = "letter",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download exam as PDF. include_solutions=true appends gold solution steps.
    paper=a4|letter|legal (default letter)."""
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
    pagesize = _pdf_pagesize(paper)
    doc = SimpleDocTemplate(buffer, pagesize=pagesize, rightMargin=72, leftMargin=72,
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
    banner_style = ParagraphStyle(
        'Banner',
        parent=styles['Normal'],
        fontSize=10,
        textColor='white',
        backColor=(0.2, 0.5, 0.2) if include_solutions else (0.2, 0.35, 0.65),
        borderPadding=6,
        spaceAfter=12,
        alignment=TA_CENTER,
    )

    story = []

    if include_solutions:
        story.append(Paragraph("PROFESSOR COPY — Includes Reference Solutions", banner_style))
    else:
        story.append(Paragraph("STUDENT COPY — Questions Only", banner_style))
    story.append(Spacer(1, 0.1*inch))

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
    
    sub_style = ParagraphStyle('SubQ', parent=normal_style, leftIndent=24, spaceAfter=2)
    sub_heading = ParagraphStyle('SubQH', parent=heading_style, leftIndent=24, fontSize=11)

    if not exam.questions:
        story.append(Paragraph("No questions available.", normal_style))
    else:
        alphabet = 'abcdefghijklmnopqrstuvwxyz'
        tree = _build_question_tree(exam.questions)
        for q_num, (top_q, subs) in enumerate(tree, 1):
            _render_question_block(
                top_q, story,
                q_label=f"Question {q_num}",
                normal_style=normal_style, heading_style=heading_style, sub_style=normal_style,
                include_solutions=include_solutions, inch=inch, UPLOAD_DIR=UPLOAD_DIR
            )
            # Sub-questions indented with letter labels
            for s_num, sub_q in enumerate(subs):
                letter = alphabet[s_num] if s_num < len(alphabet) else str(s_num + 1)
                _render_question_block(
                    sub_q, story,
                    q_label=f"({letter})",
                    normal_style=sub_style, heading_style=sub_heading, sub_style=sub_style,
                    include_solutions=include_solutions, inch=inch, UPLOAD_DIR=UPLOAD_DIR
                )
            story.append(Spacer(1, 0.3 * inch))

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
    suffix = "_with_solutions" if include_solutions else "_questions_only"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={safe_filename}{suffix}.pdf",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        }
    )


@app.get("/api/exams/{exam_id}/view-pdf")
async def view_exam_pdf(
    exam_id: str,
    include_solutions: bool = False,
    paper: str = "letter",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View/download exam PDF - available to both teachers and students.
    include_solutions=true appends gold solution steps and final answers.
    paper=a4|letter|legal (default letter)."""
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
    pagesize_v = _pdf_pagesize(paper)
    doc = SimpleDocTemplate(buffer, pagesize=pagesize_v, rightMargin=72, leftMargin=72,
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
    banner_style_v = ParagraphStyle(
        'BannerV',
        parent=styles['Normal'],
        fontSize=10,
        textColor='white',
        backColor=(0.2, 0.5, 0.2) if include_solutions else (0.2, 0.35, 0.65),
        borderPadding=6,
        spaceAfter=12,
        alignment=TA_CENTER,
    )

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
    if include_solutions:
        story.append(Paragraph("PROFESSOR COPY — Includes Reference Solutions", banner_style_v))
    else:
        story.append(Paragraph("STUDENT COPY — Questions Only", banner_style_v))
    story.append(Spacer(1, 0.1*inch))
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
    
    sub_style_v = ParagraphStyle('SubQV', parent=normal_style, leftIndent=24, spaceAfter=2)
    sub_heading_v = ParagraphStyle('SubQHV', parent=heading_style, leftIndent=24, fontSize=11)

    if not exam.questions:
        story.append(Paragraph("No questions available.", normal_style))
    else:
        alphabet = 'abcdefghijklmnopqrstuvwxyz'
        tree = _build_question_tree(exam.questions)
        for q_num, (top_q, subs) in enumerate(tree, 1):
            _render_question_block(
                top_q, story,
                q_label=f"Question {q_num}",
                normal_style=normal_style, heading_style=heading_style, sub_style=normal_style,
                include_solutions=include_solutions, inch=inch, UPLOAD_DIR=UPLOAD_DIR
            )
            for s_num, sub_q in enumerate(subs):
                letter = alphabet[s_num] if s_num < len(alphabet) else str(s_num + 1)
                _render_question_block(
                    sub_q, story,
                    q_label=f"({letter})",
                    normal_style=sub_style_v, heading_style=sub_heading_v, sub_style=sub_style_v,
                    include_solutions=include_solutions, inch=inch, UPLOAD_DIR=UPLOAD_DIR
                )
            story.append(Spacer(1, 0.3 * inch))

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
    suffix = "_with_solutions" if include_solutions else "_questions_only"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={safe_filename}{suffix}.pdf",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        }
    )



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

