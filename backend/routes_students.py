import json

from flask import Blueprint, flash, redirect, render_template, request, url_for

from auth import login_required
from database import db
from models import AttendanceRecord, Device, DeviceCommand, Session, Student
from services_face import enroll_face_profile, face_provider_available


students_bp = Blueprint("students", __name__)


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
        student = Student(
            student_code=request.form["student_code"].strip(),
            full_name=request.form["full_name"].strip(),
            email=request.form.get("email", "").strip() or None,
            class_name=request.form["class_name"].strip(),
        )
        db.session.add(student)
        db.session.commit()
        flash("Student created.", "success")
        return redirect(url_for("students.student_edit", student_id=student.id))
    return render_template("student_form.html", student=None)


@students_bp.route("/students/<int:student_id>", methods=["GET", "POST"])
@login_required
def student_edit(student_id: int):
    student = Student.query.get_or_404(student_id)
    if request.method == "POST":
        student.student_code = request.form["student_code"].strip()
        student.full_name = request.form["full_name"].strip()
        student.email = request.form.get("email", "").strip() or None
        student.class_name = request.form["class_name"].strip()
        student.active = request.form.get("active") == "on"
        db.session.commit()
        flash("Student updated.", "success")
        return redirect(url_for("students.student_edit", student_id=student.id))
    devices = Device.query.order_by(Device.display_name.asc()).all()
    return render_template("student_form.html", student=student, devices=devices)


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
    device = Device.query.get_or_404(device_id)
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
