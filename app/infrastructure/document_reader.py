"""Extract plain text from PDF, DOCX and text files."""
import logging
import re
import zipfile
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document

logger = logging.getLogger(__name__)

MAX_DOCUMENT_BYTES = 15 * 1024 * 1024
MAX_PDF_PAGES = 60
MAX_DOCX_EXPANDED_BYTES = 75 * 1024 * 1024
MAX_DOCX_COMPRESSION_RATIO = 100

_SECTION_HEADERS = {
    "summary", "professional summary",
    "skills", "technical skills", "core technical skills",
    "experience", "professional experience", "work experience", "employment",
    "education", "academic background",
    "certifications", "certificates",
    "projects", "key projects", "selected projects", "selected project delivery",
    "languages",
}

# Pattern to add space before dates concatenated with letters (e.g., "Kuala LumpurOct 2019" → "Kuala Lumpur Oct 2019")
_MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
_DATE_PREFIX_RE = re.compile(r"([a-zA-Z])(" + _MONTHS + r")")


def extract_text(path: str) -> str:
    suffix = Path(path).suffix.lower()
    logger.info("Reading document: %s (type=%s)", path, suffix)
    _validate_input_size(Path(path))
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        _validate_docx_archive(Path(path))
        return _read_docx(path)
    if suffix in (".txt", ".md"):
        return Path(path).read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {suffix}. Use PDF, DOCX or TXT.")


def _validate_input_size(path: Path) -> None:
    if path.stat().st_size > MAX_DOCUMENT_BYTES:
        raise ValueError(
            "Document exceeds the 15 MB safety limit."
        )


def _validate_docx_archive(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        compressed = 0
        expanded = 0

        for entry in archive.infolist():
            compressed += max(entry.compress_size, 1)
            expanded += entry.file_size

            if expanded > MAX_DOCX_EXPANDED_BYTES:
                raise ValueError(
                    "DOCX expands beyond the safety limit."
                )

        if expanded / max(compressed, 1) > (
            MAX_DOCX_COMPRESSION_RATIO
        ):
            raise ValueError(
                "Suspicious DOCX compression ratio."
            )


def _read_pdf(path: str) -> str:
    with fitz.open(path) as doc:
        if doc.page_count > MAX_PDF_PAGES:
            raise ValueError(
                f"PDF exceeds {MAX_PDF_PAGES} pages."
            )
        parts: list[str] = []
        for page in doc:
            blocks = page.get_text("blocks")
            # Sort by vertical position (top→bottom), then horizontal (left→right)
            blocks.sort(key=lambda b: (round(b[1], 1), b[0]))
            for block in blocks:
                # block[4] is the text content; skip image-only blocks
                if len(block) > 4 and block[4].strip():
                    parts.append(block[4].strip())
        return "\n".join(parts)


def _is_section_header_row(first_cell: str) -> bool:
    clean = re.sub(r"[^a-z ]", "", first_cell.lower()).strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean in _SECTION_HEADERS


def _read_docx(path: str) -> str:
    doc = Document(path)
    parts: list[str] = []
    for child in doc.element.body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "p":
            from docx.text.paragraph import Paragraph
            para = Paragraph(child, doc)
            text = para.text
            if not text:
                parts.append("")
                continue
            is_list = para.style and "list" in (para.style.name or "").lower()
            # Fix concatenated dates (e.g., "Kuala LumpurOct 2019")
            text = _DATE_PREFIX_RE.sub(r"\1 \2", text)
            # Split on newlines to handle paragraphs with mixed content
            for subline in text.split("\n"):
                subline = subline.strip()
                if subline:
                    if is_list and not subline.startswith("\u2022"):
                        subline = "\u2022 " + subline
                    parts.append(subline)
                else:
                    parts.append("")
        elif tag == "tbl":
            from docx.table import Table
            table = Table(child, doc)
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if cells and _is_section_header_row(cells[0]):
                    parts.append(cells[0])
                else:
                    parts.append(" | ".join(cells))
    return "\n".join(parts)
