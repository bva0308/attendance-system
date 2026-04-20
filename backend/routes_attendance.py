from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from auth import login_required
from models import Session, Student
from services_reports import AttendanceFilter, export_attendance_csv, query_attendance


attendance_bp = Blueprint("attendance", __name__)


def _optional_int_arg(name: str) -> int | None:
    value = request.args.get(name)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Invalid value for {name}.")


def _build_filters() -> AttendanceFilter:
    return AttendanceFilter(
        class_name=request.args.get("class_name") or None,
        student_id=_optional_int_arg("student_id"),
        session_id=_optional_int_arg("session_id"),
        date_from=request.args.get("date_from") or None,
        date_to=request.args.get("date_to") or None,
    )


@attendance_bp.route("/attendance")
@login_required
def attendance_records():
    try:
        filters = _build_filters()
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("attendance.attendance_records"))
    records = query_attendance(filters)
    return render_template(
        "attendance_list.html",
        records=records,
        students=Student.query.order_by(Student.full_name.asc()).all(),
        sessions=Session.query.order_by(Session.starts_at.desc()).all(),
        filters=filters,
    )


@attendance_bp.route("/attendance/export.csv")
@login_required
def attendance_export():
    filters = _build_filters()
    csv_data = export_attendance_csv(query_attendance(filters))
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance-export.csv"},
    )
