
# import os
# import uuid
# from flask import Blueprint, request, jsonify, current_app
# from werkzeug.utils import secure_filename

# from services.pdf_service import extract_pdf_text

# document_bp = Blueprint("documents", __name__)

# MAX_FILE_SIZE = 20 * 1024 * 1024


# @document_bp.route("/api/documents/upload", methods=["POST"])
# def upload_document():
#     if "file" not in request.files:
#         return jsonify({"error": "No file was provided."}), 400

#     file = request.files["file"]

#     if not file.filename:
#         return jsonify({"error": "Please select a PDF."}), 400

#     if not file.filename.lower().endswith(".pdf"):
#         return jsonify({"error": "Only PDF files are allowed."}), 400

#     original_name = secure_filename(file.filename)

#     if not original_name:
#         return jsonify({"error": "Invalid filename."}), 400

#     upload_dir = current_app.config["UPLOAD_FOLDER"]
#     os.makedirs(upload_dir, exist_ok=True)

#     saved_path = None

#     try:
#         # Stream to disk with a hard size limit.
#         saved_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}.pdf")
#         total_bytes = 0

#         file.stream.seek(0)

#         with open(saved_path, "wb") as output:
#             while True:
#                 chunk = file.stream.read(1024 * 1024)
#                 if not chunk:
#                     break

#                 total_bytes += len(chunk)
#                 if total_bytes > MAX_FILE_SIZE:
#                     raise ValueError("PDF must be 20 MB or smaller.")

#                 output.write(chunk)

#         # Basic PDF signature check, followed by actual parser validation.
#         with open(saved_path, "rb") as saved_file:
#             if not saved_file.read(5).startswith(b"%PDF-"):
#                 raise ValueError("The uploaded file is not a valid PDF.")

#         pages = extract_pdf_text(saved_path)

#         return jsonify({
#             "message": "PDF uploaded and text extracted successfully.",
#             "document": {
#                 "filename": original_name,
#                 "pages": len(pages),
#                 "characters": sum(len(p["text"]) for p in pages),
#                 "status": "extracted"
#             },
#             "preview": [
#                 {"page": p["page"], "text": p["text"][:250]}
#                 for p in pages[:3]
#             ]
#         }), 200

#     except ValueError as exc:
#         if saved_path and os.path.exists(saved_path):
#             os.remove(saved_path)
#         return jsonify({"error": str(exc)}), 400

#     except Exception:
#         if saved_path and os.path.exists(saved_path):
#             os.remove(saved_path)
#         current_app.logger.exception("PDF processing failed")
#         return jsonify({
#             "error": "Unable to process this PDF. Please try another file."
#         }), 500


import os
import uuid

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from services.pdf_service import extract_pdf_text
from database.db import get_db_connection

document_bp = Blueprint("documents", __name__)

MAX_FILE_SIZE = 20 * 1024 * 1024


@document_bp.route("/api/documents/upload", methods=["POST"])
def upload_document():

    if "file" not in request.files:
        return jsonify({"error": "No file was provided."}), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({"error": "Please select a PDF."}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed."}), 400

    original_name = secure_filename(file.filename)

    if not original_name:
        return jsonify({"error": "Invalid filename."}), 400

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)

    saved_path = None
    connection = None

    try:
        stored_filename = f"{uuid.uuid4().hex}.pdf"
        saved_path = os.path.join(upload_dir, stored_filename)

        total_bytes = 0

        file.stream.seek(0)

        with open(saved_path, "wb") as output:
            while True:
                chunk = file.stream.read(1024 * 1024)

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > MAX_FILE_SIZE:
                    raise ValueError("PDF must be 20 MB or smaller.")

                output.write(chunk)

        with open(saved_path, "rb") as saved_file:
            if not saved_file.read(5).startswith(b"%PDF-"):
                raise ValueError("The uploaded file is not a valid PDF.")

        pages = extract_pdf_text(saved_path)

        # Save PDF metadata in SQLite
        connection = get_db_connection()

        cursor = connection.execute(
            """
            INSERT INTO documents
                (filename, stored_filename, file_size, page_count, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                original_name,
                stored_filename,
                total_bytes,
                len(pages),
                "extracted"
            )
        )

        connection.commit()
        document_id = cursor.lastrowid

        return jsonify({
            "message": "PDF uploaded and saved to database successfully.",
            "document": {
                "id": document_id,
                "filename": original_name,
                "stored_filename": stored_filename,
                "file_size": total_bytes,
                "pages": len(pages),
                "characters": sum(len(p["text"]) for p in pages),
                "status": "extracted"
            },
            "preview": [
                {
                    "page": p["page"],
                    "text": p["text"][:250]
                }
                for p in pages[:3]
            ]
        }), 200

    except ValueError as exc:
        if saved_path and os.path.exists(saved_path):
            os.remove(saved_path)

        return jsonify({"error": str(exc)}), 400

    except Exception:
        if saved_path and os.path.exists(saved_path):
            os.remove(saved_path)

        current_app.logger.exception("PDF processing failed")

        return jsonify({
            "error": "Unable to process this PDF. Please try another file."
        }), 500

    finally:
        if connection is not None:
            connection.close()



# Extract-GET
@document_bp.route("/api/documents", methods=["GET"])
def get_documents():
    connection = None

    try:
        connection = get_db_connection()

        rows = connection.execute(
            """
            SELECT
                id,
                filename,
                stored_filename,
                file_size,
                page_count,
                upload_date,
                status
            FROM documents
            ORDER BY id DESC
            """
        ).fetchall()

        documents = [dict(row) for row in rows]

        return jsonify({
            "count": len(documents),
            "documents": documents
        }), 200

    except Exception:
        current_app.logger.exception(
            "Failed to retrieve documents"
        )

        return jsonify({
            "error": "Unable to retrieve documents."
        }), 500

    finally:
        if connection is not None:
            connection.close()

