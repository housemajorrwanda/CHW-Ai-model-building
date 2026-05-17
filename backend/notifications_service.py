"""
In-app notifications and computed reminder rows for the notification feed.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from sqlalchemy.orm import Session

import models

DEFAULT_EXAM_OFFSET_HOURS = (168, 72, 24)


def exam_reminders_enabled(user: models.User) -> bool:
    v = getattr(user, "remind_exam_deadlines_enabled", None)
    return True if v is None else bool(v)


def teaching_reminders_enabled(user: models.User) -> bool:
    v = getattr(user, "remind_teaching_deadlines_enabled", None)
    return True if v is None else bool(v)


def exam_offset_hours_for_user(user: models.User) -> List[int]:
    raw = getattr(user, "remind_exam_offsets_hours", None)
    if not raw or not str(raw).strip():
        return list(DEFAULT_EXAM_OFFSET_HOURS)
    try:
        arr = json.loads(raw)
        if not isinstance(arr, list):
            return list(DEFAULT_EXAM_OFFSET_HOURS)
        out: List[int] = []
        for x in arr:
            try:
                h = int(x)
                if 1 <= h <= 8760:
                    out.append(h)
            except (TypeError, ValueError):
                continue
        out = sorted(set(out), reverse=True)
        return out if out else list(DEFAULT_EXAM_OFFSET_HOURS)
    except json.JSONDecodeError:
        return list(DEFAULT_EXAM_OFFSET_HOURS)


def _due_within_label(hours: int) -> str:
    if hours >= 168 and hours % 168 == 0:
        w = hours // 168
        return f"{w} week" + ("s" if w != 1 else "")
    if hours >= 24 and hours % 24 == 0:
        d = hours // 24
        return f"{d} day" + ("s" if d != 1 else "")
    if hours == 1:
        return "1 hour"
    return f"{hours} hours"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def push_notification(
    db: Session,
    *,
    user_id: str,
    kind: str,
    title: str,
    body: Optional[str] = None,
    link: Optional[str] = None,
) -> models.Notification:
    row = models.Notification(
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        link=link,
    )
    db.add(row)
    return row


def notification_to_item(n: models.Notification) -> dict[str, Any]:
    return {
        "id": n.id,
        "category": "notification",
        "kind": n.kind,
        "title": n.title,
        "body": n.body,
        "link": n.link,
        "createdAt": n.created_at,
        "readAt": n.read_at,
    }


def _student_has_released_submission(db: Session, exam_id: str, student_id: str) -> bool:
    sub = (
        db.query(models.Submission)
        .filter(
            models.Submission.exam_id == exam_id,
            models.Submission.student_id == student_id,
            models.Submission.status == models.SubmissionStatus.APPROVED,
        )
        .first()
    )
    return sub is not None


def _reminders_for_student(db: Session, user: models.User) -> List[dict[str, Any]]:
    rows: List[dict[str, Any]] = []
    now = _utcnow()
    if not exam_reminders_enabled(user):
        return rows

    course_ids = [
        e.course_id
        for e in db.query(models.CourseEnrollment)
        .filter(
            models.CourseEnrollment.student_id == user.id,
            models.CourseEnrollment.status == models.EnrollmentStatus.APPROVED,
        )
        .all()
    ]
    if not course_ids:
        return rows

    exams = (
        db.query(models.Exam)
        .filter(
            models.Exam.course_id.in_(course_ids),
            models.Exam.is_published.is_(True),
            models.Exam.due_date.isnot(None),
        )
        .all()
    )

    for exam in exams:
        if _student_has_released_submission(db, exam.id, user.id):
            continue
        due = _ensure_aware(exam.due_date)
        course = db.query(models.Course).filter(models.Course.id == exam.course_id).first()
        course_name = course.name if course else "Course"
        link = f"/take-exam/{exam.id}"

        if due < now:
            rows.append(
                {
                    "id": f"reminder:exam-overdue:{exam.id}",
                    "category": "reminder",
                    "kind": "exam_overdue",
                    "title": f"Overdue: {exam.title}",
                    "body": f"{course_name} — due {_fmt_local(due)}. Submit when you can.",
                    "link": link,
                    "createdAt": now,
                    "readAt": None,
                }
            )
            continue

        delta = due - now
        offsets = sorted(exam_offset_hours_for_user(user))
        if not offsets:
            continue
        max_h = offsets[-1]
        if delta > timedelta(hours=max_h):
            continue
        tier_h = next((h for h in offsets if delta <= timedelta(hours=h)), None)
        if tier_h is None:
            continue
        label = f"Due within {_due_within_label(tier_h)}"
        rows.append(
            {
                "id": f"reminder:exam-due:{exam.id}:{tier_h}",
                "category": "reminder",
                "kind": "exam_due_soon",
                "title": f"{label}: {exam.title}",
                "body": f"{course_name} — due {_fmt_local(due)}.",
                "link": link,
                "createdAt": due,
                "readAt": None,
            }
        )

    return rows


def _fmt_local(dt: datetime) -> str:
    try:
        return _ensure_aware(dt).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(dt)


def _reminders_for_professor(db: Session, user: models.User) -> List[dict[str, Any]]:
    rows: List[dict[str, Any]] = []
    if not teaching_reminders_enabled(user):
        return rows
    courses = (
        db.query(models.Course).filter(models.Course.professor_id == user.id).all()
    )
    for course in courses:
        pending = (
            db.query(models.CourseEnrollment)
            .filter(
                models.CourseEnrollment.course_id == course.id,
                models.CourseEnrollment.status == models.EnrollmentStatus.PENDING,
            )
            .count()
        )
        if pending:
            rows.append(
                {
                    "id": f"reminder:enroll-pending:{course.id}",
                    "category": "reminder",
                    "kind": "enrollment_pending",
                    "title": f"{pending} enrollment request(s)",
                    "body": f"Review requests for {course.name} ({course.code}).",
                    "link": f"/courses/{course.id}",
                    "createdAt": _utcnow(),
                    "readAt": None,
                }
            )

    approve_count = (
        db.query(models.Submission)
        .join(models.Exam, models.Exam.id == models.Submission.exam_id)
        .join(models.Course, models.Course.id == models.Exam.course_id)
        .filter(models.Course.professor_id == user.id)
        .filter(
            models.Submission.status.in_(
                [
                    models.SubmissionStatus.AWAITING_APPROVAL,
                    models.SubmissionStatus.GRADED,
                ]
            )
        )
        .count()
    )
    if approve_count:
        rows.append(
            {
                "id": f"reminder:approve-all:{user.id}",
                "category": "reminder",
                "kind": "submissions_awaiting_release",
                "title": f"{approve_count} submission(s) to review or release",
                "body": "Approve graded work so students can see their scores.",
                "link": "/submissions",
                "createdAt": _utcnow(),
                "readAt": None,
            }
        )

    return rows


SCHEDULED_REPEAT = frozenset({"none", "daily", "weekly", "monthly"})


def _scheduled_body_for_feed(r: models.UserScheduledReminder) -> Optional[str]:
    parts: List[str] = []
    if r.body:
        parts.append(r.body.strip())
    if r.user_note and str(r.user_note).strip():
        parts.append("Your note: " + str(r.user_note).strip())
    if r.repeat and r.repeat != "none":
        parts.append(f"Repeats: {r.repeat}")
    return "\n".join(parts) if parts else None


def _due_scheduled_reminder_rows(db: Session, user_id: str) -> List[models.UserScheduledReminder]:
    return (
        db.query(models.UserScheduledReminder)
        .filter(
            models.UserScheduledReminder.user_id == user_id,
            models.UserScheduledReminder.active.is_(True),
            models.UserScheduledReminder.remind_at <= _utcnow(),
        )
        .order_by(models.UserScheduledReminder.remind_at.desc())
        .all()
    )


def _advance_remind_at(remind_at: datetime, repeat: str, now: datetime) -> Optional[datetime]:
    rep = (repeat or "none").lower()
    if rep == "none" or not rep:
        return None
    deltas = {
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1),
        "monthly": timedelta(days=30),
    }
    d = deltas.get(rep)
    if not d:
        return None
    nxt = _ensure_aware(remind_at)
    while nxt <= now:
        nxt = nxt + d
    return nxt


def _optional_trim(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    t = str(s).strip()
    return t if t else None


def acknowledge_scheduled_reminder(db: Session, user: models.User, reminder_id: str) -> bool:
    r = (
        db.query(models.UserScheduledReminder)
        .filter(
            models.UserScheduledReminder.id == reminder_id,
            models.UserScheduledReminder.user_id == user.id,
            models.UserScheduledReminder.active.is_(True),
        )
        .first()
    )
    if not r:
        return False
    now = _utcnow()
    nxt = _advance_remind_at(r.remind_at, r.repeat, now)
    if nxt is None:
        r.active = False
    else:
        r.remind_at = nxt
    return True


def schedule_user_reminder(
    db: Session,
    user: models.User,
    *,
    source_key: Optional[str],
    title: str,
    body: Optional[str],
    link: Optional[str],
    user_note: Optional[str],
    remind_at: datetime,
    repeat: str,
) -> models.UserScheduledReminder:
    rep = (repeat or "none").lower()
    if rep not in SCHEDULED_REPEAT:
        rep = "none"
    if source_key:
        olds = (
            db.query(models.UserScheduledReminder)
            .filter(
                models.UserScheduledReminder.user_id == user.id,
                models.UserScheduledReminder.source_key == source_key,
                models.UserScheduledReminder.active.is_(True),
            )
            .all()
        )
        for old in olds:
            old.active = False
    note = _optional_trim(user_note)
    row = models.UserScheduledReminder(
        user_id=user.id,
        source_key=source_key,
        title=title[:500],
        body=(body or "").strip() or None,
        link=link,
        user_note=note,
        remind_at=_ensure_aware(remind_at),
        repeat=rep,
        active=True,
    )
    db.add(row)
    return row


def build_feed(
    db: Session,
    user: models.User,
    *,
    limit: int = 80,
) -> tuple[List[dict[str, Any]], int]:
    stored = (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user.id)
        .order_by(models.Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    stored_items = [notification_to_item(n) for n in stored]

    if user.role == models.UserRole.STUDENT:
        reminders = _reminders_for_student(db, user)
    elif user.role == models.UserRole.PROFESSOR:
        reminders = _reminders_for_professor(db, user)
    else:
        reminders = []

    merged = stored_items + reminders

    def _sort_key(item: dict[str, Any]) -> tuple:
        pr = 0
        ts = 0.0
        c = item.get("createdAt")
        if isinstance(c, datetime):
            c = _ensure_aware(c)
            ts = c.timestamp()
        if item.get("category") == "reminder":
            if item.get("kind") == "exam_overdue":
                pr = 2
            elif item.get("kind") == "exam_due_soon":
                pr = 1
                ts = -ts
        return (pr, ts)

    merged.sort(key=_sort_key, reverse=True)
    merged = merged[:limit]

    unread_stored = sum(1 for n in stored if n.read_at is None)
    unread_reminders = len(reminders)
    badge = unread_stored + unread_reminders

    return merged, badge


def list_due_scheduled_reminders(db: Session, user: models.User) -> List[dict[str, Any]]:
    """Due personal reminders (not mixed into the notification bell list)."""
    rows = sorted(_due_scheduled_reminder_rows(db, user.id), key=lambda r: r.remind_at)
    out: List[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "title": r.title,
                "body": _scheduled_body_for_feed(r),
                "link": r.link,
                "remindAt": r.remind_at,
                "repeat": r.repeat or "none",
            }
        )
    return out


def mark_read(db: Session, user: models.User, notification_id: str) -> bool:
    n = (
        db.query(models.Notification)
        .filter(
            models.Notification.id == notification_id,
            models.Notification.user_id == user.id,
        )
        .first()
    )
    if not n:
        return False
    if n.read_at is None:
        n.read_at = _utcnow()
    return True


def mark_all_read(db: Session, user: models.User) -> int:
    rows = (
        db.query(models.Notification)
        .filter(
            models.Notification.user_id == user.id,
            models.Notification.read_at.is_(None),
        )
        .all()
    )
    now = _utcnow()
    for n in rows:
        n.read_at = now
    return len(rows)
