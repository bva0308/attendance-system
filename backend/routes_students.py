import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from auth import login_required
from database import db
from models import AttendanceRecord, Device, DeviceCommand, Session, Student
from services_face import enroll_face_profile, face_provider_available


students_bp = Blueprint("students", __name__)


def _student_form_data(student: Student | None = None) -> dict[str, object]:
    if request.method == "POST":
        return {
            "student_code": request.form.get("student_code", "").strip(),
            "full_name": request.form.get("full_name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "class_name": request.form.get("class_name", "").strip(),
            "active": request.form.get("active") == "on" if student else True,
        }

    return {
        "student_code": student.student_code if student else "",
        "full_name": student.full_name if student else "",
        "email": student.email or "" if student else "",
        "class_name": student.class_name if student else "",
        "active": student.active if student else True,
    }


def _validate_student_form(student: Student | None = None) -> tuple[dict[str, object], bool]:
    form_data = _student_form_data(student)

    if not form_data["student_code"] or not form_data["full_name"] or not form_data["class_name"]:
        flash("Student code, full name, and class / section are required.", "error")
        return form_data, False

    existing = Student.query.filter(func.lower(Student.student_code) == str(form_data["student_code"]).lower())
    if student is not None:
        existing = existing.filter(Student.id != student.id)

    if existing.first():
        flash("Student code must be unique.", "error")
        return form_data, False

    return form_data, True


@students_bp.route("/")
@login_required
def dashboard_home():
    metrics = {
        "students": Student.query.count(),
        "devices": Device.query.count(),
        "active_sessions": Session.query.filter_by(is_active=True).count(),
        "attendance_records": AttendanceRecord.query.count(),
    }
    recent_attendance = AttendanceRecord.query.order_by(AttendanceRecord.created_at.desc()).limit(10).all()
    devices = Device.query.order_by(Device.last_seen_at.desc().nullslast()).all()
    return render_template("dashboard.html", metrics=metrics, recent_attendance=recent_attendance, devices=devices)


@students_bp.route("/students")
@login_required
def students_list():
    students = Student.query.order_by(Student.class_name.asc(), Student.full_name.asc()).all()
    return render_template("students_list.html", students=students, face_provider_available=face_provider_available())


@students_bp.route("/students/new", methods=["GET", "POST"])
@login_required
def student_create():
    if request.method == "POST":
        form_data, is_valid = _validate_student_form()
        if not is_valid:
            return render_template(
                "student_form.html",
                student=None,
                form_data=form_data,
                devices=[],
                face_provider_available=face_provider_available(),
            )

        student = Student(
            student_code=str(form_data["student_code"]),
            full_name=str(form_data["full_name"]),
            email=str(form_data["email"]) or None,
            class_name=str(form_data["class_name"]),
        )
        db.session.add(student)
        db.session.commit()
        flash("Student created.", "success")
        return redirect(url_for("students.student_edit", student_id=student.id))
    return render_template(
        "student_form.html",
        student=None,
        form_data=_student_form_data(),
        devices=[],
        face_provider_available=face_provider_available(),
    )


@students_bp.route("/students/<int:student_id>", methods=["GET", "POST"])
@login_required
def student_edit(student_id: int):
    student = Student.query.get_or_404(student_id)
    devices = Device.query.filter_by(is_active=True).order_by(Device.display_name.asc()).all()
    if request.method == "POST":
        form_data, is_valid = _validate_student_form(student)
        if not is_valid:
            return render_template(
                "student_form.html",
                student=student,
                form_data=form_data,
                devices=devices,
                face_provider_available=face_provider_available(),
            )

        student.student_code = str(form_data["student_code"])
        student.full_name = str(form_data["full_name"])
        student.email = str(form_data["email"]) or None
        student.class_name = str(form_data["class_name"])
        student.active = bool(form_data["active"])
        db.session.commit()
        flash("Student updated.", "success")
        return redirect(url_for("students.student_edit", student_id=student.id))
    return render_template(
        "student_form.html",
        student=student,
        form_data=_student_form_data(student),
        devices=devices,
        face_provider_available=face_provider_available(),
    )


@students_bp.route("/students/<int:student_id>/upload-face", methods=["POST"])
@login_required
def upload_face(student_id: int):
    student = Student.query.get_or_404(student_id)
    image = request.files.get("face_image")
    if not image:
        flash("Face image is required.", "error")
        return redirect(url_for("students.student_edit", student_id=student.id))
    try:
        enroll_face_profile(student, image)
        flash("Face profile enrolled successfully.", "success")
    except Exception as exc:  # pragma: no cover
        flash(f"Face enrollment failed: {exc}", "error")
    return redirect(url_for("students.student_edit", student_id=student.id))


@students_bp.route("/students/<int:student_id>/queue-fingerprint", methods=["POST"])
@login_required
def queue_fingerprint(student_id: int):
    student = Student.query.get_or_404(student_id)
    device_id = int(request.form["device_id"])
    device = Device.query.filter_by(id=device_id, is_active=True).first_or_404()
    command = DeviceCommand(
        device=device,
        command_type="enroll_fingerprint",
        payload_json=json.dumps({"student_id": student.id, "student_code": student.student_code}),
    )
    db.session.add(command)
    db.session.commit()
    flash(f"Fingerprint enrollment queued for {student.full_name} on {device.display_name}.", "success")
    return redirect(url_for("students.student_edit", student_id=student.id))


@students_bp.route("/devices")
@login_required
def devices_page():
    devices = Device.query.order_by(Device.display_name.asc()).all()
    queued_commands = DeviceCommand.query.order_by(DeviceCommand.created_at.desc()).limit(20).all()
    return render_template("devices.html", devices=devices, queued_commands=queued_commands)
