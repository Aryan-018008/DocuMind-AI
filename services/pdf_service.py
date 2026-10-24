# # import fitz  # PyMuPDF

# # def extract_pdf_text(file_path):
# #     """Extract text from a PDF while preserving page numbers."""
# #     pages = []

# #     with fitz.open(file_path) as pdf:
# #         if pdf.is_encrypted:
# #             raise ValueError("Password-protected PDFs are not supported yet.")

# #         if len(pdf) == 0:
# #             raise ValueError("The PDF has no pages.")

# #         for page_number, page in enumerate(pdf, start=1):
# #             text = page.get_text("text" , sort= True).strip()

# #             if text:
# #                 pages.append({
# #                     "page": page_number,
# #                     "text": text
# #                 })

# #     if not pages:
# #         raise ValueError(
# #             "No readable text found. The PDF may be scanned or image-only."
# #         )

# #     return pages


# import fitz  # PyMuPDF


# def extract_pdf_text(file_path):
#     """Extract PDF text and preserve table-like rows using word positions."""
#     pages = []

#     with fitz.open(file_path) as pdf:
#         if pdf.is_encrypted:
#             raise ValueError(
#                 "Password-protected PDFs are not supported yet."
#             )

#         if len(pdf) == 0:
#             raise ValueError("The PDF has no pages.")

#         for page_number, page in enumerate(pdf, start=1):
#             # Keep PyMuPDF's sorted text extraction as the default.
#             text = page.get_text("text", sort=True).strip()
#             schedule_text = extract_test_schedule_fields(page)

#             if schedule_text:
#                  text += schedule_text

#             # Detect table-like rows using word coordinates.
#             words = page.get_text("words", sort=True)
#             rows = {}

#             for word in words:
#                 x0, y0, x1, y1, word_text = word[:5]

#                 # Group words that lie on approximately the same line.
#                 row_key = round(y0 / 5) * 5
#                 rows.setdefault(row_key, []).append(
#                     (x0, x1, word_text)
#                 )

#             reconstructed_lines = []

#             for row_key in sorted(rows):
#                 row_words = sorted(
#                     rows[row_key],
#                     key=lambda item: item[0]
#                 )

#                 line = " ".join(
#                     item[2] for item in row_words
#                 ).strip()

#                 if line:
#                     reconstructed_lines.append(line)

#             # Use reconstructed lines only if extraction produced content.
#             # The original sorted text remains the fallback.
#             if reconstructed_lines:
#                 reconstructed_text = "\n".join(
#                     reconstructed_lines
#                 ).strip()
#             else:
#                 reconstructed_text = text

#             if reconstructed_text:
#                 pages.append({
#                     "page": page_number,
#                     "text": reconstructed_text
#                 })

#     if not pages:
#         raise ValueError(
#             "No readable text found. The PDF may be scanned or image-only."
#         )

#     return pages



# def extract_test_schedule_fields(page):
#     """Reconstruct the four schedule fields from their PDF coordinates."""
#     words = page.get_text("words")

#     header_y = 268
#     value_y = 305
#     tolerance = 4

#     def row_words(target_y):
#         return [
#             (float(w[0]), str(w[4]))
#             for w in words
#             if abs(float(w[1]) - target_y) <= tolerance
#         ]

#     headers = row_words(header_y)
#     values = row_words(value_y)

#     def text_in_range(items, left, right):
#         return " ".join(
#             word for x, word in sorted(items) if left <= x < right
#         ).strip()

#     # Column boundaries are based on the coordinates you measured.
#     date_value = text_in_range(values, 40, 130)
#     reporting_value = text_in_range(values, 130, 230)
#     gate_value = text_in_range(values, 230, 330)
#     timing_value = text_in_range(values, 330, 450)

#     header_text = " ".join(word for _, word in sorted(headers))

#     if not all([
#         "Date" in header_text,
#         "Reporting" in header_text,
#         "Closure" in header_text,
#         "Timing" in header_text,
#         date_value,
#         reporting_value,
#         gate_value,
#         timing_value,
#     ]):
#         return ""

#     return (
#         "\n\nStructured Test Schedule:\n"
#         f"Date of Test: {date_value}\n"
#         f"Reporting Time: {reporting_value}\n"
#         f"Gate Closure Time: {gate_value}\n"
#         f"Test Timing: {timing_value}\n"
#     )


import fitz  # PyMuPDF
import unicodedata


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

    with fitz.open(file_path) as pdf:
        if pdf.is_encrypted:
            raise ValueError(
                "Password-protected PDFs are not supported yet."
            )

        if len(pdf) == 0:
            raise ValueError("The PDF has no pages.")

        for page_number, page in enumerate(pdf, start=1):
            # Extract the original text in reading order.
            text = page.get_text("text", sort=True).strip()
            text = unicodedata.normalize("NFKC", text)
            text = text.replace("Ɵ", "ti")

            # Reconstruct the schedule table where its layout is recognized.
            schedule_text = extract_test_schedule_fields(page)
            print("DEBUG schedule_text:", repr(schedule_text))

            # Reconstruct text lines from word coordinates.
            words = page.get_text("words", sort=True)
            rows = {}

            for word in words:
                x0, y0, x1, y1, word_text = word[:5]

                # Group words on approximately the same horizontal line.
                row_key = round(y0 / 5) * 5
                rows.setdefault(row_key, []).append(
                    (x0, word_text)
                )

            reconstructed_lines = []

            for row_key in sorted(rows):
                row_words = sorted(
                    rows[row_key],
                    key=lambda item: item[0]
                )

                line = " ".join(
                    word_text for _, word_text in row_words
                ).strip()

                if line:
                    reconstructed_lines.append(line)

            # Use reconstructed text when available; otherwise retain
            # the original PyMuPDF text extraction.
            if reconstructed_lines:
                reconstructed_text = "\n".join(
                    reconstructed_lines
                ).strip()
            else:
                reconstructed_text = text

            # Append the schedule AFTER reconstruction so it is not lost.
            if schedule_text:
                reconstructed_text += schedule_text
                print("DEBUG: Schedule detected successfully")
            print(
               "DEBUG final text contains schedule:",
               "Structured Test Schedule:" in reconstructed_text
             )

            if reconstructed_text:
                pages.append({
                    "page": page_number,
                    "text": reconstructed_text
                })

    if not pages:
        raise ValueError(
            "No readable text found. The PDF may be scanned or image-only."
        )

    return pages
