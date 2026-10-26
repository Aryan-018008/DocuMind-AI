
import re


def _clean_text(text):
    """Normalize whitespace without removing document content."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_page(text, chunk_size, overlap):
    """Split a page into bounded chunks with approximate overlap."""
    text = _clean_text(text)

    if not text:
        return []

    pieces = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        if end < text_length:
            # Prefer a paragraph, line, sentence, or word boundary.
            minimum_end = start + int(chunk_size * 0.60)

            boundaries = [
                text.rfind("\n\n", minimum_end, end),
                text.rfind("\n", minimum_end, end),
                text.rfind(". ", minimum_end, end),
                text.rfind(" ", minimum_end, end),
            ]

            boundary = max(boundaries)

            if boundary >= minimum_end:
                end = boundary + (
                    1 if text[boundary] == "\n" else 0
                )

        piece = text[start:end].strip()

        if piece:
            pieces.append(piece)

        if end >= text_length:
            break

        # Begin the next chunk near the requested overlap.
        next_start = max(start + 1, end - overlap)

        # Avoid splitting a word at the beginning of a chunk.
        while (
            next_start < text_length
            and next_start > 0
            and not text[next_start - 1].isspace()
            and not text[next_start].isspace()
        ):
            next_start += 1

        start = next_start

    return pieces


def chunk_pdf_pages(pages, chunk_size=800, overlap=150):
    """
    Convert extracted PDF pages into chunks.

    Each result contains:
    - chunk_index: globally unique chunk number
    - page: original PDF page number
    - text: chunk content

    There is no maximum chunk-count limit.
    """
    if not isinstance(pages, list):
        raise TypeError("pages must be a list")

    if chunk_size < 1:
        raise ValueError("chunk_size must be greater than 0")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    chunks = []
    chunk_index = 0

    for page_data in pages:
        if not isinstance(page_data, dict):
            continue

        page_number = page_data.get("page")
        page_text = page_data.get("text", "")

        if not isinstance(page_text, str) or not page_text.strip():
            continue

        page_pieces = _split_page(
            page_text,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for piece in page_pieces:
            chunks.append({
                "chunk_index": chunk_index,
                "page": page_number,
                "text": piece,
            })

            chunk_index += 1

    return chunks
