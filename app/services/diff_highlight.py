"""Builds HTML for the optimized-resume preview with AI-added/changed
text highlighted in red. Diffing is word-level for prose fields
(summary) and bullet-level (with a word-level pass inside changed
bullets) for experience bullets. Fields the optimizer never touches
(contact, skills, education, certifications) are rendered plain.
"""
from difflib import SequenceMatcher
from html import escape

from app.schemas import ResumeData

HIGHLIGHT = '<span style="color:#ff5c5c;">{}</span>'


def _diff_words_html(old: str, new: str) -> str:
    old_words = old.split(" ")
    new_words = new.split(" ")
    matcher = SequenceMatcher(None, old_words, new_words)
    parts: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        chunk = " ".join(new_words[j1:j2])
        if not chunk:
            continue
        parts.append(escape(chunk) if tag == "equal" else HIGHLIGHT.format(escape(chunk)))
    return " ".join(parts)


def _diff_bullets_html(old_bullets: list[str], new_bullets: list[str]) -> list[str]:
    matcher = SequenceMatcher(None, old_bullets, new_bullets)
    result: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result.extend(escape(b) for b in new_bullets[j1:j2])
        elif tag == "delete":
            continue  # bullet removed entirely; nothing to show in the "after" text
        else:  # replace / insert -> everything in this span is new/changed
            old_slice = old_bullets[i1:i2]
            new_slice = new_bullets[j1:j2]
            for k, new_b in enumerate(new_slice):
                if k < len(old_slice):
                    result.append(_diff_words_html(old_slice[k], new_b))
                else:
                    result.append(HIGHLIGHT.format(escape(new_b)))
    return result


def resume_diff_html(original: ResumeData, optimized: ResumeData) -> str:
    """Render `optimized` as HTML, with any text added or changed
    relative to `original` wrapped in a red <span>."""
    lines: list[str] = []

    name = escape(optimized.contact.name or "Resume")
    lines.append(
        f"<p style='font-size:18px; font-weight:normal;'>{name}</p>"
    )

    contact = " | ".join(
        filter(
            None,
            [
                optimized.contact.email,
                optimized.contact.phone,
                optimized.contact.location,
                optimized.contact.linkedin,
                optimized.contact.website,
            ],
        )
    )
    if contact:
        lines.append(f"<p style='color:#9aa0a6;'>{escape(contact)}</p>")

    if optimized.headline:
        headline_html = _diff_words_html(original.headline, optimized.headline)
        lines.append(f"<p style='color:#9aa0a6;'>{headline_html}</p>")

    if optimized.summary:
        lines.append(
            "<p style='font-size:15px; font-weight:normal;'>Summary</p>"
        )
        summary_html = _diff_words_html(original.summary, optimized.summary)
        lines.append(f"<p>{summary_html}</p>")

    if optimized.skills:
        lines.append(
            "<p style='font-size:15px; font-weight:normal;'>Skills</p>"
        )
        lines.append(f"<p>{escape(', '.join(optimized.skills))}</p>")

    if optimized.experience:
        lines.append(
            "<p style='font-size:15px; font-weight:normal;'>Experience</p>"
        )
        for orig_exp, opt_exp in zip(original.experience, optimized.experience):
            header = opt_exp.title + (f" - {opt_exp.company}" if opt_exp.company else "")
            dates = " - ".join(filter(None, [opt_exp.start_date, opt_exp.end_date]))
            if dates:
                header += f" ({dates})"
            lines.append(
                f"<p style='font-weight:normal;'>{escape(header)}</p>"
            )
            lines.append("<ul>")
            for bullet_html in _diff_bullets_html(orig_exp.bullets, opt_exp.bullets):
                lines.append(f"<li>{bullet_html}</li>")
            lines.append("</ul>")

    if optimized.education:
        lines.append("<h2>Education</h2>")
        for edu in optimized.education:
            line = ", ".join(filter(None, [
                edu.degree,
                edu.institution,
                getattr(edu, "location", ""),
            ]))
            cgpa = getattr(edu, "cgpa", "")
            if cgpa:
                line += f" | CGPA {cgpa}"
            if edu.year:
                line += f" ({edu.year})"
            lines.append(f"<p>{escape(line)}</p>")

    if optimized.certifications:
        lines.append("<h2>Certifications</h2>")
        lines.append("<ul>")
        for cert in optimized.certifications:
            lines.append(f"<li>{escape(cert)}</li>")
        lines.append("</ul>")

    return f"""
    <html>
    <head>
    <style>
    body {{
        font-family: Segoe UI;
        font-size: 14px;
        font-weight: normal;
    }}

    p, li {{
        font-weight: normal;
    }}

    span {{
        font-weight: normal;
    }}
    </style>
    </head>
    <body>

    {"".join(lines)}

    </body>
    </html>
    """
