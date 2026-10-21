
import fitz  # PyMuPDF


def extract_pdf_text(file_path):
    """Extract text from a PDF while preserving page numbers."""
    pages = []

    with fitz.open(file_path) as pdf:
        if pdf.is_encrypted:
            raise ValueError("Password-protected PDFs are not supported yet.")

        if len(pdf) == 0:
            raise ValueError("The PDF has no pages.")

        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()

            if text:
                pages.append({
                    "page": page_number,
                    "text": text
                })

    if not pages:
        raise ValueError(
            "No readable text found. The PDF may be scanned or image-only."
        )

    return pages
