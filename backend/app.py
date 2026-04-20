import os
from datetime import datetime

from flask import Flask, render_template

from config import config
from database import db
from routes_attendance import attendance_bp
from routes_auth import auth_bp
from routes_device import device_bp
from routes_sessions import sessions_bp
from routes_students import students_bp


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web", "templates")),
        static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web", "static")),
    )
    app.secret_key = config.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = config.database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["APP_CONFIG"] = config

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(device_bp)

    @app.context_processor
    def inject_globals():
        return {"cfg": config}

    @app.template_filter("datetime_display")
    def datetime_display(value: datetime | None) -> str:
        if value is None:
            return "never"
        return value.strftime("%Y-%m-%d %H:%M:%S")

    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", title="Not found", message="The requested page does not exist."), 404

    return app


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host=config.app_host, port=config.app_port, debug=config.debug)
