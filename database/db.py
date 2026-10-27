
import os
import sqlite3

from flask import current_app


def get_db_connection():
    """Create a connection to the SQLite database."""

    db_path = current_app.config["DATABASE"]

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_db():
    """Create authentication tables and safely extend existing documents."""

    connection = get_db_connection()

    try:
        # 1. Users table for registration and login.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Preserve the existing documents table.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                page_count INTEGER NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'extracted',
                user_id INTEGER REFERENCES users(id)
            )
        """)

        # 3. Safely migrate an existing documents table.
        columns = connection.execute(
            "PRAGMA table_info(documents)"
        ).fetchall()

        column_names = {column["name"] for column in columns}

        if "user_id" not in column_names:
            connection.execute("""
                ALTER TABLE documents
                ADD COLUMN user_id INTEGER REFERENCES users(id)
            """)

        # 4. Store email verification OTP hashes and expiry information.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS email_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL COLLATE NOCASE,
                otp_hash TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_user_id
            ON documents(user_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_email_otps_email
            ON email_otps(email)
        """)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
