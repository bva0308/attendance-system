from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from database import db
from models import Device, Session, Student


app = create_app()


with app.app_context():
    db.create_all()

    if not Device.query.filter_by(device_id="esp32cam-lab-01").first():
        device = Device(
            device_id="esp32cam-lab-01",
            display_name="Lab Entrance Device",
            api_key_hash=generate_password_hash("demo-device-key"),
        )
        db.session.add(device)

    if not Student.query.filter_by(student_code="STU001").first():
        db.session.add(Student(student_code="STU001", full_name="Demo Student", email="demo@example.com", class_name="ECE-8"))

    if not Session.query.filter_by(title="Embedded Systems Demo").first():
        token = "demo-session-token"
        db.session.add(
            Session(
                title="Embedded Systems Demo",
                class_name="ECE-8",
                starts_at=datetime.utcnow() - timedelta(hours=1),
                ends_at=datetime.utcnow() + timedelta(hours=4),
                session_token=token,
                qr_payload=f"ATTEND:{token}",
                is_active=True,
            )
        )

    db.session.commit()
    print("Seeded demo device, student, and session.")
