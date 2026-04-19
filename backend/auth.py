from functools import wraps

from flask import abort, current_app, jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash

from models import Device


def verify_admin_credentials(username: str, password: str) -> bool:
    cfg = current_app.config["APP_CONFIG"]
    if username != cfg.admin_username:
        return False

    password_hash = getattr(cfg, "admin_password_hash", "")
    if password_hash:
        return check_password_hash(password_hash, password)

    plain_password = getattr(cfg, "admin_password", "")
    if plain_password:
        return password == plain_password

    return False


def is_github_login_enabled() -> bool:
    cfg = current_app.config["APP_CONFIG"]
    return bool(cfg.github_client_id and cfg.github_client_secret)


def is_allowed_github_identity(login: str, email: str) -> bool:
    cfg = current_app.config["APP_CONFIG"]
    normalized_login = (login or "").strip().lower()
    normalized_email = (email or "").strip().lower()

    allowed_users = {item.lower() for item in cfg.github_allowed_users}
    allowed_emails = {item.lower() for item in cfg.github_allowed_emails}

    if allowed_users and normalized_login in allowed_users:
        return True

    if allowed_emails and normalized_email in allowed_emails:
        return True

    if not allowed_users and not allowed_emails:
        return normalized_email == cfg.admin_username.strip().lower()

    return False


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapper


def admin_api_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return jsonify({"ok": False, "error": "authentication required"}), 401
        return view_func(*args, **kwargs)

    return wrapper


def device_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        device_identifier = request.headers.get("X-Device-Id", "").strip()
        device_key = request.headers.get("X-Device-Key", "").strip()
        if not device_identifier or not device_key:
            return jsonify({"ok": False, "error": "missing device credentials"}), 401

        device = Device.query.filter_by(device_id=device_identifier, is_active=True).first()
        if not device or not check_password_hash(device.api_key_hash, device_key):
            return jsonify({"ok": False, "error": "invalid device credentials"}), 401

        request.device = device
        return view_func(*args, **kwargs)

    return wrapper


def api_abort(message: str, code: int = 400):
    response = jsonify({"ok": False, "error": message})
    response.status_code = code
    abort(response)
