
import re
# Common labels found in structured documents.
FIELD_LABELS = [
    "Registration Number",
    "Candidate Name",
    "Date of Birth",
    "Exam Venue",
    "Exam Centre",
    "Date of Test",
    "Reporting Time",
    "Gate Closure Time",
    "Test Timing",
    "Test Center",
    "Test Centre",
    "Roll No",
    "Email Address",
    "Phone Number",
    "Application Number",
]

FIELD_PATTERN = re.compile(
    r"(?<!\w)("
    + "|".join(
        re.escape(label)
        for label in sorted(FIELD_LABELS, key=len, reverse=True)
    )
    + r")\b",
    re.IGNORECASE,
)


def chunk_pdf_pages(pages, chunk_size=800, overlap=150):
    """Create field-aware chunks while preserving page numbers."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be non-negative and smaller than chunk_size."
        )

    chunks = []
    chunk_index = 0

    def add_chunk(page_number, text):
        nonlocal chunk_index

        text = text.strip()
        if text:
            chunks.append({
                "chunk_index": chunk_index,
                "page": page_number,
                "text": text,
            })
            chunk_index += 1

    for page in pages:
        page_number = page["page"]
        text = page["text"].strip()

        if not text:
            continue

        text = re.sub(r"[ \t]+", " ", text)

        # Separate recognized field labels when multiple labels
        # have been merged into a single extracted line.
        text = FIELD_PATTERN.sub(
            lambda match: "\n" + match.group(0),
            text,
        )

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        # Keep each recognized field and its value together.
        # blocks = []
        # current_block = []

        # for line in lines:
        #     is_field = bool(FIELD_PATTERN.match(line))

        #     if is_field and current_block:
        #         blocks.append("\n".join(current_block))
        #         current_block = [line]
        #     else:
        #         current_block.append(line)

        # if current_block:
        #     blocks.append("\n".join(current_block))

        
        blocks = []
        current_block = []
        i = 0

        schedule_labels = (
            "Date of Test:",
            "Reporting Time:",
            "Gate Closure Time:",
            "Test Timing:",
        )

        while i < len(lines):
            line = lines[i]

            # Keep the complete structured schedule in one block.
            if line.strip() == "Structured Test Schedule:":
                if current_block:
                    blocks.append("\n".join(current_block))
                    current_block = []

                schedule_block = [line]
                i += 1

                while (
                    i < len(lines)
                    and lines[i].startswith(schedule_labels)
                ):
                    schedule_block.append(lines[i])
                    i += 1

                blocks.append("\n".join(schedule_block))
                continue

            is_field = bool(FIELD_PATTERN.match(line))

            if is_field and current_block:
                blocks.append("\n".join(current_block))
                current_block = [line]
            else:
                current_block.append(line)

            i += 1

        if current_block:
            blocks.append("\n".join(current_block))


        # Pack blocks into chunks without splitting blocks unnecessarily.
        current_chunk = []
        current_length = 0

        for block in blocks:
            block_length = len(block)

            # Oversized blocks are split into smaller text pieces.
            if block_length > chunk_size:
                if current_chunk:
                    add_chunk(page_number, "\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                start = 0
                while start < block_length:
                    end = min(start + chunk_size, block_length)
                    add_chunk(page_number, block[start:end])

                    if end == block_length:
                        break

                    start = max(start + 1, end - overlap)

                continue

            extra = block_length + (1 if current_chunk else 0)

            if current_chunk and current_length + extra > chunk_size:
                add_chunk(page_number, "\n".join(current_chunk))
                current_chunk = []
                current_length = 0

            current_chunk.append(block)
            current_length += block_length + (
                1 if len(current_chunk) > 1 else 0
            )

        if current_chunk:
            add_chunk(page_number, "\n".join(current_chunk))

    return chunks
