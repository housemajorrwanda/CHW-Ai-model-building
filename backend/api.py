"""
FastAPI backend for EasyGrade
"""
from pathlib import Path

from dotenv import load_dotenv

# Load project-root .env when running locally (docker compose sets env via env_file).
_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir.parent / ".env")
load_dotenv(_backend_dir / ".env")  # optional backend-local override

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func
from typing import List, Optional, Tuple, Any, Dict
import os
import re
import math
import logging
import shutil
from datetime import datetime, timedelta, date, timezone
import jwt
import json

logger = logging.getLogger(__name__)

from database import get_db, init_db, engine, SessionLocal
import models
import schemas
import notifications_service
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
_default_origins = (
    "http://localhost:8080,http://localhost:5173,http://localhost:3000,"
    "http://127.0.0.1:8080,http://localhost,http://127.0.0.1"
)
_env_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
# Merge env origins with local dev defaults so setting ALLOWED_ORIGINS for ngrok
# does not break login from localhost:8080.
_dev_origins = [o.strip() for o in _default_origins.split(",") if o.strip()]
allowed_origins = list(dict.fromkeys(_env_origins + _dev_origins)) if _env_origins else _dev_origins
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

# OCR: EasyOCR is optional (large deps). Tesseract alone is weak on handwriting; for local dev set
# USE_EASYOCR=1 and `pip install easyocr` for better scan accuracy.
_use_easyocr = os.getenv("USE_EASYOCR", "").lower() in ("1", "true", "yes")
ocr_processor = OCRProcessor(language="en", dpi=360, psm=6, use_easyocr=_use_easyocr)
_cloud = getattr(ocr_processor, "cloud", None)
if _cloud is not None:
    _cloud._refresh_provider()
_cloud_name = _cloud.active_provider_name if _cloud else None
logger.info(
    "OCR processor: easyocr=%s cloud=%s (set USE_EASYOCR=1 and install easyocr for handwriting scans)",
    _use_easyocr,
    _cloud_name or "none (local TrOCR/Tesseract fallback)",
)
if os.getenv("MATH_OCR_PROVIDER", "").strip().lower() == "mathpix" and not _cloud_name:
    logger.warning(
        "MATH_OCR_PROVIDER=mathpix but Mathpix is not active — check MATHPIX_APP_ID / "
        "MATHPIX_APP_KEY in .env and restart the backend after changing env vars."
    )
if _use_easyocr and not ocr_processor.use_easyocr:
    logger.warning(
        "USE_EASYOCR is set but EasyOCR did not load (missing package or init failed); using Tesseract only."
    )


@app.get("/api/ocr/status")
def ocr_status():
    """
    Report which OCR engines are wired up. Surfaced in the take-exam UI so the
    student knows whether handwriting will be read by a local TrOCR model, a
    cloud math/handwriting provider, or just the basic Tesseract fallback.
    """
    cloud = getattr(ocr_processor, "cloud", None)
    cloud_status = cloud.status() if cloud else {
        "active": None,
        "available": [],
        "configured": [],
    }
    trocr_enabled = getattr(ocr_processor, "trocr", None) is not None
    trocr_runtime = bool(getattr(ocr_processor, "trocr_runtime_available", False))
    lh: dict = {}
    if trocr_runtime:
        try:
            from ocr.local_handwriting import local_handwriting_engine_status

            lh = local_handwriting_engine_status()
        except Exception:
            lh = {}
    pp_status: dict = {}
    try:
        from ocr.pp_structure_processor import pp_structure_engine_status

        pp_status = pp_structure_engine_status()
    except Exception:
        pp_status = {}
    prose_model = lh.get("proseModel") if trocr_enabled else None
    return {
        "cloud": cloud_status,
        "localTrocr": {
            "enabled": trocr_enabled,
            "runtimeAvailable": trocr_runtime,
            # `model` kept for older frontends — same as prose TrOCR checkpoint.
            "model": prose_model,
            "proseModel": prose_model,
            "mathTrocrModel": lh.get("mathTrocrModel") if trocr_enabled else None,
            "pix2texOptIn": bool(lh.get("pix2texOptIn")),
            "pix2texReady": bool(lh.get("pix2texImportable")),
            "mathEnsembleMode": lh.get("mathEnsembleMode") if trocr_enabled else None,
        },
        "localEasyOcr": bool(ocr_processor.use_easyocr),
        "ppStructure": pp_status,
        "tesseract": True,
        # Friendly description for the UI; safe to show to students.
        "summary": _ocr_status_summary(
            cloud_status,
            trocr_enabled,
            trocr_runtime,
            ocr_processor.use_easyocr,
            lh if trocr_enabled else {},
            pp_status,
        ),
    }


def _ocr_status_summary(
    cloud_status: dict,
    trocr_enabled: bool,
    trocr_runtime: bool,
    easy_loaded: bool,
    local_hw: Optional[dict] = None,
    pp_structure: Optional[dict] = None,
) -> str:
    active = cloud_status.get("active")
    if active == "mathpix":
        return "Handwritten math is read by Mathpix (cloud math/handwriting OCR)."
    if active == "gcv":
        return "Handwriting is read by Google Cloud Vision (cloud OCR)."
    if active == "azure":
        return "Handwriting is read by Azure Read (cloud OCR)."
    pp = pp_structure or {}
    if pp.get("ready"):
        return (
            "Handwriting and formulas are read by PP-StructureV3 (PaddleOCR) "
            f"with {pp.get('lang', 'en')} text recognition on "
            f"{pp.get('device', 'cpu')}."
        )
    if trocr_enabled:
        lh = local_hw or {}
        prose = lh.get("proseModel") or "microsoft/trocr-small-handwritten"
        math_m = lh.get("mathTrocrModel") or "fhswf/TrOCR_Math_handwritten"
        mode = lh.get("mathEnsembleMode") or "full"
        tail = (
            " When you submit, each line is scored across prose + math models; "
            "set OCR_MATH_HEURISTIC_ONLY=1 on slow servers to skip math on non-math lines."
            if mode == "full"
            else " Math handwriting (fhswf) runs only on lines that look like math or noisy OCR."
        )
        if lh.get("pix2texOptIn") and lh.get("pix2texImportable"):
            tail += " pix2tex (third pass) is enabled."
        return (
            "Handwriting uses local TrOCR: prose model "
            f"({prose}) plus math handwriting ({math_m}).{tail} "
            "Quality beats Tesseract alone; difficult scans may still need review."
        )
    # No handwriting engine is active. We deliberately do not surface this to
    # students — the routing preview + page images already give them enough to
    # verify their submission. The status endpoint still returns the raw flags
    # so admins can debug it; the UI just hides the banner.
    return ""


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
    if submission.total_score is not None:
        return submission.total_score
    if submission.grading_results:
        return round(sum(float(gr.score or 0) for gr in submission.grading_results), 2)
    return None


def _recompute_submission_total_score(db: Session, submission_id: str) -> float:
    """Sum persisted per-question scores (source of truth after auto-grade)."""
    rows = (
        db.query(models.GradingResult)
        .filter(models.GradingResult.submission_id == submission_id)
        .all()
    )
    return round(sum(float(r.score or 0) for r in rows), 2)


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
            # Footer "Page N of M" lines duplicate <<PAGEBREAK>> and inflate page_num during parsing.
            text = re.sub(
                r'(?m)^\s*(?:-+\s*\d+\s+of\s+\d+\s*-+|page\s+\d+\s+of\s+\d+)\s*$',
                '',
                text,
                flags=re.IGNORECASE,
            )
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


async def _read_upload_file_as_text(file: UploadFile) -> str:
    """Extract plain text from an uploaded .txt, image, or PDF (shared by exam/answer-key uploads)."""
    file_content = await file.read()
    file_ext = Path(file.filename or "").suffix.lower()

    if file_ext == ".txt":
        return file_content.decode("utf-8", errors="replace")

    if file_ext in [".jpg", ".jpeg", ".png", ".pdf"]:
        from ocr.text_rich_content import normalize_exam_ocr_text

        ocr_result = ocr_processor.extract_steps_from_file(
            file_content, file.filename or "upload"
        )
        text = normalize_exam_ocr_text(ocr_result.combined_text or "")
        if not text:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from file. Use .txt or a clear PDF/image.",
            )
        return text

    raise HTTPException(
        status_code=400,
        detail="Unsupported file format. Use .txt, .jpg, .png, or .pdf",
    )


def _apply_answer_key_matches(
    db: Session,
    matches: List[dict],
    *,
    overwrite: bool = True,
) -> int:
    """Write aligned gold solutions onto existing exam questions."""
    from answer_key_aligner import _meaningful_steps

    updated = 0
    for match in matches:
        question = (
            db.query(models.Question)
            .filter(models.Question.id == match["question_id"])
            .first()
        )
        if not question:
            continue
        if not overwrite and question.gold_steps:
            continue

        steps = _meaningful_steps(match.get("gold_steps") or [])
        if not steps:
            continue

        db.query(models.GoldSolutionStep).filter(
            models.GoldSolutionStep.question_id == question.id
        ).delete(synchronize_session=False)

        for step in steps:
            db.add(
                models.GoldSolutionStep(
                    question_id=question.id,
                    step_number=int(step.get("step_number") or 1),
                    description=(step.get("description") or "Solution")[:500],
                    expression=(step.get("expression") or "")[:500],
                    latex=(step.get("latex") or "")[:500] if step.get("latex") else None,
                    points=int(step.get("points") or 1),
                    required=bool(step.get("required", True)),
                )
            )

        final_answer = (match.get("final_answer") or "").strip()
        if final_answer:
            question.final_answer = final_answer[:500]
        final_latex = (match.get("final_answer_latex") or "").strip()
        if final_latex:
            question.final_answer_latex = final_latex[:500]
        updated += 1

    return updated


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
        'diagram', 'graph', 'figure', 'plot', 'sketch',
        'illustration', 'apparatus', 'setup', 'experiment',
        'flow chart', 'flowchart', 'flow chart below',
        'the diagram', 'study it and answer',
        'outlines some of the process',
        'chart below', 'graph below', 'figure below', 'diagram below',
        'reaction scheme', 'scheme below', 'deduce the structures',
        'mass spectrum', 'relative intensity', 'm/z',
        'match column', 'column a', 'table below',
    }

    def _text_needs_diagram(blob: str) -> bool:
        blob = (blob or "").lower()
        return any(kw in blob for kw in _DIAGRAM_KW)

    def _question_wants_diagram(q: dict) -> bool:
        if _text_needs_diagram(q.get("text") or ""):
            return True
        return any(_question_wants_diagram(sub) for sub in q.get("sub_questions") or [])

    # Solution section markers (lower-case) used to find where answers start on the page
    _SOL_MARKERS = [
        'gold solution', 'model answer', 'expected answer',
        'correct answer', 'answer key', 'solution:',
    ]

    pages_needed = {q.get('page_num', i) for i, q in enumerate(questions)}
    if not pages_needed:
        return result

    def _questions_wanting_diagram(pg_num: int) -> List[int]:
        nums = []
        for q in questions:
            if q.get('page_num', -1) != pg_num:
                continue
            if _question_wants_diagram(q):
                nums.append(q.get("number"))
        return nums

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
    page_has_diagram_ref: dict = {}
    for pg_num in pages_needed:
        info = page_info.get(pg_num)
        if info is None:
            continue
        want = _questions_wanting_diagram(pg_num)
        page_has_diagram_ref[pg_num] = bool(want)
        if info['images'] or want:
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
                # Vector drawing (flow charts, diagrams without embedded raster images)
                cropped = None
                if gold_top is not None:
                    crop_px = max(60, int(gold_top * sy) - 12)
                    cropped = page_img.crop((0, 0, page_img.width, crop_px))
                elif page_has_diagram_ref.get(pg_num):
                    top_px = int(page_img.height * 0.12)
                    bot_px = int(page_img.height * 0.72)
                    cropped = page_img.crop((0, top_px, page_img.width, bot_px))
                if cropped is not None:
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
    from notifications_service import (
        exam_offset_hours_for_user,
        exam_reminders_enabled,
        teaching_reminders_enabled,
    )

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
        remindExamDeadlinesEnabled=exam_reminders_enabled(user),
        remindExamOffsetsHours=exam_offset_hours_for_user(user),
        remindTeachingDeadlinesEnabled=teaching_reminders_enabled(user),
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


@app.get("/api/notifications", response_model=schemas.NotificationFeedResponse)
def list_notifications(
    limit: int = 80,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """In-app notifications plus computed reminders (exam deadlines, enrollments, approvals)."""
    if limit > 200:
        limit = 200
    if limit < 1:
        limit = 1
    items, badge = notifications_service.build_feed(db, current_user, limit=limit)
    return schemas.NotificationFeedResponse(
        items=[schemas.NotificationFeedItem(**item) for item in items],
        unreadCount=badge,
    )


@app.patch("/api/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single persisted notification as read (reminder rows are not stored)."""
    if notification_id.startswith("reminder:"):
        raise HTTPException(status_code=400, detail="Reminders cannot be marked read")
    ok = notifications_service.mark_read(db, current_user, notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.commit()
    return {"ok": True}


@app.post("/api/notifications/read-all")
def mark_all_notifications_read(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all persisted notifications as read for the current user."""
    marked = notifications_service.mark_all_read(db, current_user)
    db.commit()
    return {"marked": marked}


@app.get("/api/reminders/due", response_model=List[schemas.ScheduledReminderDueItem])
def get_due_scheduled_reminders(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Personal reminders that are due now (shown in a separate alert, not the bell list)."""
    raw = notifications_service.list_due_scheduled_reminders(db, current_user)
    return [schemas.ScheduledReminderDueItem(**row) for row in raw]


@app.post("/api/reminders/schedule")
def schedule_personal_reminder(
    body: schemas.ScheduleReminderRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a follow-up reminder (date/time, optional repeat) tied to a feed item."""
    ra = body.remindAt
    if ra.tzinfo is None:
        ra = ra.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if ra <= now - timedelta(minutes=1):
        raise HTTPException(status_code=400, detail="Choose a time in the future")
    r = notifications_service.schedule_user_reminder(
        db,
        current_user,
        source_key=body.sourceKey,
        title=body.title,
        body=body.body,
        link=body.link,
        user_note=body.userNote,
        remind_at=ra,
        repeat=body.repeat,
    )
    db.commit()
    db.refresh(r)
    return {"id": r.id}


@app.post("/api/reminders/scheduled/{reminder_id}/acknowledge")
def acknowledge_personal_reminder(
    reminder_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dismiss a due scheduled reminder, or advance it when repeat is enabled."""
    ok = notifications_service.acknowledge_scheduled_reminder(db, current_user, reminder_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found")
    db.commit()
    return {"ok": True}


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

    if "remindExamDeadlinesEnabled" in _prof:
        current_user.remind_exam_deadlines_enabled = bool(_prof["remindExamDeadlinesEnabled"])
    if "remindExamOffsetsHours" in _prof:
        import json as _json

        hours = _prof["remindExamOffsetsHours"]
        current_user.remind_exam_offsets_hours = _json.dumps(hours)
    if "remindTeachingDeadlinesEnabled" in _prof:
        current_user.remind_teaching_deadlines_enabled = bool(_prof["remindTeachingDeadlinesEnabled"])

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
    notifications_service.push_notification(
        db,
        user_id=course.professor_id,
        kind="enrollment_requested",
        title="New enrollment request",
        body=f"{current_user.name} requested to join {course.name} ({course.code}).",
        link=f"/courses/{course_id}",
    )
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
    notifications_service.push_notification(
        db,
        user_id=enrollment.student_id,
        kind="enrollment_approved",
        title=f"Enrolled in {course.name}",
        body="You can now access published exams for this course.",
        link="/my-exams",
    )
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
    notifications_service.push_notification(
        db,
        user_id=enrollment.student_id,
        kind="enrollment_rejected",
        title=f"Enrollment update: {course.name}",
        body="Your request to join this course was not approved.",
        link="/browse-courses",
    )
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


def _user_can_access_course_announcements(
    db: Session, user: models.User, course: models.Course
) -> bool:
    if user.role == models.UserRole.ADMIN:
        return True
    if user.role == models.UserRole.PROFESSOR and course.professor_id == user.id:
        return True
    if user.role == models.UserRole.STUDENT:
        row = (
            db.query(models.CourseEnrollment)
            .filter(
                models.CourseEnrollment.course_id == course.id,
                models.CourseEnrollment.student_id == user.id,
                models.CourseEnrollment.status == models.EnrollmentStatus.APPROVED,
            )
            .first()
        )
        return row is not None
    return False


def _user_can_view_exam(db: Session, user: models.User, exam: models.Exam) -> bool:
    """Professors/admins for the course, enrolled students, or anyone if published."""
    if exam.is_published:
        return True
    course = db.query(models.Course).filter(models.Course.id == exam.course_id).first()
    if not course:
        return False
    return _user_can_access_course_announcements(db, user, course)


def _schema_reaction_kind_to_model(kind: schemas.AnnouncementReactionKind) -> models.AnnouncementReactionKind:
    return models.AnnouncementReactionKind(kind.value)


def _announcement_to_schema(
    ann: models.CourseAnnouncement, viewer: models.User
) -> schemas.AnnouncementResponse:
    counts = {"like": 0, "improve": 0, "implement": 0}
    my_like = my_improve = my_implement = False
    for r in ann.reactions:
        k = r.kind.value if hasattr(r.kind, "value") else str(r.kind)
        if k in counts:
            counts[k] += 1
        if r.user_id == viewer.id:
            if k == "like":
                my_like = True
            elif k == "improve":
                my_improve = True
            elif k == "implement":
                my_implement = True
    comments_sorted = sorted(
        ann.comments,
        key=lambda c: c.created_at or datetime(1970, 1, 1, tzinfo=timezone.utc),
    )
    comment_payloads = [
        schemas.AnnouncementCommentResponse(
            id=c.id,
            authorId=c.author_id,
            authorName=c.author.name,
            body=c.body,
            createdAt=c.created_at,
        )
        for c in comments_sorted
    ]
    return schemas.AnnouncementResponse(
        id=ann.id,
        courseId=ann.course_id,
        authorId=ann.author_id,
        authorName=ann.author.name,
        title=ann.title,
        body=ann.body,
        pinned=bool(ann.pinned),
        createdAt=ann.created_at,
        likeCount=counts["like"],
        improveCount=counts["improve"],
        implementCount=counts["implement"],
        commentCount=len(comment_payloads),
        myLiked=my_like,
        myImprove=my_improve,
        myImplement=my_implement,
        comments=comment_payloads,
    )


def _load_announcement_for_course(
    db: Session, course_id: str, announcement_id: str
) -> Optional[models.CourseAnnouncement]:
    return (
        db.query(models.CourseAnnouncement)
        .filter(
            models.CourseAnnouncement.id == announcement_id,
            models.CourseAnnouncement.course_id == course_id,
        )
        .options(
            joinedload(models.CourseAnnouncement.author),
            selectinload(models.CourseAnnouncement.comments).joinedload(
                models.AnnouncementComment.author
            ),
            selectinload(models.CourseAnnouncement.reactions),
        )
        .first()
    )


@app.get(
    "/api/courses/{course_id}/announcements",
    response_model=List[schemas.AnnouncementResponse],
)
def list_course_announcements(
    course_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not _user_can_access_course_announcements(db, current_user, course):
        raise HTTPException(status_code=403, detail="Not authorized to view announcements for this course")

    rows = (
        db.query(models.CourseAnnouncement)
        .filter(models.CourseAnnouncement.course_id == course_id)
        .options(
            joinedload(models.CourseAnnouncement.author),
            selectinload(models.CourseAnnouncement.comments).joinedload(
                models.AnnouncementComment.author
            ),
            selectinload(models.CourseAnnouncement.reactions),
        )
        .order_by(models.CourseAnnouncement.pinned.desc(), models.CourseAnnouncement.created_at.desc())
        .all()
    )
    return [_announcement_to_schema(a, current_user) for a in rows]


@app.post(
    "/api/courses/{course_id}/announcements",
    response_model=schemas.AnnouncementResponse,
)
def create_course_announcement(
    course_id: str,
    payload: schemas.AnnouncementCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (models.UserRole.PROFESSOR, models.UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only instructors can post announcements")
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.professor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to post in this course")

    ann = models.CourseAnnouncement(
        course_id=course_id,
        author_id=current_user.id,
        title=payload.title.strip(),
        body=payload.body.strip(),
        pinned=payload.pinned,
    )
    db.add(ann)
    db.flush()

    enrollments = (
        db.query(models.CourseEnrollment)
        .filter(
            models.CourseEnrollment.course_id == course_id,
            models.CourseEnrollment.status == models.EnrollmentStatus.APPROVED,
        )
        .all()
    )
    preview = (ann.title[:120] + "…") if len(ann.title) > 120 else ann.title
    for enr in enrollments:
        notifications_service.push_notification(
            db,
            user_id=enr.student_id,
            kind="course_announcement",
            title=f"New announcement: {course.name}",
            body=preview,
            link=f"/courses/{course_id}/announcements",
        )
    db.commit()
    ann = _load_announcement_for_course(db, course_id, ann.id)
    return _announcement_to_schema(ann, current_user)


@app.patch(
    "/api/courses/{course_id}/announcements/{announcement_id}",
    response_model=schemas.AnnouncementResponse,
)
def update_course_announcement(
    course_id: str,
    announcement_id: str,
    payload: schemas.AnnouncementUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (models.UserRole.PROFESSOR, models.UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized")
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.professor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    ann = (
        db.query(models.CourseAnnouncement)
        .filter(
            models.CourseAnnouncement.id == announcement_id,
            models.CourseAnnouncement.course_id == course_id,
        )
        .first()
    )
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if payload.title is not None:
        ann.title = payload.title.strip()
    if payload.body is not None:
        ann.body = payload.body.strip()
    if payload.pinned is not None:
        ann.pinned = payload.pinned
    db.commit()
    ann = _load_announcement_for_course(db, course_id, announcement_id)
    return _announcement_to_schema(ann, current_user)


@app.delete("/api/courses/{course_id}/announcements/{announcement_id}")
def delete_course_announcement(
    course_id: str,
    announcement_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (models.UserRole.PROFESSOR, models.UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized")
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.professor_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    ann = (
        db.query(models.CourseAnnouncement)
        .filter(
            models.CourseAnnouncement.id == announcement_id,
            models.CourseAnnouncement.course_id == course_id,
        )
        .first()
    )
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    db.delete(ann)
    db.commit()
    return {"message": "Announcement deleted"}


@app.post(
    "/api/courses/{course_id}/announcements/{announcement_id}/reactions/toggle",
    response_model=schemas.AnnouncementResponse,
)
def toggle_announcement_reaction(
    course_id: str,
    announcement_id: str,
    payload: schemas.AnnouncementReactionToggle,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not _user_can_access_course_announcements(db, current_user, course):
        raise HTTPException(status_code=403, detail="Not authorized")

    ann = (
        db.query(models.CourseAnnouncement)
        .filter(
            models.CourseAnnouncement.id == announcement_id,
            models.CourseAnnouncement.course_id == course_id,
        )
        .first()
    )
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")

    mk = _schema_reaction_kind_to_model(payload.kind)
    existing = (
        db.query(models.AnnouncementReaction)
        .filter(
            models.AnnouncementReaction.announcement_id == announcement_id,
            models.AnnouncementReaction.user_id == current_user.id,
            models.AnnouncementReaction.kind == mk,
        )
        .first()
    )
    if existing:
        db.delete(existing)
    else:
        db.add(
            models.AnnouncementReaction(
                announcement_id=announcement_id,
                user_id=current_user.id,
                kind=mk,
            )
        )
    db.commit()
    ann = _load_announcement_for_course(db, course_id, announcement_id)
    return _announcement_to_schema(ann, current_user)


@app.post(
    "/api/courses/{course_id}/announcements/{announcement_id}/comments",
    response_model=schemas.AnnouncementResponse,
)
def add_announcement_comment(
    course_id: str,
    announcement_id: str,
    payload: schemas.AnnouncementCommentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not _user_can_access_course_announcements(db, current_user, course):
        raise HTTPException(status_code=403, detail="Not authorized")

    ann = (
        db.query(models.CourseAnnouncement)
        .filter(
            models.CourseAnnouncement.id == announcement_id,
            models.CourseAnnouncement.course_id == course_id,
        )
        .first()
    )
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")

    c = models.AnnouncementComment(
        announcement_id=announcement_id,
        author_id=current_user.id,
        body=payload.body.strip(),
    )
    db.add(c)
    db.commit()
    ann = _load_announcement_for_course(db, course_id, announcement_id)
    return _announcement_to_schema(ann, current_user)


@app.delete(
    "/api/courses/{course_id}/announcements/{announcement_id}/comments/{comment_id}",
    response_model=schemas.AnnouncementResponse,
)
def delete_announcement_comment(
    course_id: str,
    announcement_id: str,
    comment_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not _user_can_access_course_announcements(db, current_user, course):
        raise HTTPException(status_code=403, detail="Not authorized")

    comment = (
        db.query(models.AnnouncementComment)
        .filter(
            models.AnnouncementComment.id == comment_id,
            models.AnnouncementComment.announcement_id == announcement_id,
        )
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    is_moderator = current_user.role == models.UserRole.ADMIN or course.professor_id == current_user.id
    if comment.author_id != current_user.id and not is_moderator:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    db.delete(comment)
    db.commit()
    ann = _load_announcement_for_course(db, course_id, announcement_id)
    return _announcement_to_schema(ann, current_user)


def _build_nested_question_responses(parent_id: str, children_by_parent: dict, to_response):
    children = sorted(children_by_parent.get(parent_id, []), key=lambda q: q.number)
    return [
        to_response(
            child,
            _build_nested_question_responses(child.id, children_by_parent, to_response),
        )
        for child in children
    ]


def _build_exam_questions_tree_response(
    all_questions: List[models.Question],
    *,
    include_attachments: bool = False,
    include_embedded: bool = False,
) -> List[schemas.QuestionResponse]:
    """Return only top-level questions with nested subQuestions (never flat sub-parts)."""
    top_level = [q for q in all_questions if not getattr(q, "parent_question_id", None)]
    children_by_parent: Dict[str, List[models.Question]] = {}
    for q in all_questions:
        pid = getattr(q, "parent_question_id", None)
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
                required=getattr(step, "required", True),
            )
            for step in question.gold_steps
        ]
        attachments_data = []
        if include_attachments:
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
        if include_embedded:
            for ec in question.embedded_content:
                try:
                    content_data = (
                        json.loads(ec.content_data)
                        if isinstance(ec.content_data, str)
                        else (ec.content_data or {})
                    )
                    position_data = (
                        json.loads(ec.position_data)
                        if isinstance(ec.position_data, str) and ec.position_data
                        else None
                    )
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
        rich_content_val = (
            json.loads(question.rich_content)
            if question.rich_content and isinstance(question.rich_content, str)
            else (question.rich_content if question.rich_content else None)
        )
        return schemas.QuestionResponse(
            id=question.id,
            number=question.number,
            text=display_text,
            points=question.points,
            goldSolution=schemas.GoldSolutionResponse(
                steps=gold_steps,
                finalAnswer=question.final_answer or "",
                finalAnswerLatex=question.final_answer_latex or "",
            ),
            goldSolutionSteps=gold_steps,
            finalAnswer=question.final_answer or "",
            finalAnswerLatex=question.final_answer_latex or "",
            questionType=getattr(question, "question_type", "standard"),
            richContent=rich_content_val,
            outlineTitle=_display_safe_text(question.outline_title)
            if getattr(question, "outline_title", None)
            else None,
            outlineLevel=getattr(question, "outline_level", 1),
            parentQuestionId=getattr(question, "parent_question_id", None),
            subQuestions=sub_responses or [],
            attachments=attachments_data,
            embeddedContent=embedded_data,
            theories=[],
        )

    return [
        _question_to_response(
            question,
            _build_nested_question_responses(question.id, children_by_parent, _question_to_response),
        )
        for question in sorted(top_level, key=lambda q: q.number)
    ]


def _schema_question_tree_points(question_data) -> int:
    """Sum points from a create/update payload (parents with subs use sub-totals only)."""
    subs = getattr(question_data, "subQuestions", None) or []
    if subs:
        return sum(_schema_question_tree_points(s) for s in subs)
    return int(getattr(question_data, "points", 0) or 0)


def _calculate_exam_total_points_db(db: Session, exam_id: str) -> int:
    """Recompute exam total from persisted question tree (source of truth after save/upload)."""
    rows = db.query(models.Question).filter(models.Question.exam_id == exam_id).all()
    by_parent: Dict[str, List[models.Question]] = {}
    top_level: List[models.Question] = []
    for q in rows:
        pid = getattr(q, "parent_question_id", None)
        if pid:
            by_parent.setdefault(pid, []).append(q)
        else:
            top_level.append(q)

    def _tree_points(q: models.Question) -> int:
        children = by_parent.get(q.id, [])
        if children:
            return sum(_tree_points(c) for c in children)
        return int(q.points or 0)

    return sum(_tree_points(q) for q in top_level)


def _save_question_tree_from_schema(
    db: Session,
    exam_id: str,
    exam_attach_dir: Path,
    question_data,
    *,
    parent_id: Optional[str] = None,
    protected_att_paths: Optional[dict] = None,
) -> models.Question:
    """Persist a question and all nested subQuestions from ExamCreate/Update payload."""
    new_question = models.Question(
        exam_id=exam_id,
        number=question_data.number,
        text=question_data.text,
        points=question_data.points,
        final_answer=question_data.finalAnswer,
        final_answer_latex=question_data.finalAnswerLatex,
        question_type=question_data.questionType,
        rich_content=json.dumps(question_data.richContent) if question_data.richContent else None,
        outline_title=(question_data.outlineTitle or "").strip() or None,
        outline_level=question_data.outlineLevel,
        parent_question_id=parent_id or question_data.parentQuestionId,
    )
    db.add(new_question)
    db.flush()

    if protected_att_paths is not None and question_data.richContent:
        qrc = (
            json.dumps(question_data.richContent)
            if isinstance(question_data.richContent, dict)
            else question_data.richContent
        )
        for pid, ppath in list(protected_att_paths.items()):
            if pid in (qrc or "") and ppath:
                patt = db.query(models.QuestionAttachment).filter(
                    models.QuestionAttachment.id == pid
                ).first()
                if patt:
                    patt.question_id = new_question.id

    attachments = getattr(question_data, "attachments", None) or []
    for att_data in attachments:
        if att_data.filePath.startswith("/api/attachments/"):
            att_id = att_data.filePath.split("/")[-2] if "/" in att_data.filePath else None
            if att_id:
                temp_att = db.query(models.QuestionAttachment).filter(
                    models.QuestionAttachment.id == att_id
                ).first()
                if temp_att:
                    old_path = UPLOAD_DIR / temp_att.file_path
                    if old_path.exists():
                        safe_name = f"q{question_data.number}_{temp_att.filename}"
                        new_path = exam_attach_dir / safe_name
                        shutil.move(str(old_path), str(new_path))
                        rel_path = f"exam_attachments/{exam_id}/{safe_name}"
                        temp_att.question_id = new_question.id
                        temp_att.file_path = rel_path
                    else:
                        rel_path = f"exam_attachments/{exam_id}/q{question_data.number}_{att_data.filename}"
                        db.add(
                            models.QuestionAttachment(
                                question_id=new_question.id,
                                attachment_type=att_data.attachmentType,
                                file_path=rel_path,
                                filename=att_data.filename,
                                file_size=att_data.fileSize,
                                mime_type=att_data.mimeType,
                            )
                        )
        else:
            rel_path = f"exam_attachments/{exam_id}/q{question_data.number}_{att_data.filename}"
            db.add(
                models.QuestionAttachment(
                    question_id=new_question.id,
                    attachment_type=att_data.attachmentType,
                    file_path=rel_path,
                    filename=att_data.filename,
                    file_size=att_data.fileSize,
                    mime_type=att_data.mimeType,
                )
            )

    if question_data.richContent:
        rich_json = (
            question_data.richContent
            if isinstance(question_data.richContent, dict)
            else json.loads(question_data.richContent)
        )
        for emb_data in extract_embedded_content_from_tiptap(rich_json):
            db.add(
                models.EmbeddedContent(
                    question_id=new_question.id,
                    content_type=emb_data["contentType"],
                    content_data=json.dumps(emb_data["contentData"]),
                    position_data=json.dumps(emb_data["positionData"])
                    if emb_data.get("positionData")
                    else None,
                )
            )

    for emb_data in getattr(question_data, "embeddedContent", None) or []:
        db.add(
            models.EmbeddedContent(
                question_id=new_question.id,
                content_type=emb_data.contentType,
                content_data=json.dumps(emb_data.contentData),
                position_data=json.dumps(emb_data.positionData) if emb_data.positionData else None,
            )
        )

    for step_data in question_data.goldSolutionSteps:
        db.add(
            models.GoldSolutionStep(
                question_id=new_question.id,
                step_number=step_data.stepNumber,
                description=step_data.description,
                expression=step_data.expression,
                latex=step_data.latex,
                points=step_data.points,
                required=step_data.required,
            )
        )

    for sub_q_data in question_data.subQuestions:
        _save_question_tree_from_schema(
            db,
            exam_id,
            exam_attach_dir,
            sub_q_data,
            parent_id=new_question.id,
            protected_att_paths=protected_att_paths,
        )

    return new_question


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
        questions_data = _build_exam_questions_tree_response(list(exam.questions))
        
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
    
    # Calculate total points from full question tree (not just top-level header values).
    total_points = sum(_schema_question_tree_points(q) for q in exam_data.questions)
    
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

    for question_data in exam_data.questions:
        _save_question_tree_from_schema(db, new_exam.id, exam_attach_dir, question_data)
    
    new_exam.total_points = _calculate_exam_total_points_db(db, new_exam.id)
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
                ocr_result = None
                if file_ext == '.pdf':
                    _raw_pdf_bytes = file_content
                ocr_result = ocr_processor.extract_steps_from_file(
                    file_content, file.filename or "upload"
                )
                text = ocr_result.combined_text
                if file_ext in ['.jpg', '.jpeg', '.png']:
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
        from ocr.text_rich_content import normalize_exam_ocr_text, looks_like_math_ocr

        text = normalize_exam_ocr_text(text or "")
        parsed_exam = parser.parse_exam(text)

        if looks_like_math_ocr(parsed_exam.get("title") or ""):
            parsed_exam["title"] = "Imported Exam"

        # Extract diagrams from PDF using pdfplumber + pdf2image now that we
        # know which questions are on which pages (and can find "Gold Solution:" positions)
        if _raw_pdf_bytes and parsed_exam.get('questions') and not pdf_embedded_images:
            try:
                pdf_embedded_images = _extract_pdf_diagrams(_raw_pdf_bytes, parsed_exam['questions'])
                logger.info(f"Diagram extraction: found images on {len(pdf_embedded_images)} page(s)")
            except Exception as _de:
                logger.warning(f"Diagram extraction failed: {_de}")

        # Handwritten/scanned PDFs: only render page images when a question actually
        # references a diagram (never attach the whole scan as a fake "diagram").
        def _parsed_tree_needs_diagram(qlist: list) -> bool:
            def _walk(qd: dict) -> bool:
                blob = (qd.get("text") or "").lower()
                if any(kw in blob for kw in _DIAGRAM_KW_EARLY):
                    return True
                return any(_walk(s) for s in qd.get("sub_questions") or [])

            return any(_walk(q) for q in qlist)

        _DIAGRAM_KW_EARLY = {
            'diagram', 'graph', 'figure', 'plot', 'sketch',
            'illustration', 'flow chart', 'flowchart', 'flow chart below',
            'the diagram', 'study it and answer',
            'chart below', 'graph below', 'figure below', 'diagram below',
            'reaction scheme', 'scheme below', 'deduce the structures',
            'mass spectrum', 'relative intensity', 'm/z',
            'match column', 'column a', 'table below',
            'find the area', 'find area', 'perimeter',
            'name of this figure', 'name of the figure', 'name of figure',
        }

        if (
            _raw_pdf_bytes
            and parsed_exam.get('questions')
            and ocr_processor.upload_needs_ocr(_raw_pdf_bytes, file.filename or "upload.pdf")
            and _parsed_tree_needs_diagram(parsed_exam['questions'])
        ):
            try:
                import io as _io
                from pdf2image import convert_from_bytes as _c2b

                rendered = _c2b(_raw_pdf_bytes, dpi=150)
                for pg_idx, page_img in enumerate(rendered):
                    if pg_idx in pdf_embedded_images:
                        continue
                    buf = _io.BytesIO()
                    page_img.convert("RGB").save(buf, format="PNG")
                    pdf_embedded_images[pg_idx] = [{
                        'data': buf.getvalue(),
                        'name': f'scan_page_{pg_idx + 1}.png',
                    }]
                logger.info(
                    "Scanned exam: attached %d page image(s) for diagram preservation",
                    len(rendered),
                )
            except Exception as _se:
                logger.warning(f"Scanned page render failed: {_se}")

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

        _diagram_kw = {
            'diagram', 'graph', 'figure', 'plot', 'sketch',
            'illustration', 'flow chart', 'flowchart', 'flow chart below',
            'the diagram', 'study it and answer',
            'outlines some of the process',
            'chart below', 'graph below', 'figure below', 'diagram below',
            'reaction scheme', 'scheme below', 'deduce the structures',
            'mass spectrum', 'relative intensity', 'm/z',
            'match column', 'column a', 'table below',
            'area of', 'find the area', 'find area', 'perimeter', 'parameter',
            'paramiter', 'name of this figure', 'name of the figure',
            'name of figure', 'square', 'rectangle', 'triangle', 'parallelogram',
            'rhombus', 'trapezoid', 'circle', 'shape',
        }

        def _question_needs_diagram(q_data: dict) -> bool:
            blob = (q_data.get("text") or "").lower()
            if any(kw in blob for kw in _diagram_kw):
                return True
            return any(
                _question_needs_diagram(sub)
                for sub in q_data.get("sub_questions") or []
            )

        def _persist_parsed_question(
            question_data: dict,
            *,
            parent_id: Optional[str] = None,
            outline_level: int = 1,
            q_idx: int = 0,
        ) -> None:
            from ocr.text_rich_content import normalize_exam_ocr_text, ocr_text_to_rich_content

            raw_text = question_data.get("text") or ""
            q_text = _normalize_text_for_storage(normalize_exam_ocr_text(raw_text))
            q_rich = ocr_text_to_rich_content(q_text) if q_text.strip() else None
            label = (question_data.get("label") or "").strip()
            sub_list = question_data.get("sub_questions") or []
            q_type = "multi-part" if sub_list else "standard"
            new_question = models.Question(
                exam_id=new_exam.id,
                number=question_data["number"],
                text=q_text,
                rich_content=json.dumps(q_rich) if q_rich else None,
                points=question_data["points"],
                outline_level=outline_level,
                outline_title=label or None,
                parent_question_id=parent_id,
                question_type=q_type,
            )
            db.add(new_question)
            db.flush()

            if parent_id is None:
                q_page_num = question_data.get("page_num", q_idx)
                if q_page_num in pdf_embedded_images and _question_needs_diagram(question_data):
                    import io as _io
                    from PIL import Image as _PILImg

                    for img_idx, img_info in enumerate(pdf_embedded_images[q_page_num]):
                        try:
                            raw_data = img_info["data"]
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
                            logger.warning(
                                f"Could not save diagram for Q{question_data['number']}: {_e}"
                            )

            for step_data in question_data.get("gold_solution_steps") or []:
                expr = _normalize_text_for_storage(
                    normalize_exam_ocr_text(step_data.get("expression") or "")
                )
                db.add(
                    models.GoldSolutionStep(
                        question_id=new_question.id,
                        step_number=step_data["step_number"],
                        description=step_data["description"],
                        expression=expr,
                        points=step_data["points"],
                        required=step_data["required"],
                    )
                )

            for sub_idx, sub_data in enumerate(question_data.get("sub_questions") or [], start=1):
                sub_payload = dict(sub_data)
                sub_payload["number"] = sub_idx
                _persist_parsed_question(
                    sub_payload,
                    parent_id=new_question.id,
                    outline_level=outline_level + 1,
                )

        for q_idx, question_data in enumerate(parsed_exam["questions"]):
            _persist_parsed_question(question_data, q_idx=q_idx)

        new_exam.total_points = _calculate_exam_total_points_db(db, new_exam.id)
        db.commit()
        db.refresh(new_exam)

        return {
            "message": "Exam uploaded and parsed successfully",
            "exam_id": new_exam.id,
            "title": new_exam.title,
            "questions_found": len(parsed_exam['questions']),
            "total_points": new_exam.total_points
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
    """Serve a question attachment file (image, etc.). Public when exam is published; otherwise requires course access."""
    att = db.query(models.QuestionAttachment).filter(models.QuestionAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")

    allowed = False
    if not att.question_id:
        # Temp upload before question is saved — require auth only
        if credentials:
            try:
                get_current_user(credentials, db)
                allowed = True
            except Exception:
                pass
        if not allowed:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        question = db.query(models.Question).filter(models.Question.id == att.question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="Not found")
        exam = db.query(models.Exam).filter(models.Exam.id == question.exam_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Not found")
        if exam.is_published:
            allowed = True
        elif credentials:
            try:
                user = get_current_user(credentials, db)
                allowed = _user_can_view_exam(db, user, exam)
            except Exception:
                pass
        if not allowed:
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
    
    questions_data = _build_exam_questions_tree_response(
        list(exam.questions),
        include_attachments=True,
        include_embedded=True,
    )
    
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


@app.post("/api/exams/{exam_id}/preview-answer-key")
async def preview_exam_answer_key(
    exam_id: str,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Preview how an uploaded marking scheme / answer key aligns to existing questions.
    Does not modify the exam.
    """
    if current_user.role != models.UserRole.PROFESSOR:
        raise HTTPException(status_code=403, detail="Only professors can upload answer keys")

    exam = (
        db.query(models.Exam)
        .options(selectinload(models.Exam.questions))
        .filter(models.Exam.id == exam_id)
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    from answer_key_aligner import (
        align_answer_key,
        build_exam_tree_for_alignment,
        parse_answer_key_text,
    )

    text = await _read_upload_file_as_text(file)
    key_tree = parse_answer_key_text(text)
    if not key_tree:
        raise HTTPException(
            status_code=400,
            detail=(
                "No answer sections found. For handwritten keys use Q1, Q2, … headings "
                "or upload a clear scan/PDF (Mathpix OCR). Typed keys can use "
                "Question 1 / Gold Solution / Model Answer format."
            ),
        )

    exam_tree = build_exam_tree_for_alignment(list(exam.questions))
    preview = align_answer_key(exam_tree, key_tree)
    if not preview["matched"] and preview["summary"]["key_sections_found"] > 0:
        preview["warnings"] = [
            "Answer key sections were read but none matched an exam question number. "
            "Check that Q numbers in the key align with the exam (e.g. key has Q1–Q4 but exam has Q6)."
        ]
    preview["exam_id"] = exam_id
    preview["exam_title"] = exam.title
    return preview


@app.post("/api/exams/{exam_id}/upload-answer-key")
async def upload_exam_answer_key(
    exam_id: str,
    file: UploadFile = File(...),
    overwrite: bool = Form(True),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a separate marking scheme and align gold solutions to existing questions.

    Questions without a matching answer-key section are left unchanged.
    """
    if current_user.role != models.UserRole.PROFESSOR:
        raise HTTPException(status_code=403, detail="Only professors can upload answer keys")

    exam = (
        db.query(models.Exam)
        .options(selectinload(models.Exam.questions))
        .filter(models.Exam.id == exam_id)
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    from answer_key_aligner import (
        align_answer_key,
        build_exam_tree_for_alignment,
        parse_answer_key_text,
    )

    text = await _read_upload_file_as_text(file)
    key_tree = parse_answer_key_text(text)
    if not key_tree:
        raise HTTPException(
            status_code=400,
            detail=(
                "No answer sections found. For handwritten keys use Q1, Q2, … headings "
                "or upload a clear scan/PDF (Mathpix OCR). Typed keys can use "
                "Question 1 / Gold Solution / Model Answer format."
            ),
        )

    exam_tree = build_exam_tree_for_alignment(list(exam.questions))
    alignment = align_answer_key(exam_tree, key_tree)
    if not alignment["matched"] and alignment["summary"]["key_sections_found"] > 0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Found {alignment['summary']['key_sections_found']} answer section(s) "
                f"(Q{', Q'.join(str(q['number']) for q in key_tree if q.get('number') is not None)}), "
                "but none matched this exam's question numbers. "
                "Ensure the key uses the same question numbers as the exam."
            ),
        )
    updated = _apply_answer_key_matches(
        db,
        alignment["matched"],
        overwrite=overwrite,
    )
    db.commit()

    return {
        "message": "Answer key aligned and applied",
        "exam_id": exam_id,
        "questions_updated": updated,
        "matched_count": len(alignment["matched"]),
        "unmatched_exam_count": len(alignment["unmatched_exam_questions"]),
        "unmatched_key_count": len(alignment["unmatched_key_sections"]),
        "summary": alignment["summary"],
    }


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
    
    # Total points recalculated from saved tree after questions are written.
    exam.total_points = sum(_schema_question_tree_points(q) for q in exam_data.questions)
    
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

    for question_data in exam_data.questions:
        _save_question_tree_from_schema(
            db,
            exam.id,
            exam_attach_dir,
            question_data,
            protected_att_paths=_protected_att_paths,
        )
    
    exam.total_points = _calculate_exam_total_points_db(db, exam.id)
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
    enrollments = (
        db.query(models.CourseEnrollment)
        .filter(
            models.CourseEnrollment.course_id == course.id,
            models.CourseEnrollment.status == models.EnrollmentStatus.APPROVED,
        )
        .all()
    )
    for en in enrollments:
        notifications_service.push_notification(
            db,
            user_id=en.student_id,
            kind="exam_published",
            title=f"New exam published: {exam.title}",
            body=f"Open it from My Exams — {course.name} ({course.code}).",
            link=f"/take-exam/{exam.id}",
        )
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

        # Extract Recharts-style graph nodes from exam builder
        elif node_type == 'graph':
            attrs = node.get('attrs') or {}
            embedded_items.append({
                'contentType': 'graph',
                'contentData': {
                    'graphType': attrs.get('graphType', 'line'),
                    'data': attrs.get('data') or [],
                    'title': attrs.get('title', ''),
                    'xLabel': attrs.get('xLabel', ''),
                    'yLabel': attrs.get('yLabel', ''),
                },
                'positionData': None,
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
    
    raw = unescape(html_content)
    latex_content = None
    all_latex = []
    for attr_match in re.finditer(r'data-latex=(["\'])(.*?)\1', raw, re.DOTALL):
        chunk = unescape(attr_match.group(2)).strip()
        if chunk:
            all_latex.append(chunk)
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
        matches = re.findall(pattern, raw, re.DOTALL)
        if matches:
            all_latex.extend([unescape(m.strip()) for m in matches if m and m.strip()])
    
    if all_latex:
        latex_content = "\n".join([m.strip() for m in all_latex if m.strip()])
    
    text_content = re.sub(r'<[^>]+>', '', raw)
    text_content = unescape(text_content).strip()
    
    if text_content.lower() in ['type your answer here...', '']:
        text_content = ''
    
    if not text_content and latex_content:
        text_content = latex_content
    
    return text_content, latex_content


def _submission_answer_meta(
    question: Optional[models.Question],
    questions_by_id: dict,
) -> dict:
    """Labels for sub-question answers in submission review UI."""
    if not question:
        return {
            "parentQuestionId": None,
            "outlineTitle": None,
            "displayLabel": None,
        }
    pid = getattr(question, "parent_question_id", None)
    outline = getattr(question, "outline_title", None)
    if pid:
        parent = questions_by_id.get(pid)
        pnum = parent.number if parent else "?"
        part = (outline or "").strip() or f"({question.number})"
        return {
            "parentQuestionId": pid,
            "outlineTitle": outline,
            "displayLabel": f"Q{pnum} · {part}",
        }
    return {
        "parentQuestionId": None,
        "outlineTitle": outline,
        "displayLabel": f"Q{question.number}",
    }


def _submitted_answer_response(
    *,
    question_id: str,
    question_number: int,
    questions_by_id: dict,
    extracted_text: Optional[str],
    extracted_latex: Optional[str],
    grading_result: Optional[schemas.GradingResultResponse],
) -> schemas.SubmittedAnswerResponse:
    question = questions_by_id.get(question_id)
    meta = _submission_answer_meta(question, questions_by_id)
    disp_plain, disp_latex = _polish_submission_answer_fields(extracted_text, extracted_latex)
    qnum = int(question.number) if question else int(question_number or 0)
    return schemas.SubmittedAnswerResponse(
        questionId=str(question_id),
        questionNumber=qnum,
        parentQuestionId=meta["parentQuestionId"],
        outlineTitle=meta["outlineTitle"],
        displayLabel=meta["displayLabel"],
        extractedText=extracted_text,
        extractedLatex=extracted_latex,
        extractedTextDisplay=disp_plain,
        extractedMathLatex=disp_latex,
        extractedSteps=[],
        gradingResult=grading_result,
    )


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


def _polish_submission_answer_fields(
    extracted_text: Optional[str],
    extracted_latex: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Parallel display fields for OCR / typed answers (SymPy + cleanup)."""
    from ocr.ocr_transcript_polish import polish_ocr_for_submission_display

    p = polish_ocr_for_submission_display(extracted_text, extracted_latex)
    d = (p.display_plain or "").strip() or None
    m = (p.math_latex or "").strip() or None
    return d, m


def _step_result_response_for_api(step) -> schemas.StepResultResponse:
    from ocr.ocr_transcript_polish import polish_step_snippet

    rd, rml = polish_step_snippet(step.received)
    ed, ed_latex = polish_step_snippet(step.expected)
    return schemas.StepResultResponse(
        id=step.id,
        stepNumber=step.step_number,
        isCorrect=step.is_correct,
        score=step.score,
        maxScore=step.max_score,
        feedback=step.feedback or "",
        expected=step.expected,
        received=step.received,
        expectedDisplay=ed,
        expectedMathLatex=ed_latex,
        receivedDisplay=rd,
        receivedMathLatex=rml,
    )


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
                _submitted_answer_response(
                    question_id=str(question_id or question.id),
                    question_number=int(question_number if question_number is not None else question.number),
                    questions_by_id=questions_by_id,
                    extracted_text=display,
                    extracted_latex=latex_vis,
                    grading_result=None,
                )
            )
        else:
            # Question id/number no longer on exam — still return the payload so instructors see work
            try:
                qnum = int(question_number) if question_number is not None else 0
            except (TypeError, ValueError):
                qnum = 0
            answers.append(
                _submitted_answer_response(
                    question_id=str(question_id or "unknown"),
                    question_number=qnum,
                    questions_by_id=questions_by_id,
                    extracted_text=display,
                    extracted_latex=latex_vis,
                    grading_result=None,
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

    # Mathpix / LaTeX arrays use \\ between rows — treat each row as a step.
    row_sep = re.sub(r"\s*\\\\\s*", "\n<<LATEX_ROW>>\n", text)
    if "<<LATEX_ROW>>" in row_sep:
        row_parts = [p.strip() for p in row_sep.split("<<LATEX_ROW>>") if p.strip()]
        row_parts = [
            re.sub(r"^\\begin\{[^}]+\}(\{[^}]*\})?", "", p).strip()
            for p in row_parts
        ]
        row_parts = [re.sub(r"\\end\{[^}]+\}", "", p).strip() for p in row_parts]
        row_parts = [p for p in row_parts if p and len(p) > 1]
        if len(row_parts) >= 2:
            expanded: List[str] = []
            for row in row_parts:
                if "=" in row:
                    expanded.extend(_finalize_latex_step_segments(row))
                else:
                    expanded.append(row)
            if len(expanded) >= 2:
                return expanded

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

        # 1a2) Prose rubric phrases common in OCR (Factor… Set each factor… Solve for…)
        prose_split = re.compile(
            r"\s+(?=(?:Step\s*\d+\s*:?\s*"
            r"|Factor(?:ing)?(?:\s+the(?:\s+quadratic)?)?\s*"
            r"|(?i:Set each factor)\b\s*"
            r"|(?i:Solve(?:\s+for\s+\w+)?)\s*:?\s*"
            r"|Therefore\b|Thus\b|Hence\b|(?i:Substitute(?:\s+into)?)\b\s*))"
        )
        prose_parts = [p.strip() for p in prose_split.split(single_line) if p.strip()]
        if len(prose_parts) >= 2:
            return prose_parts

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


def _resolve_exam_question_for_answer(
    questions: List[models.Question],
    question_id: Optional[str],
    question_number: Optional[int],
) -> Optional[models.Question]:
    """Match a submitted answer row to an exam question (prefer id; avoid sub-part number clashes)."""
    if question_id:
        hit = next((q for q in questions if q.id == question_id), None)
        if hit:
            return hit
    if question_number is not None:
        return next(
            (
                q
                for q in questions
                if q.number == question_number and q.parent_question_id is None
            ),
            None,
        ) or next((q for q in questions if q.number == question_number), None)
    return None


def _split_multipart_page_text(page_text: str, sub_count: int) -> List[str]:
    """Split one page into sub-parts using (a), i., A., etc. when possible."""
    if sub_count <= 1:
        t = (page_text or "").strip()
        return [t] if t else []
    text = (page_text or "").strip()
    if not text:
        return [""] * sub_count

    split_patterns = [
        r"(?mi)^\s*\(([a-z])\)\s*",
        r"(?mi)^\s*\((i{1,3}|iv|vi{0,3}|ix|x)\)\s*",
        r"(?mi)^\s*(i{1,3}|iv|vi{0,3}|ix|x)\.\s+",
        r"(?mi)^\s*([A-E])\.\s+",
        r"(?mi)^\s*([a-z])\)\s+",
        r"(?mi)^\s*(\d{1,2})\.\s+",
    ]
    for pat in split_patterns:
        pattern = re.compile(pat)
        matches = list(pattern.finditer(text))
        if len(matches) >= sub_count:
            parts: List[str] = []
            for i in range(sub_count):
                start = matches[i].start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
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
        r"(?mi)^[^\w\n]{0,8}(?:question|q\.?|problem|exercise)\s*(\d{1,2})\s*[\.\):,\-]?(?:\s+|$)",
        text,
    ):
        num = int(m.group(1))
        if num in want:
            hits.append((m.start(), num))
    if len(hits) < 2:
        for m in re.finditer(
            r"(?mi)^[^\w\n]{0,8}Q\s*(\d{1,2})\s*[\.\):,\-]?(?:\s+|$)",
            text,
        ):
            num = int(m.group(1))
            if num in want:
                hits.append((m.start(), num))
    if len(hits) < 2:
        for m in re.finditer(
            r"(?mi)^[^\d\n]{0,8}(\d{1,2})\s*[\.\):,\-–]?(?:\s+|$)",
            text,
        ):
            num = int(m.group(1))
            if num in want:
                hits.append((m.start(), num))
    if len(hits) < 2:
        for m in re.finditer(
            r"(?mi)^[^\d\n]{0,8}(\d{1,2})\s*[\.\):,\-–]\s*$",
            text,
        ):
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


def _split_monolithic_by_line_item_numbers(
    text: str, top_level: List[models.Question]
) -> Optional[List[str]]:
    """
    OCR-friendly split: lines that start with an item number in the exam (1. 2) 3: …).
    More permissive than _split_monolithic_solution_text; helps when many answers sit on few pages.
    """
    ordered = sorted(top_level, key=lambda q: q.number)
    n = len(ordered)
    if n <= 1:
        return None
    want = {q.number for q in ordered}
    t = text or ""
    pat = re.compile(
        r"(?mi)^[^\d\n]{0,8}(\d{1,2})\s*[\.\):,\-–]?(?:\s+|$)"
    )
    hits: List[Tuple[int, int]] = []
    for m in pat.finditer(t):
        num = int(m.group(1))
        if num not in want:
            continue
        hits.append((m.start(), num))
    if len(hits) < 2:
        return None
    hits.sort(key=lambda x: x[0])
    dedup: List[Tuple[int, int]] = []
    seen_nums: set = set()
    for pos, num in hits:
        if num in seen_nums:
            continue
        seen_nums.add(num)
        dedup.append((pos, num))
    hits = dedup
    by_num: dict = {}
    for i, (pos, num) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(t)
        by_num[num] = t[pos:end].strip()
    out: List[str] = []
    for q in ordered:
        out.append(by_num.get(q.number, "").strip())
    if sum(1 for c in out if c) < 2:
        return None
    return out


def _split_monolithic_by_equal_blocks(text: str, n: int) -> Optional[List[str]]:
    """
    Last-resort split: exactly N non-empty paragraphs, or exactly N substantive lines.
    Helps scanned homework where answers are stacked with blank lines but no 'Q2' labels.
    If there are more than N paragraphs, the first N-1 stay separate and the rest merge
    into the last block (common when the final answer has extra blank lines).
    """
    if n <= 1:
        return None
    t = (text or "").strip()
    if not t:
        return None
    paras = [p.strip() for p in re.split(r"\n{2,}", t) if p.strip()]
    if len(paras) >= n:
        if len(paras) == n:
            return paras
        return paras[: n - 1] + ["\n\n".join(paras[n - 1 :])]
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    lines = [ln for ln in lines if len(ln) >= 2]
    if len(lines) == n:
        return lines
    return None


def _split_monolithic_by_flow_bins(text: str, n: int) -> Optional[List[str]]:
    """
    Final fallback for noisy OCR: split ordered lines into N sequential bins.
    This keeps answer order when explicit question labels are unreadable.
    """
    if n <= 1:
        return None
    t = (text or "").strip()
    if not t:
        return None
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    lines = [ln for ln in lines if len(ln) >= 2]
    if len(lines) < max(6, n):
        return None
    step = max(1, math.ceil(len(lines) / n))
    out: List[str] = []
    for i in range(n):
        start = i * step
        end = (i + 1) * step if i < n - 1 else len(lines)
        chunk = "\n".join(lines[start:end]).strip()
        out.append(chunk)
    if sum(1 for c in out if c.strip()) < max(2, n // 3):
        return None
    return out


def _chunk_non_empty_count(chunks: Optional[List[str]]) -> int:
    if not chunks:
        return 0
    return sum(1 for c in chunks if (c or "").strip())


def _resolve_monolithic_chunks(
    text: str, top_level: List[models.Question]
) -> Tuple[Optional[List[str]], str]:
    """
    Try heading-based split first, then equal block/line count. Returns (chunks, method)
    where method is 'headings', 'blocks', or ''.
    """
    ordered = sorted(top_level, key=lambda q: q.number)
    n = len(ordered)
    if n <= 1:
        st = (text or "").strip()
        return ([st] if st else []), "single"
    try:
        from answer_key_aligner import split_student_work_by_question_number

        by_q_markers = split_student_work_by_question_number(
            text, [q.number for q in ordered]
        )
        if (
            by_q_markers is not None
            and len(by_q_markers) == n
            and _chunk_non_empty_count(by_q_markers) >= max(2, n // 3)
        ):
            return by_q_markers, "q_markers"
    except Exception:
        pass
    by_headings = _split_monolithic_solution_text(text, ordered)
    if (
        by_headings is not None
        and len(by_headings) == n
        and _chunk_non_empty_count(by_headings) >= max(2, n // 3)
    ):
        return by_headings, "headings"
    by_line_items = _split_monolithic_by_line_item_numbers(text, ordered)
    if (
        by_line_items is not None
        and len(by_line_items) == n
        and _chunk_non_empty_count(by_line_items) >= max(2, n // 3)
    ):
        return by_line_items, "line_numbers"
    by_blocks = _split_monolithic_by_equal_blocks(text, n)
    if (
        by_blocks is not None
        and len(by_blocks) == n
        and _chunk_non_empty_count(by_blocks) >= max(2, n // 3)
    ):
        return by_blocks, "blocks"
    by_flow = _split_monolithic_by_flow_bins(text, n)
    if by_flow is not None and len(by_flow) == n:
        return by_flow, "flow_bins"
    return None, ""


def _monolithic_chunks_usable(
    chunks: Optional[List[str]], tls: List[models.Question]
) -> bool:
    if not chunks or len(chunks) != len(tls):
        return False
    return any((c or "").strip() for c in chunks)


def _strip_scan_app_watermarks(text: str) -> str:
    """Remove common phone-scanner branding lines from OCR text.

    Handles OCR noise around the branding (stray primes / dots / spaces) — e.g.
    `scam's'c'a'n'n'er` and `Sca nn ed with CamScanner` both match.
    """
    if not text or not text.strip():
        return text
    out_lines: List[str] = []
    for line in text.splitlines():
        sl = line.strip()
        if not sl:
            out_lines.append(line)
            continue
        # Collapse OCR noise so brand names match even when primes/dots/spaces
        # have been sprinkled between every letter by an over-eager detector.
        normalised = re.sub(r"[^A-Za-z]+", "", sl).lower()
        if re.search(
            r"(camscanner|scannedwith|adobescan|tinyscanner|microsoftlens|"
            r"geniusscan|scannerapp|notescan|officelens|clearscanner)",
            normalised,
        ):
            continue
        out_lines.append(line)
    return "\n".join(out_lines).strip()


def _preview_answer_excerpt(text: Optional[str], max_chars: int = 2400) -> Optional[str]:
    if not text or not str(text).strip():
        return None
    t = str(text).strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1].rstrip() + "…"


def _try_split_answer_pdf_across_questions(
    pdf_bytes: bytes,
    pdf_pages: List[str],
    tls: List[models.Question],
    ocr: OCRProcessor,
) -> Tuple[Optional[List[str]], str]:
    """
    When an answer PDF is not strictly one top-level question per page, join pages (or
    OCR the whole file) and split into one chunk per question using headings or blocks.
    Returns (chunks, method) with method from _resolve_monolithic_chunks, or (None, '').
    """
    if len(tls) <= 1:
        return None, ""
    needs_ocr = ocr.upload_needs_ocr(pdf_bytes, "answers.pdf")
    joined = ""
    if not needs_ocr:
        joined = "\n\n".join((p or "").strip() for p in pdf_pages).strip()
    chunks: Optional[List[str]] = None
    method = ""
    if joined:
        joined = _prepare_monolithic_split_text(_strip_scan_app_watermarks(joined))
        chunks, method = _resolve_monolithic_chunks(joined, tls)
    if _monolithic_chunks_usable(chunks, tls) and chunks is not None:
        chunks = [_strip_scan_app_watermarks(c or "") for c in chunks]
        return chunks, method
    chunks, method = None, ""
    n_pages = len(pdf_pages)
    n_tl = len(tls)
    needs_full_pdf_ocr = needs_ocr or n_pages == 1 or n_pages != n_tl
    if not needs_full_pdf_ocr:
        return None, ""
    try:
        ocr_result = ocr.extract_steps_from_file(
            pdf_bytes,
            "answers.pdf",
            fast=_ocr_use_fast_preview(ocr),
        )
        combined = (ocr_result.combined_text or "").strip()
    except Exception as ex:
        logger.warning("OCR for full answer PDF failed: %s", ex)
        combined = ""
    if not combined:
        return None, ""
    combined = _strip_scan_app_watermarks(combined)
    combined = _prepare_monolithic_split_text(combined)
    chunks, method = _resolve_monolithic_chunks(combined, tls)
    if _monolithic_chunks_usable(chunks, tls) and chunks is not None:
        chunks = [_strip_scan_app_watermarks(c or "") for c in chunks]
        return chunks, method
    return None, ""


def _part_to_tiptap_math_html(part: str) -> str:
    """Plain or LaTeX chunk → minimal TipTap HTML for storage."""
    from html import escape

    p = (part or "").strip()
    if not p:
        return ""
    if p.startswith("<"):
        return p
    if "\\" in p or "^" in p or "frac" in p or "sqrt" in p:
        return f'<div data-latex="{escape(p)}" data-type="block-math"></div>'
    return _plain_chunk_to_tiptap_html(p)


def _fan_out_multipart_typed_rows(
    answers_list: List[dict],
    exam: models.Exam,
) -> List[dict]:
    """
    When a single typed row for a multi-part question contains (a)...(b)...,
    split it onto sub-question IDs so grading aligns with rubric parts.
    """
    if not answers_list:
        return answers_list
    questions = list(exam.questions)
    by_id = {q.id: q for q in questions}
    subs_by_parent: Dict[str, List[models.Question]] = {}
    for q in questions:
        pid = getattr(q, "parent_question_id", None)
        if pid:
            subs_by_parent.setdefault(pid, []).append(q)
    for pid in subs_by_parent:
        subs_by_parent[pid].sort(key=lambda q: q.number)

    out: List[dict] = []
    consumed_qids: set = set()

    for entry in answers_list:
        qid = str(entry.get("questionId") or "")
        html = str(entry.get("typedAnswer") or "")
        if not html.strip():
            out.append(entry)
            continue
        if qid in consumed_qids:
            continue
        q = by_id.get(qid)
        parent_id = None
        if q:
            parent_id = q.parent_question_id or (
                q.id if subs_by_parent.get(q.id) else None
            )
        subs = subs_by_parent.get(parent_id or "", [])
        if len(subs) <= 1:
            out.append(entry)
            continue

        plain, latex = extract_math_from_html(html)
        source = (latex or plain or "").strip()
        if not source:
            out.append(entry)
            continue
        parts = _split_multipart_page_text(source, len(subs))
        if sum(1 for p in parts if (p or "").strip()) < 2:
            out.append(entry)
            continue

        for sub_q, part in zip(subs, parts):
            part = (part or "").strip()
            if not part:
                continue
            out.append(
                {
                    "questionId": sub_q.id,
                    "questionNumber": sub_q.number,
                    "typedAnswer": _part_to_tiptap_math_html(part),
                }
            )
        consumed_qids.add(qid)
        if qid not in {s.id for s in subs}:
            consumed_qids.add(qid)
        else:
            for s in subs:
                consumed_qids.add(s.id)

    return out if out else answers_list


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


def _plain_chunk_to_tiptap_html(chunk: str) -> str:
    """Plain text / OCR segment → minimal HTML for stored typed answers."""
    from html import escape

    t = (chunk or "").strip()
    if not t:
        return ""
    paras = [p.strip() for p in re.split(r"\n{2,}", t) if p.strip()]
    if len(paras) <= 1:
        inner = escape(t).replace("\n", "<br>")
        return f"<p>{inner}</p>"
    return "".join(
        "<p>" + escape(p).replace("\n", "<br>") + "</p>" for p in paras
    )


def _typed_split_skip_target(
    target_id: str,
    host_top_level_id: str,
    locked_question_ids: set,
) -> bool:
    """Do not overwrite another question's answer row when fanning out a monolithic paste."""
    if target_id == host_top_level_id:
        return False
    return target_id in locked_question_ids


def _dispatch_typed_chunk_to_top_level_question(
    chunk: str,
    top_q: models.Question,
    extra: List[dict],
    host_top_level_id: str,
    locked_question_ids: set,
) -> None:
    """
    Store one OCR/text segment onto a top-level question (and its sub-parts when present).
    """
    chunk = (chunk or "").strip()
    if not chunk:
        return
    subs = _sorted_subquestions(top_q)
    if subs:
        parts = _split_multipart_page_text(chunk, len(subs))
        for sub_q, part in zip(subs, parts):
            if _typed_split_skip_target(sub_q.id, host_top_level_id, locked_question_ids):
                continue
            body = _plain_chunk_to_tiptap_html((part or "").strip())
            if body:
                _append_typed_for_question(extra, sub_q, body)
        return
    if _typed_split_skip_target(top_q.id, host_top_level_id, locked_question_ids):
        return
    _append_typed_for_question(extra, top_q, _plain_chunk_to_tiptap_html(chunk))


def _expand_monolithic_typed_payload(
    answers_list: List[dict],
    exam: models.Exam,
) -> List[dict]:
    """
    If a student pastes a whole answer sheet into one top-level question's rich-text
    box (Q1…Qn headings or N paragraphs for N questions), split and assign rows.
    """
    if not answers_list or not isinstance(answers_list, list):
        return answers_list
    tls = _ordered_top_level_questions(list(exam.questions))
    if len(tls) <= 1:
        return answers_list
    top_level_ids = {t.id for t in tls}
    locked_question_ids = {
        str(e.get("questionId"))
        for e in answers_list
        if str(e.get("typedAnswer") or "").strip()
    }
    out: List[dict] = []
    for entry in answers_list:
        qid = str(entry.get("questionId") or "")
        raw_html = str(entry.get("typedAnswer") or "")
        if qid not in top_level_ids or not raw_html.strip():
            out.append(entry)
            continue
        text_content, latex_content = extract_math_from_html(raw_html)
        plain_parts = []
        if text_content:
            plain_parts.append(text_content)
        if latex_content:
            plain_parts.append(latex_content)
        plain = "\n\n".join(plain_parts).strip() if plain_parts else ""
        if not plain:
            out.append(entry)
            continue
        chunks, _ = _resolve_monolithic_chunks(plain, tls)
        if not _monolithic_chunks_usable(chunks, tls) or chunks is None:
            out.append(entry)
            continue
        expanded: List[dict] = []
        for top_q, chunk in zip(tls, chunks):
            if not (chunk or "").strip():
                continue
            before = len(expanded)
            _dispatch_typed_chunk_to_top_level_question(
                chunk,
                top_q,
                expanded,
                host_top_level_id=qid,
                locked_question_ids=locked_question_ids,
            )
            if len(expanded) == before:
                continue
        if len(expanded) < 2:
            out.append(entry)
            continue
        out.extend(expanded)
    return out


def _ingest_image_as_full_exam_monolith_if_detected(
    raw: bytes,
    filename: str,
    exam: models.Exam,
    ocr: OCRProcessor,
) -> Optional[Tuple[List[dict], List[dict]]]:
    """
    One photo (PNG/JPEG/…) under a question slot that OCRs to a multi-section answer sheet.
    """
    stem = Path(filename or "").stem
    if not stem.startswith("q_"):
        return None
    tls = _ordered_top_level_questions(list(exam.questions))
    if len(tls) <= 1:
        return None
    fn_lower = (filename or "").lower()
    if fn_lower.endswith(".pdf"):
        return None
    if not fn_lower.endswith(
        (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff")
    ):
        head = raw[:12] if raw else b""
        is_webp = len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
        if not (
            head.startswith(b"\x89PNG")
            or head.startswith(b"\xff\xd8\xff")
            or head.startswith(b"GIF8")
            or is_webp
        ):
            return None
    try:
        ocr_result = ocr.extract_steps_from_file(raw, filename or "upload.png")
        combined = (ocr_result.combined_text or "").strip()
    except Exception as ex:
        logger.warning("OCR for monolithic image %s: %s", filename, ex)
        return None
    if not combined:
        return None
    chunks, _ = _resolve_monolithic_chunks(combined, tls)
    if not _monolithic_chunks_usable(chunks, tls) or not chunks:
        return None
    extra_typed: List[dict] = []
    empty_locked: set = set()
    for top_q, chunk in zip(tls, chunks):
        if not (chunk or "").strip():
            continue
        _dispatch_typed_chunk_to_top_level_question(
            chunk,
            top_q,
            extra_typed,
            host_top_level_id="",
            locked_question_ids=empty_locked,
        )
    if len(extra_typed) < 2:
        return None
    return (extra_typed, [])


def _ocr_text_likely_scan_app_noise(combined: str) -> bool:
    """Phone scan apps often watermark OCR; those strings are not student work."""
    t = combined or ""
    if len(t) < 40:
        return False
    return bool(
        re.search(
            r"(?i)(camscanner|scan\s*hero|tiny\s*scanner|adobe\s*scan|microsoft\s+lens)",
            t,
        )
    )


def _ocr_chunk_is_usable(text: str, ocr: OCRProcessor) -> bool:
    """True when pre-routed OCR text should be stored instead of re-OCRing a PDF page."""
    t = (text or "").strip()
    if len(t) < 15 or _ocr_text_likely_scan_app_noise(t):
        return False
    if ocr._text_is_clean(t):
        return True
    if re.search(r"[\$\\]|\\frac|\\begin|\\sqrt", t):
        return len(t) >= 20
    return len(t) >= 40 and bool(re.search(r"[A-Za-z0-9]", t))


def _store_routed_text_as_typed_answers(
    text: str,
    top_q: models.Question,
    extra_typed_answers: List[dict],
    ocr: OCRProcessor,
) -> None:
    """Persist routed OCR / embedded text onto the target question (and sub-parts)."""
    text = (text or "").strip()
    if not text:
        return
    subs = _sorted_subquestions(top_q)

    def _body_for_chunk(chunk: str) -> str:
        chunk = (chunk or "").strip()
        if not chunk:
            return ""
        if ocr._text_is_clean(chunk):
            return chunk
        return _plain_chunk_to_tiptap_html(chunk)

    if subs:
        parts = _split_multipart_page_text(text, len(subs))
        for sub_q, part in zip(subs, parts):
            body = _body_for_chunk(part)
            if body:
                _append_typed_for_question(extra_typed_answers, sub_q, body)
        return
    body = _body_for_chunk(text)
    if body:
        _append_typed_for_question(extra_typed_answers, top_q, body)


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
    page_text = (page_text or "").strip()
    if ocr._text_is_clean(page_text) or _ocr_chunk_is_usable(page_text, ocr):
        _store_routed_text_as_typed_answers(
            page_text, top_q, extra_typed_answers, ocr
        )
        return
    subs = _sorted_subquestions(top_q)
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
        imgs = _c2b(page_buf.read(), dpi=getattr(ocr, "dpi", 360) or 360)
        if not imgs:
            return
        img_buf = _io.BytesIO()
        imgs[0].save(img_buf, format="PNG")
        png_bytes = img_buf.getvalue()
        ocr_result = ocr.extract_steps_from_file(png_bytes, f"page{page_idx}.png")
        combined = (ocr_result.combined_text or "").strip() or "\n".join(
            s for s in ocr_result.steps if s.strip()
        )
        combined = _strip_scan_app_watermarks(combined)
        ocr_is_usable = (
            bool(combined)
            and len(combined) > 30
            and not _ocr_text_likely_scan_app_noise(combined)
        )
        # Always keep the rendered page as an image record so the grader can
        # re-OCR it at grade time / instructors can review the original scan.
        target = subs[0] if subs else top_q
        safe_name = f"q_{target.id}_pdf{page_idx}.png"
        extra_image_records.append({"filename": safe_name, "data": png_bytes})

        # Also save the OCR transcript as a typed answer so the marked report
        # shows the student's work even when (a) the question has no gold
        # steps configured or (b) the grader can't compare to a reference.
        if ocr_is_usable:
            if subs:
                chunks = _split_multipart_page_text(combined, len(subs))
                for sub_q, chunk in zip(subs, chunks):
                    body = _plain_chunk_to_tiptap_html((chunk or "").strip())
                    if body:
                        _append_typed_for_question(extra_typed_answers, sub_q, body)
            else:
                body = _plain_chunk_to_tiptap_html(combined)
                if body:
                    _append_typed_for_question(extra_typed_answers, top_q, body)
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
    pdf_pages = _resolve_pdf_pages_for_routing(pdf_bytes, ocr)
    tls = _ordered_top_level_questions(list(exam.questions))
    if not tls:
        return extra_typed, extra_img

    if len(tls) > 1:
        chunks, _split_m = _try_split_answer_pdf_across_questions(
            pdf_bytes, pdf_pages, tls, ocr
        )
        if _monolithic_chunks_usable(chunks, tls) and chunks is not None:
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


def _pdf_page_count(pdf_bytes: bytes) -> int:
    try:
        import io as _io
        from pypdf import PdfReader

        return len(PdfReader(_io.BytesIO(pdf_bytes)).pages)
    except Exception:
        pass
    try:
        from pdf2image import convert_from_bytes as _c2b

        # Low DPI — only need a page count, not OCR quality.
        return len(_c2b(pdf_bytes, dpi=72))
    except Exception:
        return 0


def _ocr_use_fast_preview(ocr: OCRProcessor) -> bool:
    """Use Mathpix/full OCR for previews when a cloud provider is configured."""
    cloud = getattr(ocr, "cloud", None)
    if cloud is not None:
        return not bool(cloud.active_provider_name)
    return True


def _resolve_pdf_pages_for_routing(
    pdf_bytes: bytes, ocr: OCRProcessor
) -> List[str]:
    """
    Per-page text for answer-PDF routing. Scanned/handwritten pages go through
    Mathpix (or local OCR fallback), not unreliable embedded PDF text.
    """
    page_count = _pdf_page_count(pdf_bytes)
    if page_count <= 0:
        return []
    embedded = ocr._best_pdf_text_pages(pdf_bytes)
    while len(embedded) < page_count:
        embedded.append("")
    needs_ocr = ocr.upload_needs_ocr(pdf_bytes, "answers.pdf")
    pages: List[str] = []
    for i in range(page_count):
        direct = embedded[i] if i < len(embedded) else ""
        if needs_ocr or not ocr._text_is_clean(direct):
            ocr_text = _ocr_excerpt_single_pdf_page(pdf_bytes, i, ocr)
            pages.append(_strip_scan_app_watermarks(ocr_text or direct))
        else:
            pages.append(direct)
    return pages


def _prepare_monolithic_split_text(text: str) -> str:
    """Normalize handwritten OCR markers (Q1, $a_{2}$., etc.) before section splitting."""
    try:
        from answer_key_aligner import _normalize_handwritten_key_markers

        normalized = _normalize_handwritten_key_markers(text)
        return re.sub(r"<<QMARKER:(\d+)>>", r"Question \1\n", normalized)
    except Exception:
        return text


def _ocr_excerpt_single_pdf_page(
    pdf_bytes: bytes, page_idx: int, ocr: OCRProcessor
) -> str:
    """Run OCR on one PDF page for preview excerpts (review UI)."""
    try:
        import io as _io
        from pdf2image import convert_from_bytes as _c2b

        base_dpi = int(getattr(ocr, "dpi", 360) or 360)
        dpi = max(240, min(420, base_dpi))
        imgs: list = []
        try:
            from pypdf import PdfReader as _PR, PdfWriter as _PW

            reader = _PR(_io.BytesIO(pdf_bytes))
            if page_idx >= len(reader.pages):
                return ""
            writer = _PW()
            writer.add_page(reader.pages[page_idx])
            buf = _io.BytesIO()
            writer.write(buf)
            buf.seek(0)
            imgs = _c2b(buf.read(), dpi=dpi)
        except Exception:
            imgs = _c2b(
                pdf_bytes,
                dpi=dpi,
                first_page=page_idx + 1,
                last_page=page_idx + 1,
            )
        if not imgs:
            return ""
        ib = _io.BytesIO()
        imgs[0].save(ib, format="PNG")
        res = ocr.extract_steps_from_file(
            ib.getvalue(),
            f"preview_p{page_idx}.png",
            fast=_ocr_use_fast_preview(ocr),
        )
        return _strip_scan_app_watermarks((res.combined_text or "").strip())
    except Exception as ex:
        logger.debug("Preview OCR for PDF page %s: %s", page_idx, ex)
        return ""


def build_answer_pdf_preview(pdf_bytes: bytes, exam: models.Exam, ocr: OCRProcessor) -> dict:
    """
    Dry-run routing for the full-answer PDF (no DB writes). Used by the take-exam UI.
    """
    pdf_pages = _resolve_pdf_pages_for_routing(pdf_bytes, ocr)
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

    if n_tl > 1:
        chunks, split_method = _try_split_answer_pdf_across_questions(
            pdf_bytes, pdf_pages, tls, ocr
        )
        if _monolithic_chunks_usable(chunks, tls) and chunks is not None:
            if split_method == "blocks":
                warnings.append(
                    "Answers were split by matching the number of paragraphs (or lines) to the number of questions (no “Question 2”-style headings). Check that each block matches the right question."
                )
            if split_method == "line_numbers":
                warnings.append(
                    "Answers were split on line-leading numbers (1. 2) 3. …). Verify each section matches the intended exam question."
                )
            if split_method == "flow_bins":
                warnings.append(
                    "OCR labels were unclear, so answers were split by reading order into sequential blocks. Please verify each block is mapped to the intended question."
                )
            if split_method == "q_markers":
                warnings.append(
                    "Answers were matched to questions by Q1 / Q2 / … headings in your PDF."
                )
            for top_q, chunk in zip(tls, chunks):
                subs = _sorted_subquestions(top_q)
                rows.append(
                    {
                        "questionNumber": top_q.number,
                        "questionLabel": f"Q{top_q.number}",
                        "source": "multi_section_split",
                        "subParts": _preview_sub_parts_for_page(subs, chunk, ocr),
                        "answerExcerpt": _preview_answer_excerpt(chunk),
                        "pdfPage": None,
                    }
                )
            if n_pages == 1:
                if split_method == "blocks":
                    summary_mono = (
                        f"One PDF page split into {n_tl} parts by paragraph/line count; verify each block matches the intended question."
                    )
                elif split_method == "line_numbers":
                    summary_mono = (
                        f"One PDF page split into {n_tl} sections using numbered lines (1. 2. …); confirm each matches the right question."
                    )
                elif split_method == "flow_bins":
                    summary_mono = (
                        f"One PDF page split into {n_tl} sequential OCR blocks (labels unclear); confirm each block matches the right question."
                    )
                elif split_method == "q_markers":
                    summary_mono = (
                        f"One PDF page split into {n_tl} answers using Q1 / Q2 / … headings matched to exam question numbers."
                    )
                else:
                    summary_mono = (
                        f"One PDF page split into {n_tl} main questions via headings (1., Question 2, Q3, …)."
                    )
            else:
                if split_method == "blocks":
                    summary_mono = (
                        f"{n_pages} PDF pages were merged and split into {n_tl} answers by paragraph/line count; verify each block matches the intended question."
                    )
                elif split_method == "line_numbers":
                    summary_mono = (
                        f"{n_pages} PDF page(s) were merged and split into {n_tl} answers using numbered lines; confirm each section matches the right question."
                    )
                elif split_method == "flow_bins":
                    summary_mono = (
                        f"{n_pages} PDF page(s) were merged and split into {n_tl} sequential OCR blocks (labels unclear); confirm each block matches the right question."
                    )
                else:
                    summary_mono = (
                        f"{n_pages} PDF page(s) were merged and split into {n_tl} main questions via headings (1., Question 2, Q3, …)."
                    )
            return {
                "strategy": "monolithic",
                "pdfPageCount": n_pages,
                "topLevelCount": n_tl,
                "rows": rows,
                "warnings": warnings,
                "monolithicDetected": True,
                "summary": summary_mono,
            }

    for page_idx, top_q in enumerate(tls):
        if page_idx >= n_pages:
            rows.append(
                {
                    "questionNumber": top_q.number,
                    "questionLabel": f"Q{top_q.number}",
                    "source": "missing_page",
                    "subParts": [],
                    "answerExcerpt": None,
                    "pdfPage": None,
                    "note": f"No page {page_idx + 1} in PDF — nothing routed here.",
                }
            )
            continue
        page_text = pdf_pages[page_idx]
        subs = _sorted_subquestions(top_q)
        excerpt = _preview_answer_excerpt(page_text) if (page_text or "").strip() else None
        rows.append(
            {
                "questionNumber": top_q.number,
                "questionLabel": f"Q{top_q.number}",
                "source": f"pdf_page_{page_idx + 1}",
                "subParts": _preview_sub_parts_for_page(subs, page_text, ocr),
                "answerExcerpt": excerpt,
                "pdfPage": page_idx + 1,
            }
        )

    if n_pages > n_tl:
        warnings.append(
            f"{n_pages - n_tl} extra PDF page(s) after page {n_tl} will be ignored."
        )
    if n_tl > 1 and n_pages != n_tl:
        warnings.append(
            f"This PDF has {n_pages} page(s) for {n_tl} main questions; section detection did not match, so page 1 → Q{tls[0].number}, page 2 → Q{tls[1].number}, … Add headings like “1.” or “Question 2” on their own lines so answers can be reassigned automatically."
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
    chunks: Optional[List[str]] = None
    if ocr._text_is_clean(sole):
        chunks, _ = _resolve_monolithic_chunks(sole, tls)
    if not _monolithic_chunks_usable(chunks, tls):
        try:
            ocr_result = ocr.extract_steps_from_file(pdf_bytes, filename)
            combined = (ocr_result.combined_text or "").strip()
        except Exception:
            combined = ""
        if combined:
            chunks, _ = _resolve_monolithic_chunks(combined, tls)
    if not _monolithic_chunks_usable(chunks, tls):
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


    return (extra_typed, extra_img)


def _question_grading_context(question: models.Question) -> dict:
    """Keywords and metadata passed into the matching engine."""
    text = (question.text or "")[:2000]
    words = re.findall(r"[a-z]{4,}", text.lower())
    return {
        "question_type": getattr(question, "question_type", "standard") or "standard",
        "keywords": list(dict.fromkeys(words))[:24],
        "question_number": question.number,
        "outline_level": getattr(question, "outline_level", 1),
    }


def _gold_steps_for_question(question: models.Question) -> List[GraderStep]:
    gold_steps: List[GraderStep] = []
    for step in question.gold_steps or []:
        content = (
            step.latex if step.latex and step.latex.strip()
            else (step.expression or step.description or "")
        )
        if content.strip():
            gold_steps.append(
                GraderStep(
                    content=content.strip(),
                    points=float(step.points),
                    required=step.required,
                )
            )
    return gold_steps


def _extract_typed_answer_for_grading(typed_answer: str) -> Tuple[str, Optional[str]]:
    """
    Extract gradeable text from stored TipTap/HTML answers.
    Uses the same fallback as API display so OCR segments are not skipped.
    """
    text, latex = _typed_answer_for_api_display(str(typed_answer or ""))
    plain = (text or "").strip()
    latex_out = (latex or "").strip() or None
    return plain, latex_out


def _align_evaluations_to_gold_steps(
    grading_result: dict,
    gold_steps: List[GraderStep],
    student_steps: List[str],
) -> Tuple[List[Any], List[str]]:
    """
    One evaluation row per gold rubric step so the UI aligns reference steps
    with AI grading (handles single-block OCR answers).
    """
    from math_grader import StepEvaluation, StepStatus

    evaluations = grading_result.get("evaluations") or []
    steps_for_storage = grading_result.get("student_steps_for_storage") or student_steps
    strategies = grading_result.get("strategies_used") or []

    if (
        len(evaluations) == len(gold_steps)
        and strategies
        and strategies[0] == "prose_rubric"
    ):
        received = [
            steps_for_storage[i] if i < len(steps_for_storage) else "—"
            for i in range(len(gold_steps))
        ]
        return evaluations, received

    gold_to_match: Dict[int, Tuple[Any, str]] = {}
    for i, ev in enumerate(evaluations):
        gj = getattr(ev, "matched_gold_step", None)
        if gj is None or not (0 <= gj < len(gold_steps)):
            continue
        stu_text = (
            steps_for_storage[i]
            if i < len(steps_for_storage)
            else (student_steps[i] if i < len(student_steps) else "")
        )
        prev = gold_to_match.get(gj)
        if prev is None or ev.points_earned > prev[0].points_earned:
            gold_to_match[gj] = (ev, stu_text)

    aligned_evals: List[Any] = []
    aligned_received: List[str] = []
    for j, gold in enumerate(gold_steps):
        if j in gold_to_match:
            ev, stu_text = gold_to_match[j]
            aligned_evals.append(ev)
            aligned_received.append(stu_text or "—")
        else:
            aligned_evals.append(
                StepEvaluation(
                    StepStatus.INCORRECT,
                    0.0,
                    "No student step matched this rubric item",
                    matched_gold_step=j,
                )
            )
            aligned_received.append("—")

    return aligned_evals, aligned_received


def _grade_one_typed_answer_payload(
    db: Session,
    submission: models.Submission,
    questions: List[models.Question],
    answer_data: dict,
    graded_question_ids: set,
    feedback_prefix: str = "Auto-graded",
) -> float:
    """Grade a single typed-answer JSON row if not already graded."""
    typed_answer = answer_data.get("typedAnswer", "")
    if typed_answer is None or not str(typed_answer).strip():
        return 0.0

    question = _resolve_exam_question_for_answer(
        questions,
        answer_data.get("questionId"),
        answer_data.get("questionNumber"),
    )
    if not question:
        logger.warning(
            "Skipping typed answer — question not found (id=%s number=%s)",
            answer_data.get("questionId"),
            answer_data.get("questionNumber"),
        )
        return 0.0
    if question.id in graded_question_ids:
        return 0.0

    text_content, latex_content = _extract_typed_answer_for_grading(str(typed_answer))
    if not text_content and not latex_content:
        return 0.0

    answer_to_grade = latex_content if latex_content else text_content
    student_steps = parse_answer_into_steps(answer_to_grade)
    if not student_steps:
        student_steps = [answer_to_grade.strip()]

    return _grade_student_work_for_question(
        db,
        submission,
        question,
        student_steps,
        text_content,
        latex_content,
        feedback_prefix,
        graded_question_ids,
    )


def _store_grading_result_rows(
    db: Session,
    submission_id: str,
    question: models.Question,
    grading_result: dict,
    student_steps: List[str],
    gold_steps: List[GraderStep],
    extracted_text: str,
    extracted_latex: Optional[str],
    feedback_prefix: str,
) -> None:
    aligned_evals, aligned_received = _align_evaluations_to_gold_steps(
        grading_result, gold_steps, student_steps
    )
    aligned_total = round(
        sum(float(getattr(ev, "points_earned", 0) or 0) for ev in aligned_evals),
        2,
    )
    max_score = float(grading_result.get("max_score") or sum(g.points for g in gold_steps))
    percentage = (aligned_total / max_score * 100) if max_score > 0 else 0.0

    db_grading_result = models.GradingResult(
        submission_id=submission_id,
        question_id=question.id,
        extracted_text=extracted_text or None,
        extracted_latex=extracted_latex,
        score=aligned_total,
        max_score=max_score,
        feedback=f"{feedback_prefix}: {percentage:.1f}%",
        is_correct=percentage >= 70,
    )
    db.add(db_grading_result)
    db.flush()

    for idx, (received_text, evaluation) in enumerate(
        zip(aligned_received, aligned_evals), start=1
    ):
        matched_gold = None
        if evaluation.matched_gold_step is not None:
            matched_gold = gold_steps[evaluation.matched_gold_step].content
        display_received = received_text if received_text and received_text != "—" else ""
        db.add(
            models.StepResult(
                grading_result_id=db_grading_result.id,
                step_number=idx,
                student_text=display_received,
                is_correct=evaluation.status.value == "Correct",
                score=evaluation.points_earned,
                max_score=_step_result_max_score(evaluation, gold_steps, idx),
                feedback=evaluation.feedback,
                expected=matched_gold,
                received=display_received or received_text,
            )
        )


def _grade_student_work_for_question(
    db: Session,
    submission: models.Submission,
    question: models.Question,
    student_steps: List[str],
    extracted_text: str,
    extracted_latex: Optional[str],
    feedback_prefix: str,
    graded_question_ids: set,
    image_bytes: Optional[bytes] = None,
) -> float:
    """
    Grade one question (or sub-question): optimal step matching + optional visual score.
    Returns points earned; mutates graded_question_ids on success.
    """
    if question.id in graded_question_ids:
        return 0.0
    if not student_steps:
        return 0.0

    gold_steps = _gold_steps_for_question(question)
    if not gold_steps:
        if (extracted_text or "").strip() or (extracted_latex or "").strip():
            db.add(
                models.GradingResult(
                    submission_id=submission.id,
                    question_id=question.id,
                    extracted_text=extracted_text,
                    extracted_latex=extracted_latex,
                    score=0.0,
                    max_score=float(question.points or 0),
                    feedback="Answer captured; no reference solution — awaiting manual grade.",
                    is_correct=False,
                )
            )
            db.flush()
            graded_question_ids.add(question.id)
        return 0.0

    ctx = _question_grading_context(question)
    grader = HybridGrader(gold_steps, use_ml=True, use_symbolic=True, question_context=ctx)
    grading_result = grader.grade(student_steps)

    visual_extra = ""
    if image_bytes:
        try:
            from grading.visual_grader import grade_visual_answer, merge_visual_score

            visual = grade_visual_answer(image_bytes, question, extracted_text or "")
            if visual:
                merged, visual_extra = merge_visual_score(
                    grading_result["total_score"],
                    grading_result["max_score"],
                    visual,
                    visual_weight=0.35,
                )
                grading_result["total_score"] = merged
                grading_result["percentage"] = (
                    (merged / grading_result["max_score"] * 100)
                    if grading_result["max_score"] > 0
                    else 0.0
                )
        except Exception as ex:
            logger.warning("Visual grading skipped for Q%s: %s", question.number, ex)

    fp = feedback_prefix + (visual_extra if visual_extra else "")
    _store_grading_result_rows(
        db,
        submission.id,
        question,
        grading_result,
        student_steps,
        gold_steps,
        extracted_text,
        extracted_latex,
        fp,
    )
    graded_question_ids.add(question.id)
    return float(grading_result["total_score"])


def _grade_ocr_image_for_question_tree(
    db: Session,
    submission: models.Submission,
    question: models.Question,
    image_bytes: bytes,
    image_path: Path,
    graded_question_ids: set,
) -> float:
    """
    OCR an answer image and grade the target question. When the target is a
    parent with sub-questions, split the page and grade each sub-part separately.
    """
    ocr_result = ocr_processor.extract_steps_from_file(image_bytes, image_path.name)
    combined = (ocr_result.combined_text or "").strip() or "\n".join(
        s for s in (ocr_result.steps or []) if s.strip()
    )
    subs = _sorted_subquestions(question)
    total = 0.0

    if subs:
        chunks = _split_multipart_page_text(combined, len(subs))
        for sub_q, chunk in zip(subs, chunks):
            chunk = (chunk or "").strip()
            if not chunk:
                continue
            steps = parse_answer_into_steps(chunk) or [chunk]
            total += _grade_student_work_for_question(
                db,
                submission,
                sub_q,
                steps,
                chunk,
                None,
                "Auto-graded (handwriting)",
                graded_question_ids,
                image_bytes=image_bytes if sub_q == subs[0] else None,
            )
        if total > 0:
            return total

    steps = ocr_result.steps or parse_answer_into_steps(combined) or ([combined] if combined else [])
    return _grade_student_work_for_question(
        db,
        submission,
        question,
        steps,
        combined,
        None,
        "Auto-graded (handwriting)",
        graded_question_ids,
        image_bytes=image_bytes,
    )


def _reset_submission_grading(db: Session, submission_id: str) -> None:
    """Remove prior grading rows so re-runs (auto or manual) do not duplicate results."""
    submission = (
        db.query(models.Submission)
        .options(selectinload(models.Submission.grading_results))
        .filter(models.Submission.id == submission_id)
        .first()
    )
    if submission and submission.grading_results:
        submission.grading_results.clear()
        db.flush()


async def _run_auto_grade_background(submission_id: str) -> None:
    """Background worker: own DB session so submit can return while OCR/grading runs."""
    db = SessionLocal()
    try:
        await grade_submission_automatically(submission_id, db)
    except Exception:
        logger.exception("Background auto-grading failed for submission %s", submission_id)
    finally:
        db.close()


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
    
    _reset_submission_grading(db, submission_id)
    submission.status = models.SubmissionStatus.GRADING
    db.commit()
    
    exam = (
        db.query(models.Exam)
        .options(
            selectinload(models.Exam.questions).selectinload(models.Question.gold_steps),
            selectinload(models.Exam.questions).selectinload(models.Question.embedded_content),
            selectinload(models.Exam.questions).selectinload(models.Question.sub_questions).selectinload(
                models.Question.gold_steps
            ),
        )
        .filter(models.Exam.id == submission.exam_id)
        .first()
    )
    if not exam:
        submission.status = models.SubmissionStatus.PENDING
        db.commit()
        return
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
            if isinstance(typed_answers_data, list):
                typed_answers_data = _expand_monolithic_typed_payload(
                    typed_answers_data, exam
                )
                typed_answers_data = _fan_out_multipart_typed_rows(
                    typed_answers_data, exam
                )
                for answer_data in typed_answers_data:
                    if not isinstance(answer_data, dict):
                        continue
                    total_score += _grade_one_typed_answer_payload(
                        db,
                        submission,
                        questions,
                        answer_data,
                        graded_question_ids,
                        "Auto-graded",
                    )
        except Exception as e:
            logger.exception("Error grading typed answers: %s", e)

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
                    subs = _sorted_subquestions(question)
                    if not subs:
                        logger.info(
                            "Skipping image for Q%s — already graded via typed answer",
                            question.number,
                        )
                        continue
                    if all(s.id in graded_question_ids for s in subs):
                        logger.info(
                            "Skipping image for Q%s — all sub-parts already graded",
                            question.number,
                        )
                        continue

                with open(image_path, "rb") as f:
                    image_bytes = f.read()

                total_score += _grade_ocr_image_for_question_tree(
                    db, submission, question, image_bytes, image_path, graded_question_ids
                )

            except Exception as e:
                logger.exception("Error grading image %s: %s", image_record.image_path, e)

    # Grade any typed rows still missing after the image pass (e.g. OCR-only transcripts)
    if has_typed_answers:
        try:
            typed_answers_data = json.loads(submission.typed_answers)
            if isinstance(typed_answers_data, list):
                typed_answers_data = _expand_monolithic_typed_payload(
                    typed_answers_data, exam
                )
                typed_answers_data = _fan_out_multipart_typed_rows(
                    typed_answers_data, exam
                )
                for answer_data in typed_answers_data:
                    if not isinstance(answer_data, dict):
                        continue
                    total_score += _grade_one_typed_answer_payload(
                        db,
                        submission,
                        questions,
                        answer_data,
                        graded_question_ids,
                        "Auto-graded (handwriting)",
                    )
        except Exception as e:
            logger.exception("Error in typed-answer reconciliation pass: %s", e)

    db.flush()
    total_score = _recompute_submission_total_score(db, submission.id)
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
    background_tasks: BackgroundTasks = BackgroundTasks(),
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

    for i, raw, fname in image_payloads:
        if i in skip_upload_indices:
            continue
        if (fname or "").lower().endswith(".pdf"):
            continue
        try:
            expanded_img = _ingest_image_as_full_exam_monolith_if_detected(
                raw, fname, exam, ocr_processor
            )
            if expanded_img:
                t3, img3 = expanded_img
                extra_typed_answers.extend(t3)
                extra_image_records.extend(img3)
                skip_upload_indices.add(i)
        except Exception as ex:
            logger.warning("Image monolith expansion skipped for %s: %s", fname, ex)

    # ── Merge typed answers ───────────────────────────────────────────────────
    merged_answers = extra_typed_answers[:]
    if answers:
        try:
            import json as _json
            existing = _json.loads(answers)
            existing = _expand_monolithic_typed_payload(existing, exam)
            existing = _fan_out_multipart_typed_rows(existing, exam)
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
    
    course = db.query(models.Course).filter(models.Course.id == exam.course_id).first()
    if course:
        notifications_service.push_notification(
            db,
            user_id=course.professor_id,
            kind="submission_received",
            title="New exam submission",
            body=f"{current_user.name} submitted {exam.title}.",
            link=f"/submissions/{new_submission.id}",
        )

    new_submission.status = models.SubmissionStatus.GRADING
    db.commit()
    db.refresh(new_submission)

    # Grade in the background so long OCR runs do not block the student submit response.
    background_tasks.add_task(_run_auto_grade_background, new_submission.id)

    return {
        "id": new_submission.id,
        "status": "grading",
        "message": "Submission received. AI grading started automatically.",
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
    
    submissions = (
        query.options(
            selectinload(models.Submission.grading_results).selectinload(
                models.GradingResult.step_results
            )
        )
        .order_by(models.Submission.submitted_at.desc())
        .all()
    )
    
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
            step_results = [_step_result_response_for_api(step) for step in grading_result.step_results]

            question = questions_by_id.get(grading_result.question_id)
            gr = schemas.GradingResultResponse(
                id=grading_result.id,
                score=grading_result.score,
                maxScore=grading_result.max_score,
                feedback=grading_result.feedback or "",
                stepResults=step_results,
                isCorrect=grading_result.is_correct
            ) if _show_grading else None

            answers.append(
                _submitted_answer_response(
                    question_id=grading_result.question_id,
                    question_number=question.number if question else 0,
                    questions_by_id=questions_by_id,
                    extracted_text=grading_result.extracted_text,
                    extracted_latex=grading_result.extracted_latex,
                    grading_result=gr,
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
    submission = (
        db.query(models.Submission)
        .options(
            selectinload(models.Submission.grading_results).selectinload(
                models.GradingResult.step_results
            )
        )
        .filter(models.Submission.id == submission_id)
        .first()
    )
    
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
        step_results = [_step_result_response_for_api(step) for step in grading_result.step_results]

        question = questions_by_id.get(grading_result.question_id)
        gr = schemas.GradingResultResponse(
            id=grading_result.id,
            score=grading_result.score,
            maxScore=grading_result.max_score,
            feedback=grading_result.feedback or "",
            stepResults=step_results,
            isCorrect=grading_result.is_correct
        ) if _show_grading else None

        answers.append(
            _submitted_answer_response(
                question_id=grading_result.question_id,
                question_number=question.number if question else 0,
                questions_by_id=questions_by_id,
                extracted_text=grading_result.extracted_text,
                extracted_latex=grading_result.extracted_latex,
                grading_result=gr,
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
    """Re-run automatic grading (same pipeline as submit). Professors only."""
    if current_user.role not in [models.UserRole.PROFESSOR, models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only professors can grade submissions")

    submission = (
        db.query(models.Submission)
        .options(selectinload(models.Submission.images))
        .filter(models.Submission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    has_typed = bool((submission.typed_answers or "").strip())
    has_images = len(submission.images) > 0
    if not has_typed and not has_images:
        raise HTTPException(
            status_code=400,
            detail="No answers found for submission (neither typed nor images)",
        )

    await grade_submission_automatically(submission_id, db)
    db.refresh(submission)
    exam = db.query(models.Exam).filter(models.Exam.id == submission.exam_id).first()

    st = submission.status
    if isinstance(st, models.SubmissionStatus):
        st = st.value

    return {
        "status": "success",
        "message": "Submission graded automatically",
        "submissionStatus": st,
        "totalScore": submission.total_score,
        "maxScore": submission.max_score if submission.max_score is not None else (exam.total_points if exam else 0),
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
    
    submission.total_score = _recompute_submission_total_score(db, submission_id)
    submission.status = models.SubmissionStatus.AWAITING_APPROVAL
    db.commit()
    
    return {
        "status": "success",
        "message": "Grades adjusted successfully",
        "totalScore": submission.total_score
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
    exam = db.query(models.Exam).filter(models.Exam.id == submission.exam_id).first()
    exam_title = exam.title if exam else "Exam"
    notifications_service.push_notification(
        db,
        user_id=submission.student_id,
        kind="grade_released",
        title=f"Grades released: {exam_title}",
        body="Your instructor approved your work. View scores and feedback in My Results.",
        link="/my-results",
    )
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


def _week_start_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _submission_status_label(status: models.SubmissionStatus) -> str:
    return {
        models.SubmissionStatus.PENDING: "Pending",
        models.SubmissionStatus.GRADING: "Grading",
        models.SubmissionStatus.GRADED: "Graded",
        models.SubmissionStatus.AWAITING_APPROVAL: "Awaiting approval",
        models.SubmissionStatus.APPROVED: "Released",
    }.get(status, status.value)


@app.get("/api/dashboard/analytics", response_model=schemas.DashboardAnalyticsResponse)
def get_dashboard_analytics(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Role-specific analytics for charts: instructors (professor/admin) see class-wide
    submission and course metrics; students see their released scores and workload.
    """
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)

    if current_user.role in (models.UserRole.PROFESSOR, models.UserRole.ADMIN):
        base = (
            db.query(models.Submission)
            .join(models.Exam, models.Submission.exam_id == models.Exam.id)
            .join(models.Course, models.Exam.course_id == models.Course.id)
        )
        if current_user.role == models.UserRole.PROFESSOR:
            base = base.filter(models.Course.professor_id == current_user.id)

        status_rows = (
            base.with_entities(models.Submission.status, func.count(models.Submission.id))
            .group_by(models.Submission.status)
            .all()
        )
        submission_status = [
            schemas.AnalyticsCountItem(
                label=_submission_status_label(st),
                key=st.value,
                count=cnt,
            )
            for st, cnt in status_rows
        ]
        submission_status.sort(key=lambda x: -x.count)

        courses_q = db.query(models.Course)
        if current_user.role == models.UserRole.PROFESSOR:
            courses_q = courses_q.filter(models.Course.professor_id == current_user.id)
        courses = courses_q.all()
        course_ids = [c.id for c in courses]
        course_by_id = {c.id: c for c in courses}

        course_breakdown: List[schemas.InstructorCourseAnalyticsItem] = []
        if course_ids:
            subs_for_courses = (
                db.query(models.Submission, models.Course.id.label("cid"))
                .join(models.Exam, models.Submission.exam_id == models.Exam.id)
                .join(models.Course, models.Exam.course_id == models.Course.id)
                .filter(models.Course.id.in_(course_ids))
            )
            if current_user.role == models.UserRole.PROFESSOR:
                subs_for_courses = subs_for_courses.filter(models.Course.professor_id == current_user.id)

            from collections import defaultdict

            per_course_subs: dict = defaultdict(list)
            for sub, cid in subs_for_courses.all():
                per_course_subs[cid].append(sub)

            for cid in course_ids:
                c = course_by_id[cid]
                subs_list = per_course_subs.get(cid, [])
                scored = [
                    s
                    for s in subs_list
                    if s.total_score is not None and s.max_score and s.max_score > 0
                ]
                avg_pct = None
                if scored:
                    avg_pct = round(
                        sum((s.total_score / s.max_score) * 100.0 for s in scored) / len(scored),
                        1,
                    )
                course_breakdown.append(
                    schemas.InstructorCourseAnalyticsItem(
                        courseId=c.id,
                        courseName=c.name,
                        courseCode=c.code,
                        submissionCount=len(subs_list),
                        gradedCount=len(scored),
                        avgPercent=avg_pct,
                    )
                )
            course_breakdown.sort(key=lambda x: -x.submissionCount)

        enrollments_by_course: List[schemas.InstructorEnrollmentItem] = []
        for cid in course_ids:
            c = course_by_id[cid]
            n = (
                db.query(func.count(models.CourseEnrollment.id))
                .filter(
                    models.CourseEnrollment.course_id == cid,
                    models.CourseEnrollment.status == models.EnrollmentStatus.APPROVED,
                )
                .scalar()
                or 0
            )
            enrollments_by_course.append(
                schemas.InstructorEnrollmentItem(
                    courseId=c.id,
                    courseName=c.name,
                    approvedStudents=int(n),
                )
            )
        enrollments_by_course.sort(key=lambda x: -x.approvedStudents)

        cutoff = datetime.utcnow() - timedelta(weeks=11)
        recent_submitted = (
            base.filter(models.Submission.submitted_at.isnot(None))
            .filter(models.Submission.submitted_at >= cutoff)
            .with_entities(models.Submission.submitted_at)
            .all()
        )
        week_counts: dict = {}
        for (sub_at,) in recent_submitted:
            if not sub_at:
                continue
            d = sub_at.date() if hasattr(sub_at, "date") else sub_at
            ws = _week_start_monday(d)
            week_counts[ws] = week_counts.get(ws, 0) + 1

        today = datetime.utcnow().date()
        anchor = _week_start_monday(today)
        weekly_submissions: List[schemas.InstructorWeekSubmissionsItem] = []
        for i in range(10):
            ws = anchor - timedelta(weeks=(9 - i))
            weekly_submissions.append(
                schemas.InstructorWeekSubmissionsItem(
                    weekStart=ws.isoformat(),
                    count=int(week_counts.get(ws, 0)),
                )
            )

        return schemas.DashboardAnalyticsResponse(
            role=role_val,
            instructor=schemas.InstructorAnalyticsData(
                submissionStatus=submission_status,
                courseBreakdown=course_breakdown,
                weeklySubmissions=weekly_submissions,
                enrollmentsByCourse=enrollments_by_course,
            ),
            student=None,
        )

    # Student
    enrolled_rows = (
        db.query(models.CourseEnrollment.course_id)
        .filter(
            models.CourseEnrollment.student_id == current_user.id,
            models.CourseEnrollment.status == models.EnrollmentStatus.APPROVED,
        )
        .all()
    )
    enrolled_ids = [r[0] for r in enrolled_rows]

    st_rows = (
        db.query(models.Submission.status, func.count(models.Submission.id))
        .filter(models.Submission.student_id == current_user.id)
        .group_by(models.Submission.status)
        .all()
    )
    submission_status = [
        schemas.AnalyticsCountItem(
            label=_submission_status_label(st),
            key=st.value,
            count=cnt,
        )
        for st, cnt in st_rows
    ]
    submission_status.sort(key=lambda x: -x.count)

    released_exam_scores: List[schemas.StudentExamScoreItem] = []
    course_perf_map: dict = {}

    if enrolled_ids:
        released = (
            db.query(models.Submission, models.Exam, models.Course)
            .join(models.Exam, models.Submission.exam_id == models.Exam.id)
            .join(models.Course, models.Exam.course_id == models.Course.id)
            .filter(models.Submission.student_id == current_user.id)
            .filter(models.Submission.status == models.SubmissionStatus.APPROVED)
            .filter(models.Submission.total_score.isnot(None))
            .filter(models.Submission.max_score > 0)
            .filter(models.Course.id.in_(enrolled_ids))
            .order_by(models.Submission.submitted_at.desc())
            .all()
        )
        for sub, exam, course in released:
            pct = round((sub.total_score / sub.max_score) * 100.0, 1)
            released_exam_scores.append(
                schemas.StudentExamScoreItem(
                    examId=exam.id,
                    examTitle=exam.title,
                    courseName=course.name,
                    percent=pct,
                    submittedAt=sub.submitted_at,
                )
            )
            cid = course.id
            if cid not in course_perf_map:
                course_perf_map[cid] = {"name": course.name, "pcts": []}
            course_perf_map[cid]["pcts"].append(pct)

    course_performance = [
        schemas.StudentCoursePerformanceItem(
            courseId=cid,
            courseName=info["name"],
            avgPercent=round(sum(info["pcts"]) / len(info["pcts"]), 1),
            gradedCount=len(info["pcts"]),
        )
        for cid, info in course_perf_map.items()
    ]
    course_performance.sort(key=lambda x: -x.avgPercent)

    chart_scores = list(reversed(released_exam_scores[:20]))

    return schemas.DashboardAnalyticsResponse(
        role=role_val,
        instructor=None,
        student=schemas.StudentAnalyticsData(
            submissionStatus=submission_status,
            releasedExamScores=chart_scores,
            coursePerformance=course_performance,
        ),
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
    if _looks_like_math_ocr(s):
        return _normalize_text_for_storage(s)
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


def _looks_like_math_ocr(s: str) -> bool:
    """Mathpix / OCR output with LaTeX must not be stripped by the ASCII sanitizer."""
    if not s or not isinstance(s, str):
        return False
    if "$$" in s or re.search(r"(?<!\$)\$(?!\$)[^$\n]+?\$(?!\$)", s):
        return True
    lowered = s.lower()
    if any(tok in lowered for tok in ("\\begin{", "\\frac", "\\prime", "\\left", "\\right")):
        return True
    if s.count("\\") >= 2 and any(c in s for c in "{}^"):
        return True
    return False


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
    if _looks_like_math_ocr(s):
        return _normalize_text_for_storage(s)
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

