"""Extract plain text from PDF, DOCX and text files."""
import logging
import re
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document

logger = logging.getLogger(__name__)

_SECTION_HEADERS = {
    "summary", "professional summary",
    "skills", "technical skills",
    "experience", "professional experience", "work experience", "employment",
    "education", "academic background",
    "certifications", "certificates",
    "projects", "key projects",
    "languages",
}

# Pattern to add space before dates concatenated with letters (e.g., "Kuala LumpurOct 2019" → "Kuala Lumpur Oct 2019")
_MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
_DATE_PREFIX_RE = re.compile(r"([a-zA-Z])(" + _MONTHS + r")")


def extract_text(path: str) -> str:
    suffix = Path(path).suffix.lower()
    logger.info("Reading document: %s (type=%s)", path, suffix)
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    if suffix in (".txt", ".md"):
        return Path(path).read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {suffix}. Use PDF, DOCX or TXT.")


def _read_pdf(path: str) -> str:
    with fitz.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


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
