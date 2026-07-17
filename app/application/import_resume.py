"""Import resume use-case: extract text → parse → validate → persist."""
import logging
from dataclasses import dataclass

from app.domain.resume import ResumeData
from app.services.document_reader import extract_text
from app.services.resume_parser import parse_resume, parse_resume_ai

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    resume: ResumeData
    raw_text: str
    source_filename: str


class ImportResumeUseCase:
    """Orchestrate the full import pipeline for a resume file."""

    def extract(self, path: str) -> str:
        """Extract plain text from PDF/DOCX/TXT. Runs synchronously; call
        from a background thread for large files."""
        return extract_text(path)

    def parse_heuristic(self, text: str, filename: str = "") -> ImportResult:
        resume = parse_resume(text)
        return ImportResult(resume=resume, raw_text=text, source_filename=filename)

    def parse_ai(self, text: str, client, filename: str = "") -> ImportResult:
        resume = parse_resume_ai(text, client)
        return ImportResult(resume=resume, raw_text=text, source_filename=filename)

    def save(self, result: ImportResult, name: str) -> int:
        """Persist the imported resume. Returns the resume ID."""
        from app.database import db
        resume_id = db.save_resume(
            name,
            result.resume.model_dump_json(),
            result.raw_text,
            source_type="import",
            source_filename=result.source_filename,
        )
        logger.info("Saved resume id=%d name=%s", resume_id, name)
        return resume_id
