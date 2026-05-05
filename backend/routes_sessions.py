from datetime import datetime
import secrets

from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for

from auth import login_required
from database import db
from models import Session
from services_qr import generate_qr_png


sessions_bp = Blueprint("sessions", __name__)


def _build_payload(session_token: str) -> str:
    prefix = current_app.config["APP_CONFIG"].session_qr_prefix
    return f"{prefix}:{session_token}"


def _session_form_data() -> dict[str, object]:
    return {
        "title": request.form.get("title", "").strip(),
        "class_name": request.form.get("class_name", "").strip(),
        "starts_at": request.form.get("starts_at", ""),
        "ends_at": request.form.get("ends_at", ""),
        "allow_duplicates": request.form.get("allow_duplicates") == "on",
    }


def _render_session_form(form_data: dict[str, object]):
    return render_template("session_form.html", form_data=form_data)


@sessions_bp.route("/sessions")
@login_required
def sessions_list():
    sessions = Session.query.order_by(Session.starts_at.desc()).all()
    return render_template("sessions_list.html", sessions=sessions)


@sessions_bp.route("/sessions/new", methods=["GET", "POST"])
@login_required
def session_create():
    form_data = _session_form_data()
    if request.method == "POST":
        if not form_data["title"] or not form_data["class_name"]:
            flash("Session title and class / section are required.", "error")
            return _render_session_form(form_data)

        try:
            starts_at = datetime.fromisoformat(str(form_data["starts_at"]))
            ends_at = datetime.fromisoformat(str(form_data["ends_at"]))
        except ValueError:
            flash("Start and end times must use valid date-time values.", "error")
            return _render_session_form(form_data)

        if ends_at <= starts_at:
            flash("End time must be later than the start time.", "error")
            return _render_session_form(form_data)

        session_token = secrets.token_urlsafe(18)
        session = Session(
            title=str(form_data["title"]),
            class_name=str(form_data["class_name"]),
            starts_at=starts_at,
            ends_at=ends_at,
            session_token=session_token,
            qr_payload=_build_payload(session_token),
            allow_duplicates=bool(form_data["allow_duplicates"]),
        )
        db.session.add(session)
        db.session.commit()
        flash("Session created.", "success")
        return redirect(url_for("sessions.sessions_list"))
    return _render_session_form(form_data)


@sessions_bp.route("/sessions/<int:session_id>/activate", methods=["POST"])
@login_required
def session_activate(session_id: int):
    target = Session.query.get_or_404(session_id)
    Session.query.update({Session.is_active: False})
    target.is_active = True
    db.session.commit()
    flash(f"Session '{target.title}' is now active.", "success")
    return redirect(url_for("sessions.sessions_list"))


@sessions_bp.route("/sessions/<int:session_id>/deactivate", methods=["POST"])
@login_required
def session_deactivate(session_id: int):
    target = Session.query.get_or_404(session_id)
    target.is_active = False
    db.session.commit()
    flash(f"Session '{target.title}' deactivated.", "success")
    return redirect(url_for("sessions.sessions_list"))


@sessions_bp.route("/sessions/<int:session_id>/qr.png")
def session_qr_png(session_id: int):
    target = Session.query.get_or_404(session_id)
    return Response(generate_qr_png(target.qr_payload), mimetype="image/png")


@sessions_bp.route("/sessions/<int:session_id>/qr")
def session_qr_page(session_id: int):
    target = Session.query.get_or_404(session_id)
    return render_template("session_qr.html", attendance_session=target)
