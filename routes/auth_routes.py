
import os
import re
import time
import secrets
import resend

from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

from database.db import get_db_connection



auth_bp = Blueprint("auth", __name__)

OTP_EXPIRY_SECONDS = 300
MAX_OTP_ATTEMPTS = 5




def send_otp_email(email, otp):
    """Send verification OTP using Resend API."""

    api_key = os.getenv("RESEND_API_KEY")

    if not api_key:
        raise RuntimeError("RESEND_API_KEY is missing.")

    resend.api_key = api_key

    params = {
        "from": "DocuMind AI <onboarding@resend.dev>",
        "to": [email],
        "subject": "Verify your DocuMind AI account",
        "text": f"""Hello,

Your DocuMind AI verification code is: {otp}

This code expires in 5 minutes.
Do not share this code with anyone.

If you did not request this code, you can ignore this email.

Regards,
DocuMind AI Team
"""
    }

    result = resend.Emails.send(params)

    current_app.logger.info(
        "Verification email accepted by Resend. Email ID: %s",
        result.get("id")
    )

    return result



@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("SignUp.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or len(name) > 100:
        flash("Please enter a valid name.", "error")
        return redirect(url_for("auth.signup"))

    if len(email) > 254 or not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", email
    ):
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("auth.signup"))

    if len(password) < 8 or len(password) > 128:
        flash("Password must contain 8–128 characters.", "error")
        return redirect(url_for("auth.signup"))

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("auth.signup"))

    connection = get_db_connection()

    try:
        existing_user = connection.execute(
            "SELECT id, is_verified FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if existing_user and existing_user["is_verified"]:
            flash("An account with this email already exists. Please log in.", "error")
            return redirect(url_for("auth.login"))

        # Remove any previous unverified account for this email.
        if existing_user:
            connection.execute(
                "DELETE FROM email_otps WHERE email = ?", (email,)
            )
            connection.execute(
                "DELETE FROM users WHERE id = ?", (existing_user["id"],)
            )
            connection.commit()

        otp = f"{secrets.randbelow(1_000_000):06d}"
        otp_hash = generate_password_hash(otp)
        expires_at = int(time.time()) + OTP_EXPIRY_SECONDS
        password_hash = generate_password_hash(password)

        connection.execute(
            """
            INSERT INTO users (name, email, password_hash, is_verified)
            VALUES (?, ?, ?, 0)
            """,
            (name, email, password_hash),
        )

        connection.execute(
            """
            INSERT INTO email_otps (email, otp_hash, expires_at)
            VALUES (?, ?, ?)
            """,
            (email, otp_hash, expires_at),
        )

        connection.commit()

        try:
            send_otp_email(email, otp)
        except Exception:
            current_app.logger.exception("OTP email delivery failed")

            connection.execute(
                "DELETE FROM email_otps WHERE email = ?", (email,)
            )
            connection.execute(
                "DELETE FROM users WHERE email = ? AND is_verified = 0",
                (email,),
            )
            connection.commit()

            flash(
                "We couldn't send the verification email. Check the server configuration and try again.",
                "error",
            )
            return redirect(url_for("auth.signup"))

        session["pending_verification_email"] = email

        flash("Verification code sent to your email.", "success")
        return redirect(url_for("auth.verify_otp"))

    except Exception:
        connection.rollback()
        current_app.logger.exception("Signup failed")
        flash("Unable to create your account right now.", "error")
        return redirect(url_for("auth.signup"))

    finally:
        connection.close()


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    email = session.get("pending_verification_email")

    if not email:
        flash("Please sign up before verifying your email.", "error")
        return redirect(url_for("auth.signup"))

    if request.method == "GET":
        return render_template("otp_verification.html", email=email)

    otp = request.form.get("otp", "").strip()

    if not re.fullmatch(r"\d{6}", otp):
        flash("Enter the 6-digit verification code.", "error")
        return redirect(url_for("auth.verify_otp"))

    connection = get_db_connection()

    try:
        record = connection.execute(
            """
            SELECT id, otp_hash, expires_at, attempts
            FROM email_otps
            WHERE email = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (email,),
        ).fetchone()

        if not record:
            flash("No active verification code. Please sign up again.", "error")
            session.pop("pending_verification_email", None)
            return redirect(url_for("auth.signup"))

        if record["attempts"] >= MAX_OTP_ATTEMPTS:
            connection.execute(
                "DELETE FROM email_otps WHERE email = ?", (email,)
            )
            connection.commit()
            session.pop("pending_verification_email", None)
            flash("Too many attempts. Please sign up again.", "error")
            return redirect(url_for("auth.signup"))

        if int(time.time()) > record["expires_at"]:
            connection.execute(
                "DELETE FROM email_otps WHERE email = ?", (email,)
            )
            connection.commit()
            session.pop("pending_verification_email", None)
            flash("Verification code expired. Please sign up again.", "error")
            return redirect(url_for("auth.signup"))

        if not check_password_hash(record["otp_hash"], otp):
            connection.execute(
                "UPDATE email_otps SET attempts = attempts + 1 WHERE id = ?",
                (record["id"],),
            )
            connection.commit()
            flash("Incorrect verification code.", "error")
            return redirect(url_for("auth.verify_otp"))

        connection.execute(
            "UPDATE users SET is_verified = 1 WHERE email = ?",
            (email,),
        )
        connection.execute(
            "DELETE FROM email_otps WHERE email = ?", (email,)
        )
        connection.commit()

        session.pop("pending_verification_email", None)

        flash("Email verified successfully! Please log in.", "success")
        return redirect(url_for("auth.login"))

    except Exception:
        connection.rollback()
        current_app.logger.exception("OTP verification failed")
        flash("Unable to verify your email right now.", "error")
        return redirect(url_for("auth.verify_otp"))

    finally:
        connection.close()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    connection = get_db_connection()

    try:
        user = connection.execute(
            """
            SELECT id, name, email, password_hash, is_verified
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        if not user or not check_password_hash(
            user["password_hash"], password
        ):
            flash("Invalid email or password.", "error")
            return redirect(url_for("auth.login"))

        if not user["is_verified"]:
            flash("Please verify your email before logging in.", "error")
            return redirect(url_for("auth.login"))

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]

        return redirect(url_for("dashboard"))

    except Exception:
        current_app.logger.exception("Login failed")
        flash("Unable to log in right now.", "error")
        return redirect(url_for("auth.login"))

    finally:
        connection.close()


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("landing"))
