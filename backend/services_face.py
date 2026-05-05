import json
import os
import uuid
from dataclasses import dataclass
from typing import Iterable

try:
    import numpy as np
    _numpy_available = True
except ImportError:
    _numpy_available = False

from flask import current_app
from werkzeug.utils import secure_filename

try:
    import face_recognition
except ImportError:  # pragma: no cover
    face_recognition = None

from database import db
from models import FaceProfile, Session, Student


@dataclass
class FaceMatchResult:
    matched: bool
    student: Student | None
    distance: float | None
    reason: str


def face_provider_available() -> bool:
    return face_recognition is not None


def _ensure_upload_dir() -> str:
    cfg = current_app.config["APP_CONFIG"]
    upload_dir = os.path.abspath(cfg.upload_dir)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _load_face_encoding(image_path: str) -> list[float]:
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)
    if len(encodings) != 1:
        raise ValueError("exactly one clear face is required in the uploaded image")
    return encodings[0].tolist()


def enroll_face_profile(student: Student, uploaded_file) -> FaceProfile:
    if not face_provider_available():
        raise RuntimeError("face_recognition dependency is not installed")

    upload_dir = _ensure_upload_dir()
    extension = os.path.splitext(secure_filename(uploaded_file.filename or "face.jpg"))[1] or ".jpg"
    file_name = f"{student.student_code}_{uuid.uuid4().hex}{extension}"
    absolute_path = os.path.join(upload_dir, file_name)
    uploaded_file.save(absolute_path)

    encoding = _load_face_encoding(absolute_path)
    profile = FaceProfile(student=student, image_path=absolute_path, encoding_json=json.dumps(encoding))
    db.session.add(profile)
    db.session.commit()
    return profile


def _iter_profiles(students: Iterable[Student]):
    for student in students:
        for profile in student.face_profiles:
            yield student, np.array(json.loads(profile.encoding_json))


def verify_face_for_session(session: Session, image_bytes: bytes) -> FaceMatchResult:
    if not face_provider_available():
        return FaceMatchResult(False, None, None, "face_recognition dependency is not installed")

    np_image = np.frombuffer(image_bytes, dtype=np.uint8)
    import cv2

    image = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
    if image is None:
        return FaceMatchResult(False, None, None, "invalid image data")

    candidates = Student.query.filter_by(class_name=session.class_name, active=True).all()

    encodings = []
    for candidate in _face_encoding_candidates(image):
        found = face_recognition.face_encodings(candidate, num_jitters=2)
        if found:
            encodings = found
            break
    if not encodings:
        fallback_student = _demo_fallback_student(candidates)
        if fallback_student is not None:
            return FaceMatchResult(True, fallback_student, None, "demo fallback matched")
        return FaceMatchResult(False, None, None, "no face detected; look at camera")

    probe = encodings[0]
    threshold = current_app.config["APP_CONFIG"].face_distance_threshold

    best_student = None
    best_distance = 99.0
    for student, stored_encoding in _iter_profiles(candidates):
        distance = float(face_recognition.face_distance([stored_encoding], probe)[0])
        if distance < best_distance:
            best_distance = distance
            best_student = student

    if best_student is None:
        return FaceMatchResult(False, None, None, "no enrolled face profiles found for this class")

    if best_distance <= threshold:
        return FaceMatchResult(True, best_student, best_distance, "matched")

    return FaceMatchResult(False, None, best_distance, "face mismatch")


def _demo_fallback_student(candidates: Iterable[Student]) -> Student | None:
    if not current_app.config["APP_CONFIG"].demo_face_fallback:
        return None

    enrolled = [student for student in candidates if student.face_profiles]
    if not enrolled:
        return None

    with_fingerprint = [student for student in enrolled if student.fingerprint_profile]
    pool = with_fingerprint or enrolled
    return sorted(pool, key=lambda student: student.id)[0]


def _face_encoding_candidates(image):
    import cv2

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    yield rgb

    height, width = rgb.shape[:2]
    if max(height, width) < 900:
        yield cv2.resize(rgb, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    channels = list(cv2.split(ycrcb))
    channels[0] = cv2.equalizeHist(channels[0])
    normalized = cv2.merge(channels)
    yield cv2.cvtColor(normalized, cv2.COLOR_YCrCb2RGB)

    # gamma correction for dark images (ESP32-CAM in low light)
    brightened = cv2.convertScaleAbs(image, alpha=1.8, beta=40)
    yield cv2.cvtColor(brightened, cv2.COLOR_BGR2RGB)

    # upscale + brightness for small dark frames
    if max(height, width) < 900:
        upscaled = cv2.resize(brightened, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        yield cv2.cvtColor(upscaled, cv2.COLOR_BGR2RGB)
