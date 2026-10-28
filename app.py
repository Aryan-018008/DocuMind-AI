
import os

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
)

from dotenv import load_dotenv

from routes.documents_routes import document_bp
from routes.chat_routes import chat_bp
from routes.auth_routes import auth_bp

from database.db import init_db, get_db_connection


# Load environment variables.
load_dotenv()

app = Flask(__name__)

# Application configuration.
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "FLASK_SECRET_KEY is missing from .env"
    )

app.config["MAX_CONTENT_LENGTH"] = 21 * 1024 * 1024

app.config["UPLOAD_FOLDER"] = os.path.join(
    app.root_path,
    "uploads",
)

app.config["DATABASE"] = os.path.join(
    app.root_path,
    "database",
    "documind.db",
)


# Register blueprints.
app.register_blueprint(auth_bp)
app.register_blueprint(document_bp)
app.register_blueprint(chat_bp)


# Initialize database tables.
with app.app_context():
    init_db()


# Public homepage.
@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    return render_template("index.html")


# Protected dashboard.
@app.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("auth.login"))

    connection = get_db_connection()

    try:
        user = connection.execute(
            """
            SELECT id, name, email
            FROM users
            WHERE id = ? AND is_verified = 1
            """,
            (user_id,),
        ).fetchone()

    except Exception:
        app.logger.exception(
            "Failed to verify dashboard user"
        )
        session.clear()
        return redirect(url_for("auth.login"))

    finally:
        connection.close()

    if not user:
        session.clear()
        return redirect(url_for("auth.login"))

    return render_template(
        "dashboard.html",
        user=user,
    )


# Run locally.
if __name__ == "__main__":
    app.run(debug=True)
