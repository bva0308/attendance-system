import csv
import io
from dataclasses import dataclass
from datetime import datetime, time

from sqlalchemy import and_

from models import AttendanceRecord, Session, Student, VerificationEvent


@dataclass
class AttendanceFilter:
    class_name: str | None = None
    student_id: int | None = None
    session_id: int | None = None
    date_from: str | None = None
    date_to: str | None = None


@dataclass
class AttendanceViewRow:
    created_at: datetime
    student_name: str
    student_code: str
    class_name: str
    session_title: str
    status: str
    verified_by_qr: bool
    verified_by_face: bool
    verified_by_fingerprint: bool
    note: str | None


def _parse_date_boundary(value: str | None, end_of_day: bool) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    boundary = time.max if end_of_day else time.min
    return datetime.combine(parsed.date(), boundary)


def query_attendance(filters: AttendanceFilter):
    query = AttendanceRecord.query.join(Student).join(Session).order_by(AttendanceRecord.created_at.desc())

    clauses = []
    if filters.class_name:
        clauses.append(Student.class_name == filters.class_name)
    if filters.student_id:
        clauses.append(Student.id == filters.student_id)
    if filters.session_id:
        clauses.append(Session.id == filters.session_id)

    date_from = _parse_date_boundary(filters.date_from, end_of_day=False)
    date_to = _parse_date_boundary(filters.date_to, end_of_day=True)
    if date_from:
        clauses.append(AttendanceRecord.created_at >= date_from)
    if date_to:
        clauses.append(AttendanceRecord.created_at <= date_to)

    if clauses:
        query = query.filter(and_(*clauses))
    records = [
        AttendanceViewRow(
            created_at=row.created_at,
            student_name=row.student.full_name,
            student_code=row.student.student_code,
            class_name=row.student.class_name,
            session_title=row.session.title,
            status=row.status,
            verified_by_qr=row.verified_by_qr,
            verified_by_face=row.verified_by_face,
            verified_by_fingerprint=row.verified_by_fingerprint,
            note=row.note,
        )
        for row in query.all()
    ]

    event_query = VerificationEvent.query.order_by(VerificationEvent.created_at.desc())
    event_clauses = []
    if filters.class_name:
        event_clauses.append(VerificationEvent.class_name == filters.class_name)
    if filters.student_id:
        event_clauses.append(VerificationEvent.student_id == filters.student_id)
    if filters.session_id:
        event_clauses.append(VerificationEvent.session_id == filters.session_id)
    date_from = _parse_date_boundary(filters.date_from, end_of_day=False)
    date_to = _parse_date_boundary(filters.date_to, end_of_day=True)
    if date_from:
        event_clauses.append(VerificationEvent.created_at >= date_from)
    if date_to:
        event_clauses.append(VerificationEvent.created_at <= date_to)
    if event_clauses:
        event_query = event_query.filter(and_(*event_clauses))

    events = [
        AttendanceViewRow(
            created_at=row.created_at,
            student_name=(row.student.full_name if row.student else row.student_label or "Unknown fingerprint"),
            student_code=(row.student.student_code if row.student else "-"),
            class_name=row.class_name or (row.student.class_name if row.student else "-"),
            session_title=row.session_title or (row.session.title if row.session else "-"),
            status=row.status,
            verified_by_qr=row.verified_by_qr,
            verified_by_face=row.verified_by_face,
            verified_by_fingerprint=row.verified_by_fingerprint,
            note=row.note,
        )
        for row in event_query.all()
    ]
    return sorted(records + events, key=lambda item: item.created_at, reverse=True)


def query_recent_attendance(limit: int = 10):
    return query_attendance(AttendanceFilter())[:limit]


def export_attendance_csv(records: list[AttendanceViewRow]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "timestamp",
            "student_code",
            "student_name",
            "class_name",
            "session_title",
            "status",
            "verified_by_qr",
            "verified_by_face",
            "verified_by_fingerprint",
            "note",
        ]
    )
    for row in records:
        writer.writerow(
            [
                row.created_at.isoformat(),
                row.student_code,
                row.student_name,
                row.class_name,
                row.session_title,
                row.status,
                row.verified_by_qr,
                row.verified_by_face,
                row.verified_by_fingerprint,
                row.note or "",
            ]
        )
    return buffer.getvalue()
