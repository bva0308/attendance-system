import csv
import io
from dataclasses import dataclass

from sqlalchemy import and_

from models import AttendanceRecord, Session, Student


@dataclass
class AttendanceFilter:
    class_name: str | None = None
    student_id: int | None = None
    session_id: int | None = None
    date_from: str | None = None
    date_to: str | None = None


def query_attendance(filters: AttendanceFilter):
    query = AttendanceRecord.query.join(Student).join(Session).order_by(AttendanceRecord.created_at.desc())

    clauses = []
    if filters.class_name:
        clauses.append(Student.class_name == filters.class_name)
    if filters.student_id:
        clauses.append(Student.id == filters.student_id)
    if filters.session_id:
        clauses.append(Session.id == filters.session_id)
    if filters.date_from:
        clauses.append(AttendanceRecord.created_at >= f"{filters.date_from} 00:00:00")
    if filters.date_to:
        clauses.append(AttendanceRecord.created_at <= f"{filters.date_to} 23:59:59")

    if clauses:
        query = query.filter(and_(*clauses))
    return query.all()


def export_attendance_csv(records: list[AttendanceRecord]) -> str:
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
                row.student.student_code,
                row.student.full_name,
                row.student.class_name,
                row.session.title,
                row.status,
                row.verified_by_qr,
                row.verified_by_face,
                row.verified_by_fingerprint,
                row.note or "",
            ]
        )
    return buffer.getvalue()
