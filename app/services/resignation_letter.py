"""Deterministic resignation-letter generation in English and Bahasa Melayu.

No AI is required. The generator uses only user-supplied facts and deliberately
avoids legal conclusions; users should verify notice obligations in their
employment contract and applicable workplace policies.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re


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
    language: str = "en"
    resignation_type: str = "standard"
    include_leave_balance: bool = False
    include_property_return: bool = False


_TONE_VALUES = {"formal", "warm", "concise"}
_LANGUAGE_VALUES = {"en", "ms"}
_TYPE_VALUES = {"standard", "immediate", "early_release"}
_REASON_VALUES = {"none", "career", "further_studies", "personal", "relocation", "family_health", "retirement", "other"}
_REASON_SENTENCES = {
    "en": {
        "career": "I have decided to pursue another career opportunity that aligns with my long-term goals.",
        "further_studies": "I have decided to continue my studies and focus on the next stage of my academic development.",
        "personal": "I am resigning for personal reasons.",
        "relocation": "I am resigning because I will be relocating.",
        "family_health": "I am resigning due to family or health considerations.",
        "retirement": "I have decided to retire and begin the next chapter of my life.",
    },
    "ms": {
        "career": "Saya telah membuat keputusan untuk meneruskan peluang kerjaya lain yang selaras dengan matlamat jangka panjang saya.",
        "further_studies": "Saya telah membuat keputusan untuk melanjutkan pengajian dan memberi tumpuan kepada perkembangan akademik saya.",
        "personal": "Saya meletakkan jawatan atas sebab peribadi.",
        "relocation": "Saya meletakkan jawatan kerana akan berpindah ke lokasi lain.",
        "family_health": "Saya meletakkan jawatan atas faktor keluarga atau kesihatan.",
        "retirement": "Saya telah membuat keputusan untuk bersara dan memulakan fasa baharu dalam kehidupan.",
    },
}


def _clean(value: str, *, limit: int = 500) -> str:
    return (value or "").replace("\r\n", "\n").replace("\r", "\n").strip()[:limit]


def _format_date(value: str, language: str = "en") -> str:
    value = _clean(value, limit=40)
    if not value:
        return ""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return value
    if language == "ms":
        months = ["Januari", "Februari", "Mac", "April", "Mei", "Jun", "Julai", "Ogos", "September", "Oktober", "November", "Disember"]
        return f"{parsed.day} {months[parsed.month - 1]} {parsed.year}"
    return parsed.strftime("%d %B %Y")


def _address_lines(value: str) -> list[str]:
    return [line.strip() for line in _clean(value, limit=800).splitlines() if line.strip()]


def expected_notice_days(notice_period: str) -> int | None:
    """Best-effort conversion used only for a user warning, never legal advice."""
    text = _clean(notice_period, limit=100).casefold()
    match = re.search(r"(\d+)\s*(day|week|month|hari|minggu|bulan)", text)
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    if unit in {"day", "hari"}:
        return amount
    if unit in {"week", "minggu"}:
        return amount * 7
    return amount * 30


def notice_period_warning(data: ResignationLetterInput) -> str:
    try:
        actual = (date.fromisoformat(data.last_working_day) - date.fromisoformat(data.letter_date)).days
    except ValueError:
        return ""
    expected = expected_notice_days(data.notice_period)
    if expected is None or data.resignation_type == "immediate":
        return ""
    if actual < expected:
        return (
            f"The selected dates provide approximately {actual} day(s), which is shorter than the entered "
            f"notice period of approximately {expected} day(s). Verify your employment contract."
        )
    return ""


def validate_resignation_input(data: ResignationLetterInput) -> list[str]:
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
    if data.language not in _LANGUAGE_VALUES:
        errors.append("Select a valid language.")
    if data.resignation_type not in _TYPE_VALUES:
        errors.append("Select a valid resignation type.")
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
        if details and details[-1:] not in ".!?":
            details += "."
        return details
    return _REASON_SENTENCES[data.language].get(reason, "")


def _header_lines(data: ResignationLetterInput, language: str) -> list[str]:
    lines = [_clean(data.employee_name, limit=160)]
    lines.extend(_address_lines(data.employee_address))
    contact = " | ".join(v for v in [_clean(data.employee_email, limit=200), _clean(data.employee_phone, limit=80)] if v)
    if contact:
        lines.append(contact)
    lines.extend(["", _format_date(data.letter_date, language), ""])
    if _clean(data.manager_name, limit=160):
        lines.append(_clean(data.manager_name, limit=160))
    if _clean(data.manager_title, limit=160):
        lines.append(_clean(data.manager_title, limit=160))
    lines.append(_clean(data.company_name, limit=200))
    lines.extend(_address_lines(data.company_address))
    return lines


def _generate_ms(data: ResignationLetterInput) -> str:
    name = _clean(data.employee_name, limit=160)
    company = _clean(data.company_name, limit=200)
    position = _clean(data.position, limit=200)
    manager = _clean(data.manager_name, limit=160)
    last_day = _format_date(data.last_working_day, "ms")
    lines = _header_lines(data, "ms")
    lines.extend(["", f"Tuan/Puan {manager}" if manager else "Tuan/Puan,", "", f"PERKARA: NOTIS PELETAKAN JAWATAN SEBAGAI {position.upper()}", ""])
    if data.resignation_type == "immediate":
        opening = f"Dengan hormatnya, saya ingin memaklumkan peletakan jawatan saya sebagai {position} di {company}, berkuat kuasa pada {last_day}."
    else:
        opening = f"Dengan hormatnya, saya ingin mengemukakan notis peletakan jawatan saya sebagai {position} di {company}. Hari terakhir saya bekerja ialah pada {last_day}."
    if data.notice_period:
        opening += f" Notis ini diberikan berdasarkan tempoh {data.notice_period}."
    lines.append(opening)
    if data.resignation_type == "early_release":
        lines.extend(["", "Saya dengan rendah hati memohon pertimbangan pihak syarikat untuk pelepasan lebih awal daripada tempoh notis, tertakluk kepada kelulusan dan syarat syarikat."])
    reason = _reason_sentence(data)
    if reason:
        lines.extend(["", reason])
    appreciation = _clean(data.appreciation_note, limit=700) or f"Saya merakamkan setinggi-tinggi penghargaan atas peluang, pengalaman dan bimbingan yang telah diberikan sepanjang saya berkhidmat di {company}."
    if appreciation[-1:] not in ".!?":
        appreciation += "."
    lines.extend(["", appreciation])
    if data.transition_support:
        lines.extend(["", "Sepanjang baki tempoh perkhidmatan, saya akan menyelesaikan tugasan yang masih tertunggak dan membantu proses serahan tugas supaya peralihan dapat berjalan dengan lancar."])
    if data.include_leave_balance:
        lines.extend(["", "Saya juga memohon pengesahan berhubung baki cuti dan penyelesaian akhir yang berkaitan mengikut polisi syarikat."])
    if data.include_property_return:
        lines.extend(["", "Saya akan memulangkan semua harta, dokumen dan akses milik syarikat sebelum hari terakhir perkhidmatan saya."])
    lines.extend(["", "Saya mendoakan agar syarikat dan seluruh pasukan terus maju dan berjaya.", "", "Sekian, terima kasih.", "", "Yang benar,", "", name])
    return "\n".join(lines).strip() + "\n"


def _generate_en(data: ResignationLetterInput) -> str:
    employee_name = _clean(data.employee_name, limit=160)
    company_name = _clean(data.company_name, limit=200)
    position = _clean(data.position, limit=200)
    manager_name = _clean(data.manager_name, limit=160)
    notice_period = _clean(data.notice_period, limit=100)
    appreciation_note = _clean(data.appreciation_note, limit=700)
    tone = data.tone if data.tone in _TONE_VALUES else "formal"
    lines = _header_lines(data, "en")
    lines.extend(["", f"Dear {manager_name or 'Sir/Madam'},", "", f"Subject: Resignation from the Position of {position}", ""])
    last_day = _format_date(data.last_working_day, "en")
    if data.resignation_type == "immediate":
        opening = f"Please accept this letter as notice of my resignation from my position as {position} at {company_name}, effective {last_day}."
    elif tone == "warm":
        opening = f"After careful consideration, I am writing to formally resign from my position as {position} at {company_name}. My final working day will be {last_day}."
    elif tone == "concise":
        opening = f"Please accept this letter as formal notice of my resignation from my position as {position} at {company_name}, with my final working day being {last_day}."
    else:
        opening = f"Please accept this letter as formal notice of my resignation from my position as {position} at {company_name}, effective {last_day}."
    if notice_period:
        opening += f" This provides {notice_period} notice."
    lines.append(opening)
    if data.resignation_type == "early_release":
        lines.extend(["", "I respectfully request consideration for an early release from the full notice period, subject to the company's approval and applicable terms."])
    reason_sentence = _reason_sentence(data)
    if reason_sentence:
        lines.extend(["", reason_sentence])
    if appreciation_note:
        appreciation = appreciation_note + ("" if appreciation_note[-1:] in ".!?" else ".")
    elif tone == "warm":
        appreciation = f"I am sincerely grateful for the opportunities, guidance, and experience I have gained during my time with {company_name}. I have valued working with the team and appreciate the support I have received."
    elif tone == "concise":
        appreciation = f"Thank you for the opportunities and experience I have gained at {company_name}."
    else:
        appreciation = f"I appreciate the opportunities and professional experience I have gained during my time at {company_name}. Thank you for the support and guidance provided throughout my employment."
    lines.extend(["", appreciation])
    if data.transition_support:
        lines.extend(["", "During my remaining time, I will complete my outstanding responsibilities and support a structured handover to help ensure a smooth transition."])
    if data.include_leave_balance:
        lines.extend(["", "Please also confirm the treatment of my remaining leave balance and any final employment-related settlement in accordance with company policy."])
    if data.include_property_return:
        lines.extend(["", "I will return all company property, documents, and access credentials before my final working day."])
    if tone == "warm":
        closing = "I wish the company and the team continued success in the future."
    elif tone == "concise":
        closing = "I wish the company continued success."
    else:
        closing = "I wish the company continued success and appreciate your understanding."
    lines.extend(["", closing, "", "Sincerely,", "", employee_name])
    return "\n".join(lines).strip() + "\n"


def generate_resignation_letter(data: ResignationLetterInput) -> str:
    errors = validate_resignation_input(data)
    if errors:
        raise ValueError(" ".join(errors))
    return _generate_ms(data) if data.language == "ms" else _generate_en(data)
