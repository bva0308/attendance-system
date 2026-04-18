import json
import secrets
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from auth import is_allowed_github_identity, is_github_login_enabled, verify_admin_credentials


auth_bp = Blueprint("auth", __name__)


def _github_redirect_uri() -> str:
    cfg = current_app.config["APP_CONFIG"]
    return cfg.github_redirect_uri or url_for("auth.github_callback", _external=True)


def _fetch_json(url: str, method: str = "GET", payload: dict | None = None, headers: dict | None = None) -> dict:
    data = None
    request_headers = {"Accept": "application/json", "User-Agent": "attendance-system"}
    if headers:
        request_headers.update(headers)

    if payload is not None:
        data = urlencode(payload).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

    req = Request(url, data=data, headers=request_headers, method=method)
    with urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if verify_admin_credentials(username, password):
            session["admin_authenticated"] = True
            session["admin_username"] = username
            session["auth_provider"] = "password"
            return redirect(url_for("students.dashboard_home"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@auth_bp.route("/login/github")
def login_github():
    if not is_github_login_enabled():
        flash("GitHub login is not configured yet.", "error")
        return redirect(url_for("auth.login"))

    state = secrets.token_urlsafe(24)
    session["github_oauth_state"] = state

    cfg = current_app.config["APP_CONFIG"]
    query = urlencode(
        {
            "client_id": cfg.github_client_id,
            "redirect_uri": _github_redirect_uri(),
            "scope": cfg.github_scope,
            "state": state,
        }
    )
    return redirect(f"https://github.com/login/oauth/authorize?{query}")


@auth_bp.route("/login/github/callback")
def github_callback():
    if not is_github_login_enabled():
        flash("GitHub login is not configured yet.", "error")
        return redirect(url_for("auth.login"))

    if request.args.get("state") != session.get("github_oauth_state"):
        flash("GitHub login could not be verified. Please try again.", "error")
        return redirect(url_for("auth.login"))

    error = request.args.get("error")
    if error:
        flash(f"GitHub login failed: {error}", "error")
        return redirect(url_for("auth.login"))

    code = request.args.get("code", "").strip()
    if not code:
        flash("GitHub did not return an authorization code.", "error")
        return redirect(url_for("auth.login"))

    cfg = current_app.config["APP_CONFIG"]

    try:
        token_payload = _fetch_json(
            "https://github.com/login/oauth/access_token",
            method="POST",
            payload={
                "client_id": cfg.github_client_id,
                "client_secret": cfg.github_client_secret,
                "code": code,
                "redirect_uri": _github_redirect_uri(),
            },
        )
        access_token = token_payload.get("access_token", "")
        if not access_token:
            raise ValueError("missing access token")

        user_payload = _fetch_json(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        emails_payload = _fetch_json(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    except Exception:
        flash("GitHub login could not be completed. Check the OAuth app settings and try again.", "error")
        return redirect(url_for("auth.login"))
    finally:
        session.pop("github_oauth_state", None)

    login_name = (user_payload.get("login") or "").strip()
    verified_email = ""
    if isinstance(emails_payload, list):
        primary_email = next((item for item in emails_payload if item.get("primary") and item.get("verified")), None)
        fallback_email = next((item for item in emails_payload if item.get("verified")), None)
        verified_email = ((primary_email or fallback_email) or {}).get("email", "").strip()

    if not is_allowed_github_identity(login_name, verified_email):
        flash("Your GitHub account is not allowed to access this dashboard.", "error")
        return redirect(url_for("auth.login"))

    session["admin_authenticated"] = True
    session["admin_username"] = verified_email or login_name
    session["auth_provider"] = "github"
    return redirect(url_for("students.dashboard_home"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
