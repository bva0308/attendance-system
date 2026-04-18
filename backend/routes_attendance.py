from flask import Blueprint, Response, render_template, request

from auth import login_required
from models import Session, Student
from services_reports import AttendanceFilter, export_attendance_csv, query_attendance


attendance_bp = Blueprint("attendance", __name__)


@attendance_bp.route("/attendance")
@login_required
def attendance_records():
    filters = AttendanceFilter(
        class_name=request.args.get("class_name") or None,
        student_id=int(request.args["student_id"]) if request.args.get("student_id") else None,
        session_id=int(request.args["session_id"]) if request.args.get("session_id") else None,
        date_from=request.args.get("date_from") or None,
        date_to=request.args.get("date_to") or None,
    )
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
    filters = AttendanceFilter(
        class_name=request.args.get("class_name") or None,
        student_id=int(request.args["student_id"]) if request.args.get("student_id") else None,
        session_id=int(request.args["session_id"]) if request.args.get("session_id") else None,
        date_from=request.args.get("date_from") or None,
        date_to=request.args.get("date_to") or None,
    )
    csv_data = export_attendance_csv(query_attendance(filters))
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance-export.csv"},
    )
