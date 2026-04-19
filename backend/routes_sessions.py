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


@sessions_bp.route("/sessions")
@login_required
def sessions_list():
    sessions = Session.query.order_by(Session.starts_at.desc()).all()
    return render_template("sessions_list.html", sessions=sessions)


@sessions_bp.route("/sessions/new", methods=["GET", "POST"])
@login_required
def session_create():
    if request.method == "POST":
        try:
            starts_at = datetime.fromisoformat(request.form["starts_at"])
            ends_at = datetime.fromisoformat(request.form["ends_at"])
        except ValueError:
            flash("Start and end times must use valid date-time values.", "error")
            return render_template("session_form.html")

        if ends_at <= starts_at:
            flash("End time must be later than the start time.", "error")
            return render_template("session_form.html")

        session_token = secrets.token_urlsafe(18)
        session = Session(
            title=request.form["title"].strip(),
            class_name=request.form["class_name"].strip(),
            starts_at=starts_at,
            ends_at=ends_at,
            session_token=session_token,
            qr_payload=_build_payload(session_token),
            allow_duplicates=request.form.get("allow_duplicates") == "on",
        )
        db.session.add(session)
        db.session.commit()
        flash("Session created.", "success")
        return redirect(url_for("sessions.sessions_list"))
    return render_template("session_form.html")


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
@login_required
def session_qr_png(session_id: int):
    target = Session.query.get_or_404(session_id)
    return Response(generate_qr_png(target.qr_payload), mimetype="image/png")
