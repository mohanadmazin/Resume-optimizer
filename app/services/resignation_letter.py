"""Deterministic resignation-letter generation.

The generator intentionally avoids AI so a professional draft remains available
when Ollama is offline.  It only uses facts explicitly supplied by the user.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class ResignationLetterInput:
    employee_name: str
    company_name: str
    position: str
    letter_date: str
    last_working_day: str
    manager_name: str = ""
    manager_title: str = ""
    employee_address: str = ""
    employee_email: str = ""
    employee_phone: str = ""
    company_address: str = ""
    notice_period: str = ""
    tone: str = "formal"
    reason: str = "none"
    reason_details: str = ""
    transition_support: bool = True
    appreciation_note: str = ""


_TONE_VALUES = {"formal", "warm", "concise"}
_REASON_VALUES = {"none", "career", "further_studies", "personal", "relocation", "family_health", "retirement", "other"}
_REASON_SENTENCES = {
    "career": "I have decided to pursue another career opportunity that aligns with my long-term goals.",
    "further_studies": "I have decided to continue my studies and focus on the next stage of my academic development.",
    "personal": "I am resigning for personal reasons.",
    "relocation": "I am resigning because I will be relocating.",
    "family_health": "I am resigning due to family or health considerations.",
    "retirement": "I have decided to retire and begin the next chapter of my life.",
}


def _clean(value: str, *, limit: int = 500) -> str:
    """Normalize user text while preserving intentional line breaks."""
    value = (value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return value[:limit]


def _format_date(value: str) -> str:
    value = _clean(value, limit=40)
    if not value:
        return ""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return value
    return parsed.strftime("%d %B %Y")


def _address_lines(value: str) -> list[str]:
    return [line.strip() for line in _clean(value, limit=800).splitlines() if line.strip()]


def validate_resignation_input(data: ResignationLetterInput) -> list[str]:
    """Return user-facing validation messages for a resignation-letter request."""
    errors: list[str] = []
    required = {
        "Full name": data.employee_name,
        "Company name": data.company_name,
        "Position": data.position,
        "Letter date": data.letter_date,
        "Last working day": data.last_working_day,
    }
    for label, value in required.items():
        if not _clean(value):
            errors.append(f"{label} is required.")

    try:
        letter_day = date.fromisoformat(data.letter_date)
        last_day = date.fromisoformat(data.last_working_day)
        if last_day < letter_day:
            errors.append("Last working day cannot be earlier than the letter date.")
    except ValueError:
        errors.append("Enter valid letter and last-working-day dates.")

    if data.tone not in _TONE_VALUES:
        errors.append("Select a valid letter tone.")
    if data.reason not in _REASON_VALUES:
        errors.append("Select a valid resignation reason option.")
    if data.reason == "other" and not _clean(data.reason_details):
        errors.append("Enter custom reason wording or choose another reason option.")
    return errors


def _reason_sentence(data: ResignationLetterInput) -> str:
    reason = _clean(data.reason, limit=40)
    if reason in {"", "none"}:
        return ""
    if reason == "other":
        details = _clean(data.reason_details, limit=500)
        if not details:
            return ""
        if details[-1:] not in ".!?":
            details += "."
        return details
    return _REASON_SENTENCES.get(reason, "")


def generate_resignation_letter(data: ResignationLetterInput) -> str:
    """Create a polished resignation letter using only supplied information."""
    errors = validate_resignation_input(data)
    if errors:
        raise ValueError(" ".join(errors))

    employee_name = _clean(data.employee_name, limit=160)
    company_name = _clean(data.company_name, limit=200)
    position = _clean(data.position, limit=200)
    manager_name = _clean(data.manager_name, limit=160)
    manager_title = _clean(data.manager_title, limit=160)
    notice_period = _clean(data.notice_period, limit=100)
    appreciation_note = _clean(data.appreciation_note, limit=700)
    tone = data.tone if data.tone in _TONE_VALUES else "formal"

    lines: list[str] = [employee_name]
    lines.extend(_address_lines(data.employee_address))
    contact = " | ".join(
        value for value in [_clean(data.employee_email, limit=200), _clean(data.employee_phone, limit=80)] if value
    )
    if contact:
        lines.append(contact)
    lines.extend(["", _format_date(data.letter_date), ""])

    if manager_name:
        lines.append(manager_name)
    if manager_title:
        lines.append(manager_title)
    lines.append(company_name)
    lines.extend(_address_lines(data.company_address))
    lines.extend(["", f"Dear {manager_name or 'Sir/Madam'},", ""])
    lines.extend([f"Subject: Resignation from the Position of {position}", ""])

    last_day = _format_date(data.last_working_day)
    if tone == "warm":
        opening = (
            f"After careful consideration, I am writing to formally resign from my position as {position} "
            f"at {company_name}. My final working day will be {last_day}."
        )
    elif tone == "concise":
        opening = (
            f"Please accept this letter as formal notice of my resignation from my position as {position} "
            f"at {company_name}, with my final working day being {last_day}."
        )
    else:
        opening = (
            f"Please accept this letter as formal notice of my resignation from my position as {position} "
            f"at {company_name}, effective {last_day}."
        )
    if notice_period:
        opening += f" This provides {notice_period} notice."
    lines.append(opening)

    reason_sentence = _reason_sentence(data)
    if reason_sentence:
        lines.extend(["", reason_sentence])

    if appreciation_note:
        appreciation = appreciation_note
        if appreciation[-1:] not in ".!?":
            appreciation += "."
    elif tone == "warm":
        appreciation = (
            f"I am sincerely grateful for the opportunities, guidance, and experience I have gained during my time "
            f"with {company_name}. I have valued working with the team and appreciate the support I have received."
        )
    elif tone == "concise":
        appreciation = f"Thank you for the opportunities and experience I have gained at {company_name}."
    else:
        appreciation = (
            f"I appreciate the opportunities and professional experience I have gained during my time at "
            f"{company_name}. Thank you for the support and guidance provided throughout my employment."
        )
    lines.extend(["", appreciation])

    if data.transition_support:
        transition = (
            "During my remaining time, I will complete my outstanding responsibilities and support a structured "
            "handover to help ensure a smooth transition."
        )
        lines.extend(["", transition])

    if tone == "warm":
        closing = "I wish the company and the team continued success in the future."
    elif tone == "concise":
        closing = "I wish the company continued success."
    else:
        closing = "I wish the company continued success and appreciate your understanding."
    lines.extend(["", closing, "", "Sincerely,", "", employee_name])

    return "\n".join(lines).strip() + "\n"
