"""Export a structured resume to Markdown, DOCX and PDF."""
import textwrap
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from app.schemas import ResumeData

# Brand palette / type, matched to the reference CV template.
NAVY = "1A5276"
GREY = "7E8B8D"
DARK = "1C1C1C"
FONT_NAME = "Times New Roman"

_NAVY_RGB = RGBColor(0x1A, 0x52, 0x76)
_GREY_RGB = RGBColor(0x7E, 0x8B, 0x8D)
_DARK_RGB = RGBColor(0x1C, 0x1C, 0x1C)

_NAVY_F = (0x1A / 255, 0x52 / 255, 0x76 / 255)
_GREY_F = (0x7E / 255, 0x8B / 255, 0x8D / 255)
_DARK_F = (0x1C / 255, 0x1C / 255, 0x1C / 255)


def _top_rule(paragraph, color: str = NAVY) -> None:
    """Add a thin top border above a paragraph (mimics the rule line
    the reference CV draws above each section heading)."""
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    top = OxmlElement("w:top")
    top.set(qn("w:val"), "single")
    top.set(qn("w:sz"), "12")
    top.set(qn("w:space"), "4")
    top.set(qn("w:color"), color)
    pBdr.append(top)
    pPr.append(pBdr)


def _blocks(resume: ResumeData) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = [("h1", resume.contact.name or "Resume")]
    contact = " | ".join(
        filter(
            None,
            [
                resume.contact.email,
                resume.contact.phone,
                resume.contact.location,
                resume.contact.linkedin,
                resume.contact.website,
            ],
        )
    )
    if contact:
        blocks.append(("meta", contact))
    if resume.summary:
        blocks += [("h2", "Summary"), ("p", resume.summary)]
    if resume.skills:
        blocks += [("h2", "Skills"), ("p", ", ".join(resume.skills))]
    if resume.experience:
        blocks.append(("h2", "Experience"))
        for exp in resume.experience:
            header = exp.title + (f" - {exp.company}" if exp.company else "")
            dates = " - ".join(filter(None, [exp.start_date, exp.end_date]))
            blocks.append(("h3", header + (f" ({dates})" if dates else "")))
            for bullet in exp.bullets:
                blocks.append(("li", bullet))
    if resume.education:
        blocks.append(("h2", "Education"))
        for edu in resume.education:
            line = ", ".join(filter(None, [edu.degree, edu.institution]))
            if edu.year:
                line += f" ({edu.year})"
            blocks.append(("p", line))
    if resume.certifications:
        blocks.append(("h2", "Certifications"))
        for cert in resume.certifications:
            blocks.append(("li", cert))
    return blocks


def to_markdown(resume: ResumeData) -> str:
    out: list[str] = []
    for kind, text in _blocks(resume):
        if kind == "h1":
            out.append(f"# {text}")
        elif kind == "h2":
            out.append(f"\n## {text}\n")
        elif kind == "h3":
            out.append(f"### {text}")
        elif kind == "li":
            out.append(f"- {text}")
        else:
            out.append(text)
    return "\n".join(out).strip() + "\n"


def export_markdown(resume: ResumeData, path: str) -> None:
    Path(path).write_text(to_markdown(resume), encoding="utf-8")


def export_docx(resume: ResumeData, path: str) -> None:
    doc = Document()
    doc.styles["Normal"].font.name = FONT_NAME
    doc.styles["Normal"].font.size = Pt(10)
    section = doc.sections[0]
    right_tab = section.page_width - section.left_margin - section.right_margin

    def run(paragraph, text, *, color=_DARK_RGB, size=10, bold=False, italic=False):
        r = paragraph.add_run(text)
        r.font.name = FONT_NAME
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.bold = bold
        r.font.italic = italic
        return r

    def heading(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        _top_rule(p)
        run(p, text.upper(), color=_NAVY_RGB, size=11.5, bold=True)
        return p

    def side_by_side(paragraph, left_text, left_kw, right_text, right_kw):
        paragraph.paragraph_format.tab_stops.add_tab_stop(right_tab, WD_TAB_ALIGNMENT.RIGHT)
        run(paragraph, left_text, **left_kw)
        if right_text:
            run(paragraph, "\t" + right_text, **right_kw)

    # Header block: name, contact line, centered.
    name_p = doc.add_paragraph()
    name_p.alignment = 1  # center
    run(name_p, (resume.contact.name or "Resume").upper(), color=_NAVY_RGB, size=22, bold=True)

    contact = " | ".join(
        filter(
            None,
            [
                resume.contact.email,
                resume.contact.phone,
                resume.contact.location,
                resume.contact.linkedin,
                resume.contact.website,
            ],
        )
    )
    if contact:
        contact_p = doc.add_paragraph()
        contact_p.alignment = 1
        contact_p.paragraph_format.space_after = Pt(6)
        run(contact_p, contact, color=_GREY_RGB, size=9)

    if resume.summary:
        heading("Professional Summary")
        p = doc.add_paragraph()
        run(p, resume.summary, size=10)

    if resume.skills:
        heading("Skills")
        p = doc.add_paragraph()
        run(p, ", ".join(resume.skills), size=10)

    if resume.experience:
        heading("Professional Experience")
        for exp in resume.experience:
            header_p = doc.add_paragraph()
            header_p.paragraph_format.space_before = Pt(8)
            dates = " - ".join(filter(None, [exp.start_date, exp.end_date]))
            side_by_side(
                header_p,
                exp.title + (f" \u00b7 {exp.company}" if exp.company else ""),
                {"color": _DARK_RGB, "size": 11, "bold": True},
                dates,
                {"color": _GREY_RGB, "size": 9.5, "italic": True},
            )
            for bullet in exp.bullets:
                bp = doc.add_paragraph(style="List Bullet")
                bp.paragraph_format.space_after = Pt(2)
                run(bp, bullet, size=9.5)

    if resume.education:
        heading("Education")
        for edu in resume.education:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            line = ", ".join(filter(None, [edu.degree, edu.institution]))
            side_by_side(
                p,
                line,
                {"color": _DARK_RGB, "size": 10.5, "bold": True},
                edu.year,
                {"color": _GREY_RGB, "size": 9.5, "italic": True},
            )

    if resume.certifications:
        heading("Certifications")
        for cert in resume.certifications:
            bp = doc.add_paragraph(style="List Bullet")
            bp.paragraph_format.space_after = Pt(2)
            run(bp, cert, size=9.5)

    doc.save(path)


_PDF_SIZES = {"h1": 20.0, "h2": 13.0, "h3": 11.5, "li": 10.0, "p": 10.0, "meta": 9.0}
_PDF_COLORS = {"h1": _NAVY_F, "h2": _NAVY_F, "h3": _DARK_F, "li": _DARK_F, "p": _DARK_F, "meta": _GREY_F}
_PDF_FONTS = {"h1": "tibo", "h2": "tibo", "h3": "tibo", "li": "tiro", "p": "tiro", "meta": "tiro"}


def export_pdf(resume: ResumeData, path: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    left, right = 54.0, page.rect.width - 54.0
    y = 60.0
    for kind, text in _blocks(resume):
        size = _PDF_SIZES[kind]
        prefix = "\u2022  " if kind == "li" else ""
        centered = kind in ("h1", "meta")
        if kind == "h2":
            if y > page.rect.height - 60:
                page = doc.new_page()
                y = 60.0
            y += 10
            page.draw_line((left, y), (right, y), color=_NAVY_F, width=1.1)
            y += 12
        for line in textwrap.wrap(prefix + text, width=int(760 / size)) or [""]:
            if y > page.rect.height - 60:
                page = doc.new_page()
                y = 60.0
            x = left
            if centered:
                width = fitz.get_text_length(line, fontname=_PDF_FONTS[kind], fontsize=size)
                x = (page.rect.width - width) / 2
            page.insert_text(
                (x, y),
                line,
                fontsize=size,
                fontname=_PDF_FONTS[kind],
                color=_PDF_COLORS[kind],
            )
            y += size * 1.5
        if kind in ("p", "meta", "h2"):
            y += 4
    doc.save(path)
    doc.close()


def export_text_docx(text: str, path: str) -> None:
    """Save plain text (e.g. a cover letter) as a DOCX file."""
    doc = Document()
    for paragraph in text.split("\n"):
        doc.add_paragraph(paragraph)
    doc.save(path)
