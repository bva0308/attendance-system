import json
from datetime import datetime

from flask import Blueprint, jsonify, request

from auth import device_required
from database import db
from models import AttendanceRecord, DeviceCommand, FingerprintProfile, Session, Student
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


def _session_is_open(session: Session) -> bool:
    now = datetime.utcnow()
    return session.is_active and session.starts_at <= now <= session.ends_at


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

    template_id = result.student.fingerprint_profile.template_id if result.student.fingerprint_profile else None
    return jsonify(
        {
            "ok": True,
            "student": {
                "id": result.student.id,
                "student_code": result.student.student_code,
                "full_name": result.student.full_name,
                "class_name": result.student.class_name,
                "fingerprint_template_id": template_id,
            },
            "distance": result.distance,
        }
    )


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
