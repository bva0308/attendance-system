from datetime import datetime

from sqlalchemy.orm import relationship

from database import db


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_code = db.Column(db.String(32), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    class_name = db.Column(db.String(80), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    face_profiles = relationship("FaceProfile", back_populates="student", cascade="all, delete-orphan")
    fingerprint_profile = relationship(
        "FingerprintProfile", back_populates="student", uselist=False, cascade="all, delete-orphan"
    )
    attendance_records = relationship("AttendanceRecord", back_populates="student")


class FaceProfile(db.Model):
    __tablename__ = "face_profiles"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    encoding_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="face_profiles")


class FingerprintProfile(db.Model):
    __tablename__ = "fingerprint_profiles"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), unique=True, nullable=False)
    template_id = db.Column(db.Integer, unique=True, nullable=False)
    sensor_label = db.Column(db.String(80), default="R307", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="fingerprint_profile")


class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    api_key_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    ip_address = db.Column(db.String(64), nullable=True)
    firmware_version = db.Column(db.String(32), nullable=True)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    last_status = db.Column(db.String(120), nullable=True)
    last_rssi = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    commands = relationship("DeviceCommand", back_populates="device", cascade="all, delete-orphan")


class Session(db.Model):
    __tablename__ = "sessions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    class_name = db.Column(db.String(80), nullable=False)
    starts_at = db.Column(db.DateTime, nullable=False)
    ends_at = db.Column(db.DateTime, nullable=False)
    session_token = db.Column(db.String(128), unique=True, nullable=False)
    qr_payload = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    allow_duplicates = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    attendance_records = relationship("AttendanceRecord", back_populates="session")


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), nullable=True)
    verified_by_qr = db.Column(db.Boolean, default=False, nullable=False)
    verified_by_face = db.Column(db.Boolean, default=False, nullable=False)
    verified_by_fingerprint = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(32), default="present", nullable=False)
    duplicate_rejected = db.Column(db.Boolean, default=False, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="attendance_records")
    session = relationship("Session", back_populates="attendance_records")


class DeviceCommand(db.Model):
    __tablename__ = "device_commands"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), nullable=False)
    command_type = db.Column(db.String(64), nullable=False)
    payload_json = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), default="queued", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    device = relationship("Device", back_populates="commands")
