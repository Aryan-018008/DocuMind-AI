import re  #RegEx - Regular Expression

def chunk_pdf_pages(pages, chunk_size=800, overlap=150):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be non-negative and smaller than chunk_size."
        )

    chunks = []
    chunk_index = 0

    for page in pages:
        page_number = page["page"]
        text = page["text"].strip()

        if not text:
            continue

        # Normalize spacing without removing line boundaries.
        text = re.sub(r"[ \t]+", " ", text)
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        # Keep complete lines together whenever possible.
        groups = []
        current_group = []

        for line in lines:
            candidate = "\n".join(current_group + [line])

            if current_group and len(candidate) > chunk_size:
                groups.append("\n".join(current_group))
                current_group = [line]
            else:
                current_group.append(line)

        if current_group:
            groups.append("\n".join(current_group))

        # Create chunks with a small overlap of complete lines.
        start = 0

        while start < len(groups):
            chunk_lines = []
            length = 0
            end = start

            while end < len(groups):
                line = groups[end]
                extra = len(line) + (1 if chunk_lines else 0)

                if chunk_lines and length + extra > chunk_size:
                    break

                chunk_lines.append(line)
                length += extra
                end += 1

            chunk_text = "\n".join(chunk_lines).strip()

            if chunk_text:
                chunks.append({
                    "chunk_index": chunk_index,
                    "page": page_number,
                    "text": chunk_text
                })
                chunk_index += 1

            if end >= len(groups):
                break

            # Retain complete lines as overlap, not partial words.
            overlap_length = 0
            next_start = end

            while next_start > start:
                previous_line = groups[next_start - 1]
                if overlap_length + len(previous_line) > overlap:
                    break

                overlap_length += len(previous_line)
                next_start -= 1

            start = next_start if next_start > start else end

    return chunks
