import os
from dataclasses import dataclass


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass
class Config:
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///attendance.db")
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    admin_username: str = os.getenv("ADMIN_USERNAME", "ybibha22@tbc.edu.np")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "Bibha@28")
    admin_password_hash: str = os.getenv(
        "ADMIN_PASSWORD_HASH",
        "scrypt:32768:8:1$demoSalt$e5e9d0ca6538dc06c0d2c7c065af246a98a6a740249bca7ff280991690e54cf91497b1af6e1d889d7c3fd261bd31d25a4d8244334630bf8c1227bcddc3e39fb1",
    )
    face_distance_threshold: float = float(os.getenv("FACE_DISTANCE_THRESHOLD", "0.52"))
    session_qr_prefix: str = os.getenv("SESSION_QR_PREFIX", "ATTEND")
    relay_pulse_seconds: int = int(os.getenv("RELAY_PULSE_SECONDS", "2"))
    face_provider: str = os.getenv("FACE_PROVIDER", "face_recognition")
    github_client_id: str = os.getenv("GITHUB_CLIENT_ID", "")
    github_client_secret: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    github_redirect_uri: str = os.getenv("GITHUB_REDIRECT_URI", "")
    github_allowed_users: tuple[str, ...] = _split_csv(os.getenv("GITHUB_ALLOWED_USERS", ""))
    github_allowed_emails: tuple[str, ...] = _split_csv(os.getenv("GITHUB_ALLOWED_EMAILS", os.getenv("ADMIN_USERNAME", "")))
    github_scope: str = os.getenv("GITHUB_SCOPE", "read:user user:email")
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "5000"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


config = Config()
