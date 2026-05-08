import re


def split_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    separator: str = "\n",
) -> list[str]:
    """
    Split text into overlapping chunks, respecting sentence boundaries.
    """
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    if len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    sections = text.split(separator)
    current_chunk = ""

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(current_chunk) + len(section) + 1 <= chunk_size:
            if current_chunk:
                current_chunk += "\n" + section
            else:
                current_chunk = section
        else:
            if current_chunk:
                chunks.append(current_chunk)

            if len(section) > chunk_size:
                sub_chunks = _split_long_section(section, chunk_size, chunk_overlap)
                current_chunk = sub_chunks[-1] if sub_chunks else ""
                chunks.extend(sub_chunks[:-1] if len(sub_chunks) > 1 else [])
            else:
                if chunk_overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-chunk_overlap:]
                    current_chunk = overlap_text + "\n" + section
                else:
                    current_chunk = section

    if current_chunk:
        chunks.append(current_chunk)

    return [c for c in chunks if c.strip()]


def _split_long_section(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """Split a section that's too long by sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= chunk_size:
            if current:
                current += " " + sentence
            else:
                current = sentence
        else:
            if current:
                chunks.append(current)
            if chunk_overlap > 0 and current:
                overlap = current[-chunk_overlap:]
                current = overlap + " " + sentence
            else:
                current = sentence

    if current:
        chunks.append(current)

    return chunks


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    """Extract text content from PDF file bytes."""
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"PDF extraction failed: {str(e)}")
