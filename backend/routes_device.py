import json
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from auth import device_required
from database import db
from models import (
    AttendanceRecord,
    DeviceCommand,
    FingerprintProfile,
    PendingFingerprintVerification,
    Session,
    Student,
    VerificationEvent,
)
from services_face import verify_face_for_session
from services_qr import decode_qr_from_bytes


device_bp = Blueprint("device", __name__, url_prefix="/api/device")


def _serialize_session(session: Session | None):
    if not session:
        return None
    return {
        "id": session.id,
        "title": session.title,
        "class_name": session.class_name,
        "session_token": session.session_token,
        "starts_at": session.starts_at.isoformat(),
        "ends_at": session.ends_at.isoformat(),
        "allow_duplicates": session.allow_duplicates,
    }


def _serialize_student(student: Student | None):
    if not student:
        return None
    template_id = student.fingerprint_profile.template_id if student.fingerprint_profile else None
    return {
        "id": student.id,
        "student_code": student.student_code,
        "full_name": student.full_name,
        "class_name": student.class_name,
        "fingerprint_template_id": template_id,
    }


def _session_is_open(session: Session) -> bool:
    now = datetime.utcnow()
    return session.is_active and session.starts_at <= now <= session.ends_at


def _serialize_pending_fingerprint(pending: PendingFingerprintVerification | None):
    if not pending:
        return None
    return {
        "id": pending.id,
        "session_token": pending.session.session_token,
        "session_title": pending.session.title,
        "student_id": pending.student.id,
        "student_code": pending.student.student_code,
        "student_name": pending.student.full_name,
        "fingerprint_template_id": (
            pending.student.fingerprint_profile.template_id if pending.student.fingerprint_profile else None
        ),
    }


@device_bp.route("/heartbeat", methods=["POST"])
@device_required
def heartbeat():
    payload = request.get_json(force=True, silent=True) or {}
    request.device.ip_address = payload.get("ip_address")
    request.device.firmware_version = payload.get("firmware_version")
    request.device.last_status = payload.get("state")
    request.device.last_rssi = payload.get("wifi_rssi")
    request.device.last_seen_at = datetime.utcnow()
    db.session.commit()

    active_session = Session.query.filter_by(is_active=True).order_by(Session.starts_at.desc()).first()
    pending = (
        DeviceCommand.query.filter_by(device_id=request.device.id, status="queued")
        .order_by(DeviceCommand.created_at.asc())
        .count()
    )
    return jsonify({"ok": True, "active_session": _serialize_session(active_session), "pending_commands": pending})


@device_bp.route("/commands/next", methods=["GET"])
@device_required
def next_command():
    stale_before = datetime.utcnow() - timedelta(seconds=60)
    (
        DeviceCommand.query.filter_by(device_id=request.device.id, status="in_progress")
        .filter(DeviceCommand.created_at < stale_before)
        .update({"status": "failed", "completed_at": datetime.utcnow()})
    )
    db.session.commit()

    command = (
        DeviceCommand.query.filter_by(device_id=request.device.id, status="queued")
        .order_by(DeviceCommand.created_at.asc())
        .first()
    )
    if not command:
        return jsonify({"ok": True, "command": None})

    command.status = "in_progress"
    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "command": {
                "id": command.id,
                "type": command.command_type,
                "payload": json.loads(command.payload_json),
            },
        }
    )


@device_bp.route("/commands/<int:command_id>/complete", methods=["POST"])
@device_required
def complete_command(command_id: int):
    command = DeviceCommand.query.filter_by(id=command_id, device_id=request.device.id).first_or_404()
    payload = request.get_json(force=True, silent=True) or {}
    command.status = payload.get("status", "completed")
    command.result_message = payload.get("message")
    command.completed_at = datetime.utcnow()

    if command.command_type == "enroll_fingerprint" and command.status == "completed":
        command_payload = json.loads(command.payload_json)
        student = Student.query.get(command_payload["student_id"])
        template_id = int(payload.get("template_id") or 0)
        if student is None or template_id <= 0:
            return jsonify({"ok": False, "error": "valid student and template_id are required"}), 400
        if student.fingerprint_profile:
            student.fingerprint_profile.template_id = template_id
        else:
            db.session.add(FingerprintProfile(student=student, template_id=template_id))

    db.session.commit()
    return jsonify({"ok": True})


@device_bp.route("/verify-qr", methods=["POST"])
@device_required
def verify_qr():
    image_bytes = request.get_data()
    qr_text = decode_qr_from_bytes(image_bytes)
    if not qr_text:
        return jsonify({"ok": False, "error": "QR code not detected"}), 400

    session = Session.query.filter_by(qr_payload=qr_text, is_active=True).first()
    if not session:
        return jsonify({"ok": False, "error": "invalid or inactive session QR"}), 400

    if not _session_is_open(session):
        return jsonify({"ok": False, "error": "session is outside its active time window"}), 400

    return jsonify({"ok": True, "session": _serialize_session(session)})


@device_bp.route("/verify-face", methods=["POST"])
@device_required
def verify_face():
    session_token = request.headers.get("X-Session-Token", "")
    session = Session.query.filter_by(session_token=session_token, is_active=True).first()
    if not session:
        return jsonify({"ok": False, "error": "active session not found"}), 404

    result = verify_face_for_session(session, request.get_data())
    if not result.matched:
        return jsonify({"ok": False, "error": result.reason, "distance": result.distance}), 400

    existing = PendingFingerprintVerification.query.filter_by(
        student_id=result.student.id,
        session_id=session.id,
        status="pending",
    ).first()
    if existing is None:
        db.session.add(
            PendingFingerprintVerification(
                student=result.student,
                session=session,
                camera_device=request.device,
                message="face verified; waiting for fingerprint",
            )
        )
        db.session.commit()

    return jsonify({"ok": True, "student": _serialize_student(result.student), "distance": result.distance})


@device_bp.route("/pending-fingerprint", methods=["GET"])
@device_required
def pending_fingerprint():
    active_session = Session.query.filter_by(is_active=True).order_by(Session.starts_at.desc()).first()
    stale_query = PendingFingerprintVerification.query.filter_by(status="pending")
    if active_session is None:
        stale_query.update(
            {
                "status": "failed",
                "message": "no active session",
                "completed_at": datetime.utcnow(),
            }
        )
    else:
        stale_query.filter(PendingFingerprintVerification.session_id != active_session.id).update(
            {
                "status": "failed",
                "message": "session changed before fingerprint verification",
                "completed_at": datetime.utcnow(),
            }
        )
    db.session.commit()

    pending = (
        PendingFingerprintVerification.query.filter_by(status="pending")
        .order_by(PendingFingerprintVerification.created_at.asc())
        .first()
    )
    return jsonify({"ok": True, "pending": _serialize_pending_fingerprint(pending)})


@device_bp.route("/fingerprint-status", methods=["GET"])
@device_required
def fingerprint_status():
    session_token = request.args.get("session_token", "")
    student_id = int(request.args.get("student_id") or 0)
    session = Session.query.filter_by(session_token=session_token).first()
    if session is None or student_id <= 0:
        return jsonify({"ok": False, "error": "session_token and student_id are required"}), 400
    pending = (
        PendingFingerprintVerification.query.filter_by(session_id=session.id, student_id=student_id)
        .order_by(PendingFingerprintVerification.created_at.desc())
        .first()
    )
    if pending is None:
        return jsonify({"ok": True, "status": "failed", "message": "no fingerprint request"})
    if not session.is_active:
        pending.status = "failed"
        pending.message = "session changed before fingerprint verification"
        pending.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"ok": True, "status": pending.status, "message": pending.message})
    return jsonify({"ok": True, "status": pending.status, "message": pending.message or ""})


@device_bp.route("/complete-fingerprint", methods=["POST"])
@device_required
def complete_fingerprint():
    payload = request.get_json(force=True)
    pending_id = int(payload.get("pending_id") or 0)
    template_id = int(payload.get("template_id") or 0)

    pending = PendingFingerprintVerification.query.filter_by(id=pending_id, status="pending").first()
    if pending is None:
        return jsonify({"ok": False, "error": "pending fingerprint request not found"}), 404
    if not _session_is_open(pending.session):
        pending.status = "failed"
        pending.message = "session closed before fingerprint verification"
        pending.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"ok": False, "error": "session is not currently accepting attendance"}), 409

    profile = pending.student.fingerprint_profile
    if profile is None:
        return jsonify({"ok": False, "error": "student has no fingerprint template"}), 400
    if int(profile.template_id) != template_id:
        return jsonify({"ok": False, "error": "fingerprint does not match face-verified student"}), 400

    duplicate = AttendanceRecord.query.filter_by(
        student_id=pending.student_id,
        session_id=pending.session_id,
        status="present",
    ).first()
    if duplicate and not pending.session.allow_duplicates:
        pending.status = "failed"
        pending.message = "duplicate attendance rejected"
        pending.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"ok": False, "error": "duplicate attendance rejected"}), 409

    record = AttendanceRecord(
        student=pending.student,
        session=pending.session,
        device_id=request.device.id,
        verified_by_qr=True,
        verified_by_face=True,
        verified_by_fingerprint=True,
        note="verified by ESP32-CAM + fingerprint node",
        status="present",
    )
    pending.status = "completed"
    pending.message = "attendance marked"
    pending.completed_at = datetime.utcnow()
    db.session.add(record)
    db.session.commit()
    return jsonify({"ok": True, "attendance_id": record.id, "timestamp": record.created_at.isoformat()})


@device_bp.route("/resolve-fingerprint-student", methods=["POST"])
@device_required
def resolve_fingerprint_student():
    payload = request.get_json(force=True)
    session = Session.query.filter_by(session_token=payload["session_token"]).first_or_404()
    template_id = int(payload.get("template_id") or 0)

    if template_id <= 0:
        return jsonify({"ok": False, "error": "template_id is required"}), 400
    if not _session_is_open(session):
        return jsonify({"ok": False, "error": "session is not currently accepting attendance"}), 409

    profile = FingerprintProfile.query.filter_by(template_id=template_id).first()
    if profile is None or profile.student is None:
        return jsonify({"ok": False, "error": "fingerprint template not registered"}), 404

    student = profile.student
    if not student.active:
        return jsonify({"ok": False, "error": "student is inactive"}), 409
    if student.class_name != session.class_name:
        return jsonify({"ok": False, "error": "student is not assigned to this class"}), 400

    return jsonify({"ok": True, "student": _serialize_student(student)})


@device_bp.route("/mark-attendance", methods=["POST"])
@device_required
def mark_attendance():
    payload = request.get_json(force=True)
    session = Session.query.filter_by(session_token=payload["session_token"]).first_or_404()
    student = Student.query.get_or_404(int(payload["student_id"]))

    if not _session_is_open(session):
        return jsonify({"ok": False, "error": "session is not currently accepting attendance"}), 409

    if student.class_name != session.class_name:
        return jsonify({"ok": False, "error": "student is not assigned to this class"}), 400
    if not student.active:
        return jsonify({"ok": False, "error": "student is inactive"}), 409

    duplicate = AttendanceRecord.query.filter_by(student_id=student.id, session_id=session.id, status="present").first()
    if duplicate and not session.allow_duplicates:
        return jsonify({"ok": False, "error": "duplicate attendance rejected"}), 409

    record = AttendanceRecord(
        student=student,
        session=session,
        device_id=request.device.id,
        verified_by_qr=bool(payload.get("verified_by_qr")),
        verified_by_face=bool(payload.get("verified_by_face")),
        verified_by_fingerprint=bool(payload.get("verified_by_fingerprint")),
        note=payload.get("note"),
        status="present",
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"ok": True, "attendance_id": record.id, "timestamp": record.created_at.isoformat()})


@device_bp.route("/log-verification-failure", methods=["POST"])
@device_required
def log_verification_failure():
    payload = request.get_json(force=True)
    session = Session.query.filter_by(session_token=payload["session_token"]).first_or_404()
    student_id = payload.get("student_id")
    status = str(payload.get("status") or "rejected")

    if student_id:
        student = Student.query.get_or_404(int(student_id))
        record = AttendanceRecord(
            student=student,
            session=session,
            device_id=request.device.id,
            verified_by_qr=bool(payload.get("verified_by_qr")),
            verified_by_face=bool(payload.get("verified_by_face")),
            verified_by_fingerprint=bool(payload.get("verified_by_fingerprint")),
            note=payload.get("note"),
            status=status,
        )
        db.session.add(record)
    else:
        event = VerificationEvent(
            student_label=payload.get("student_label") or "Unknown fingerprint",
            class_name=session.class_name,
            session=session,
            session_title=session.title,
            device_id=request.device.id,
            verified_by_qr=bool(payload.get("verified_by_qr")),
            verified_by_face=bool(payload.get("verified_by_face")),
            verified_by_fingerprint=bool(payload.get("verified_by_fingerprint")),
            note=payload.get("note"),
            status=status,
        )
        db.session.add(event)
    db.session.commit()
    created_item = locals().get("record") or locals().get("event")
    return jsonify({"ok": True, "attendance_id": created_item.id, "timestamp": created_item.created_at.isoformat()})
