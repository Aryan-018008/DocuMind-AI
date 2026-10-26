
import os

from flask import Blueprint, current_app, jsonify, request

from services.pdf_service import extract_pdf_text
from services.chunking_service import chunk_pdf_pages
from services.vector_store_service import VectorStore
from services.rag_service import RAGService


chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}

    question = data.get("question", "").strip()
    filename = data.get("filename", "").strip()

    if not question:
        return jsonify({
            "error": "Please provide a question."
        }), 400

    if not filename:
        return jsonify({
            "error": "Please provide the PDF filename."
        }), 400

    # Prevent directory traversal; accept a filename only.
    if os.path.basename(filename) != filename:
        return jsonify({
            "error": "Invalid PDF filename."
        }), 400

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    pdf_path = os.path.join(upload_folder, filename)
    print("\n--- PDF DEBUG ---")
    print("Received filename:", repr(filename))
    print("UPLOAD_FOLDER:", repr(upload_folder))
    print("Resolved path:", os.path.abspath(pdf_path))
    print("File exists:", os.path.isfile(pdf_path))
    print("Files in upload folder:", os.listdir(upload_folder))
    print("-----------------\n")

    if not os.path.isfile(pdf_path) or not filename.lower().endswith(".pdf"):
        return jsonify({
            "error": "PDF not found in uploads."
        }), 404

    try:
        # Extract PDF text and generate chunks.
        pages = extract_pdf_text(pdf_path)
        chunks = chunk_pdf_pages(pages)

        if not chunks:
            return jsonify({
                "error": "No readable text found in this PDF."
            }), 422

        # Build the vector index for this PDF.
        vector_store = VectorStore()
        vector_store.build_index(chunks)

        # Generate an answer using the existing RAG service.
        rag_service = RAGService(vector_store)
        result = rag_service.answer_question(question)

        return jsonify({
            "answer": result["answer"],
            "sources": result["sources"],
            "filename": filename
        }), 200

    except Exception:
        current_app.logger.exception("Chat API failed")
        return jsonify({
            "error": "Failed to process your question. Check the server logs."
        }), 500
