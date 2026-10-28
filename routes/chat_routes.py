
import os

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    session,
)

from routes.auth_helpers import login_required
from database.db import get_db_connection
from services.pdf_service import extract_pdf_text
from services.chunking_service import chunk_pdf_pages
from services.vector_store_service import VectorStore
from services.rag_service import RAGService


chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json(silent=True) or {}

    question = data.get("question", "")
    filename = data.get("filename", "")

    if not isinstance(question, str) or not question.strip():
        return jsonify({
            "error": "Please provide a question."
        }), 400

    if not isinstance(filename, str) or not filename.strip():
        return jsonify({
            "error": "Please provide the PDF filename."
        }), 400

    question = question.strip()
    filename = filename.strip()

    # Prevent directory traversal.
    if os.path.basename(filename) != filename:
        return jsonify({
            "error": "Invalid PDF filename."
        }), 400

    if not filename.lower().endswith(".pdf"):
        return jsonify({
            "error": "Invalid PDF filename."
        }), 400

    # Confirm this PDF belongs to the logged-in user.
    connection = None

    try:
        connection = get_db_connection()

        document = connection.execute(
            """
            SELECT stored_filename
            FROM documents
            WHERE stored_filename = ?
              AND user_id = ?
            """,
            (filename, session["user_id"]),
        ).fetchone()

    except Exception:
        current_app.logger.exception(
            "Failed to verify document ownership"
        )

        return jsonify({
            "error": "Unable to verify document access."
        }), 500

    finally:
        if connection is not None:
            connection.close()

    # Do not reveal whether another user's file exists.
    if not document:
        return jsonify({
            "error": "PDF not found or you do not have access."
        }), 404

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    pdf_path = os.path.join(upload_folder, document["stored_filename"])

    if not os.path.isfile(pdf_path):
        return jsonify({
            "error": "The PDF file is missing from storage."
        }), 404

    # Handle simple greetings and thanks.
    normalized_question = question.lower().rstrip("!.,? ")

    greetings = {
        "hi", "hello", "hey", "hii", "hiii",
        "good morning", "good afternoon", "good evening",
    }

    thanks_messages = {
        "thank you", "thanks", "thank you so much",
        "thanks a lot", "thx", "ty",
    }

    if normalized_question in greetings:
        return jsonify({
            "answer": (
                "Hello! I'm DocuMind AI Assistant. "
                "Ask me anything about your selected PDF."
            ),
            "sources": [],
            "filename": filename,
        }), 200

    if normalized_question in thanks_messages:
        return jsonify({
            "answer": (
                "You're welcome! Feel free to ask another "
                "question about your PDF."
            ),
            "sources": [],
            "filename": filename,
        }), 200

    try:
        # Extract text and generate chunks.
        pages = extract_pdf_text(pdf_path)
        chunks = chunk_pdf_pages(pages)

        if not chunks:
            return jsonify({
                "error": "No readable text found in this PDF."
            }), 422

        # Build the vector index.
        vector_store = VectorStore()
        vector_store.build_index(chunks)

        # Generate the answer using RAG.
        rag_service = RAGService(vector_store)
        result = rag_service.answer_question(question)

        return jsonify({
            "answer": result["answer"],
            "sources": result["sources"],
            "filename": filename,
        }), 200

    except Exception:
        current_app.logger.exception("Chat API failed")

        return jsonify({
            "error": (
                "Failed to process your question. "
                "Please check the server logs."
            )
        }), 500
