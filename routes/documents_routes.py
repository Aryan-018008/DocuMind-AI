
import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from services.pdf_service import extract_pdf_text

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

    try:
        # Stream to disk with a hard size limit.
        saved_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}.pdf")
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

        # Basic PDF signature check, followed by actual parser validation.
        with open(saved_path, "rb") as saved_file:
            if not saved_file.read(5).startswith(b"%PDF-"):
                raise ValueError("The uploaded file is not a valid PDF.")

        pages = extract_pdf_text(saved_path)

        return jsonify({
            "message": "PDF uploaded and text extracted successfully.",
            "document": {
                "filename": original_name,
                "pages": len(pages),
                "characters": sum(len(p["text"]) for p in pages),
                "status": "extracted"
            },
            "preview": [
                {"page": p["page"], "text": p["text"][:250]}
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
