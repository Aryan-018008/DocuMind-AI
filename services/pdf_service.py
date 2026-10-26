
import unicodedata
import pymupdf


def normalize_pdf_text(text):
    """Normalize common PDF character-mapping artifacts."""
    text = unicodedata.normalize("NFKC", text)

    # Fix the specific character seen in the uploaded PDF text.
    text = text.replace("\u019f", "ti")  # Ɵ
    text = text.replace("\u0275", "ti")  # ɵ
    text = text.replace("\u03b8", "ti")  # θ
    text = text.replace("\u03f4", "ti")  # ϴ

    return text


def extract_test_schedule_fields(page):
    """Reconstruct schedule fields using measured PDF word coordinates."""
    words = page.get_text("words")

    header_y = 268
    value_y = 305
    tolerance = 4

    def row_words(target_y):
        return [
            (float(word[0]), str(word[4]))
            for word in words
            if abs(float(word[1]) - target_y) <= tolerance
        ]

    headers = row_words(header_y)
    values = row_words(value_y)

    def text_in_range(items, left, right):
        return " ".join(
            text
            for x, text in sorted(items, key=lambda item: item[0])
            if left <= x < right
        ).strip()

    date_value = text_in_range(values, 40, 130)
    reporting_value = text_in_range(values, 130, 230)
    gate_value = text_in_range(values, 230, 330)
    timing_value = text_in_range(values, 330, 450)

    header_text = " ".join(
        text for _, text in sorted(headers, key=lambda item: item[0])
    )

    if not all([
        "Date" in header_text,
        "Reporting" in header_text,
        "Closure" in header_text,
        "Timing" in header_text,
        date_value,
        reporting_value,
        gate_value,
        timing_value,
    ]):
        return ""

    return (
        "\n\nStructured Test Schedule:\n"
        f"Date of Test: {date_value}\n"
        f"Reporting Time: {reporting_value}\n"
        f"Gate Closure Time: {gate_value}\n"
        f"Test Timing: {timing_value}\n"
    )


def extract_pdf_text(file_path):
    """Extract PDF text while preserving page numbers and schedule fields."""
    pages = []

    with pymupdf.open(file_path) as pdf:
        if pdf.is_encrypted:
            raise ValueError(
                "Password-protected PDFs are not supported yet."
            )

        if len(pdf) == 0:
            raise ValueError("The PDF has no pages.")

        for page_number, page in enumerate(pdf, start=1):
            # Extract original text as a fallback.
            original_text = page.get_text("text", sort=True).strip()
            original_text = normalize_pdf_text(original_text)

            # Detect the structured test schedule.
            schedule_text = extract_test_schedule_fields(page)

            # Reconstruct text lines using word coordinates.
            words = page.get_text("words", sort=True)
            rows = {}

            for word in words:
                x0, y0, x1, y1, word_text = word[:5]

                row_key = round(y0 / 5) * 5
                rows.setdefault(row_key, []).append(
                    (x0, word_text)
                )

            reconstructed_lines = []

            for row_key in sorted(rows):
                row_words = sorted(
                    rows[row_key],
                    key=lambda item: item[0],
                )

                line = " ".join(
                    word_text for _, word_text in row_words
                ).strip()

                if line:
                    reconstructed_lines.append(line)

            if reconstructed_lines:
                reconstructed_text = "\n".join(
                    reconstructed_lines
                ).strip()
            else:
                reconstructed_text = original_text

            # IMPORTANT: Normalize AFTER reconstruction, on EVERY page.
            reconstructed_text = normalize_pdf_text(
                reconstructed_text
            )

            # Append the schedule after reconstruction.
            if schedule_text:
                reconstructed_text += normalize_pdf_text(schedule_text)
                print("DEBUG: Schedule detected successfully")

            print(
                "DEBUG final text contains schedule:",
                "Structured Test Schedule:" in reconstructed_text,
            )

            if reconstructed_text:
                pages.append({
                    "page": page_number,
                    "text": reconstructed_text,
                })

    if not pages:
        raise ValueError(
            "No readable text found. The PDF may be scanned or image-only."
        )

    return pages
