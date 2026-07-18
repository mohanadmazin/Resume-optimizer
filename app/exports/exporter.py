"""Export a structured resume to Markdown, DOCX and PDF.

DOCX and PDF are styled identically (same fonts, sizes, colors, spacing,
tab-aligned dates, bottom-ruled section headings) and both use A4 page size.
"""
import logging
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Mm

from app.schemas import ResumeData

logger = logging.getLogger(__name__)

NAVY = "1A5276"
GREY = "7E8B8D"
DARK = "1C1C1C"
FONT_NAME = "Arial"

_NAVY_RGB = RGBColor(0x1A, 0x52, 0x76)
_GREY_RGB = RGBColor(0x7E, 0x8B, 0x8D)
_DARK_RGB = RGBColor(0x1C, 0x1C, 0x1C)

_NAVY_F = (0x1A / 255, 0x52 / 255, 0x76 / 255)
_GREY_F = (0x7E / 255, 0x8B / 255, 0x8D / 255)
_DARK_F = (0x1C / 255, 0x1C / 255, 0x1C / 255)

SEP = " | "
EXP_SEP = " \u00b7 "

# A4 page geometry, shared by DOCX and PDF exporters so both render identically.
A4_WIDTH_MM = 210.0
A4_HEIGHT_MM = 297.0
A4_WIDTH_PT = 595.28
A4_HEIGHT_PT = 841.89
MARGIN_PT = 36.0


def _bottom_rule(paragraph, color: str = NAVY) -> None:
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def _blocks(resume: ResumeData) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = [("h1", resume.contact.name or "Resume")]
    if resume.headline:
        blocks.append(("meta", resume.headline))
    contact = SEP.join(
        filter(
            None,
            [
                resume.contact.location,
                resume.contact.phone,
                resume.contact.email,
                resume.contact.linkedin,
                resume.contact.website,
            ],
        )
    )
    if contact:
        blocks.append(("meta", contact))
    if resume.summary:
        blocks += [("h2", "Professional Summary"), ("p", resume.summary)]
    if resume.experience:
        blocks.append(("h2", "Professional Experience"))
        for exp in resume.experience:
            header = exp.title + (f" - {exp.company}" if exp.company else "")
            dates = " - ".join(filter(None, [exp.start_date, exp.end_date]))
            blocks.append(("h3", header + (f" ({dates})" if dates else "")))
            for bullet in exp.bullets:
                blocks.append(("li", bullet))
    if resume.projects:
        blocks.append(("h2", "Key Projects"))
        for proj in resume.projects:
            header = proj.title
            if proj.meta:
                header += f" ({proj.meta})"
            blocks.append(("h3", header))
            for bullet in proj.bullets:
                blocks.append(("li", bullet))
    if resume.skills:
        blocks += [("h2", "Technical Skills"), ("p", ", ".join(resume.skills))]
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
            parts = [p.strip() for p in cert.split("|")]
            blocks.append(("li", " \u00b7 ".join(filter(None, parts))))
    if resume.languages:
        blocks.append(("h2", "Languages"))
        for lang in resume.languages:
            blocks.append(("li", lang))
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
    logger.info("Exporting resume to Markdown: %s", path)
    Path(path).write_text(to_markdown(resume), encoding="utf-8")


def export_docx(resume: ResumeData, path: str) -> None:
    logger.info("Exporting resume to DOCX: %s", path)
    doc = Document()

    section = doc.sections[0]
    # A4 page size, matched to the PDF exporter below.
    section.page_width = Mm(A4_WIDTH_MM)
    section.page_height = Mm(A4_HEIGHT_MM)
    section.top_margin = Pt(MARGIN_PT)
    section.bottom_margin = Pt(MARGIN_PT)
    section.left_margin = Pt(MARGIN_PT)
    section.right_margin = Pt(MARGIN_PT)

    style = doc.styles["Normal"]
    rPr = style.element.get_or_add_rPr()
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), FONT_NAME)
    rFonts.set(qn("w:hAnsi"), FONT_NAME)
    rFonts.set(qn("w:cs"), FONT_NAME)
    rFonts.set(qn("w:eastAsia"), FONT_NAME)
    rPr.append(rFonts)
    style.font.size = Pt(9.5)
    style.font.color.rgb = _DARK_RGB
    style.paragraph_format.space_after = Pt(2)
    style.paragraph_format.space_before = Pt(0)

    lb = doc.styles["List Bullet"]
    lb_rPr = lb.element.get_or_add_rPr()
    lb_rFonts = OxmlElement("w:rFonts")
    lb_rFonts.set(qn("w:ascii"), FONT_NAME)
    lb_rFonts.set(qn("w:hAnsi"), FONT_NAME)
    lb_rFonts.set(qn("w:cs"), FONT_NAME)
    lb_rFonts.set(qn("w:eastAsia"), FONT_NAME)
    lb_rPr.append(lb_rFonts)
    lb.font.size = Pt(9.5)
    lb.font.color.rgb = _DARK_RGB
    lb.paragraph_format.space_after = Pt(1)
    lb.paragraph_format.space_before = Pt(0)
    lb.paragraph_format.left_indent = Pt(34)
    lb.paragraph_format.first_line_indent = Pt(-10)

    right_tab = section.page_width - section.left_margin - section.right_margin

    def add_run(paragraph, text, *, color=_DARK_RGB, size=9.5, bold=False):
        r = paragraph.add_run(text)
        r.font.name = FONT_NAME
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.bold = bold
        return r

    def section_heading(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(9)
        p.paragraph_format.space_after = Pt(3)
        add_run(p, text.upper(), color=_NAVY_RGB, size=10.5, bold=True)
        _bottom_rule(p)
        return p

    def side_by_side(paragraph, left_text, left_kw, right_text, right_kw):
        paragraph.paragraph_format.tab_stops.add_tab_stop(right_tab, WD_TAB_ALIGNMENT.RIGHT)
        add_run(paragraph, left_text, **left_kw)
        if right_text:
            add_run(paragraph, "\t" + right_text, **right_kw)

    name_p = doc.add_paragraph()
    name_p.alignment = 1
    name_p.paragraph_format.space_after = Pt(2)
    add_run(name_p, (resume.contact.name or "Resume").upper(), color=_NAVY_RGB, size=26, bold=True)

    if resume.headline:
        hp = doc.add_paragraph()
        hp.alignment = 1
        hp.paragraph_format.space_after = Pt(2)
        add_run(hp, resume.headline, color=_GREY_RGB, size=10.5)

    contact = SEP.join(
        filter(None, [
            resume.contact.location,
            resume.contact.phone,
            resume.contact.email,
            resume.contact.linkedin,
            resume.contact.website,
        ])
    )
    if contact:
        cp = doc.add_paragraph()
        cp.alignment = 1
        cp.paragraph_format.space_after = Pt(4)
        add_run(cp, contact, color=_GREY_RGB, size=9)

    rule_p = doc.add_paragraph()
    rule_p.paragraph_format.space_before = Pt(0)
    rule_p.paragraph_format.space_after = Pt(4)
    _bottom_rule(rule_p)

    if resume.summary:
        section_heading("Professional Summary")
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        add_run(p, resume.summary, size=9.5)

    if resume.experience:
        section_heading("Professional Experience")
        for exp in resume.experience:
            hp = doc.add_paragraph()
            hp.paragraph_format.space_before = Pt(6)
            hp.paragraph_format.space_after = Pt(1)
            dates = " \u2013 ".join(filter(None, [exp.start_date, exp.end_date]))
            side_by_side(
                hp,
                exp.title,
                {"color": _DARK_RGB, "size": 10.5, "bold": True},
                None,
                {},
            )
            if exp.company:
                add_run(hp, EXP_SEP + exp.company, color=_GREY_RGB, size=10)
            if dates:
                hp.paragraph_format.tab_stops.add_tab_stop(right_tab, WD_TAB_ALIGNMENT.RIGHT)
                add_run(hp, "\t" + dates, color=_GREY_RGB, size=9.5)
            for bullet in exp.bullets:
                bp = doc.add_paragraph(style="List Bullet")
                add_run(bp, bullet, size=9.5)

    if resume.projects:
        section_heading("Key Projects")
        for proj in resume.projects:
            hp = doc.add_paragraph()
            hp.paragraph_format.space_before = Pt(6)
            hp.paragraph_format.space_after = Pt(1)
            side_by_side(
                hp,
                proj.title,
                {"color": _DARK_RGB, "size": 10.5, "bold": True},
                proj.meta,
                {"color": _GREY_RGB, "size": 9.5},
            )
            for bullet in proj.bullets:
                bp = doc.add_paragraph(style="List Bullet")
                add_run(bp, bullet, size=9.5)

    if resume.skills:
        section_heading("Technical Skills")
        skill_size = 9.5
        num_cols = 6
        total_w = right_tab
        col_w = total_w // num_cols
        num_rows = (len(resume.skills) + num_cols - 1) // num_cols
        tbl = doc.add_table(rows=num_rows, cols=num_cols)
        tbl.autofit = False
        for row_idx in range(num_rows):
            for col_idx in range(num_cols):
                cell = tbl.cell(row_idx, col_idx)
                cell.width = col_w
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.space_before = Pt(1)
                flat_idx = row_idx * num_cols + col_idx
                if flat_idx < len(resume.skills):
                    add_run(p, resume.skills[flat_idx], size=skill_size)
        tbl_borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "4")
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), "CCCCCC")
            tbl_borders.append(el)
        tbl._tbl.tblPr.append(tbl_borders)

    if resume.education:
        section_heading("Education")
        for edu in resume.education:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(1)
            line = ", ".join(filter(None, [edu.degree, edu.institution]))
            side_by_side(
                p,
                line,
                {"color": _DARK_RGB, "size": 10, "bold": True},
                edu.year,
                {"color": _GREY_RGB, "size": 9},
            )

    if resume.certifications:
        section_heading("Certifications")
        for cert in resume.certifications:
            parts = [p.strip() for p in cert.split("|")]
            display = " \u00b7 ".join(filter(None, parts))
            bp = doc.add_paragraph(style="List Bullet")
            add_run(bp, display, size=9.5)

    if resume.languages:
        section_heading("Languages")
        langs_text = EXP_SEP.join(resume.languages)
        p = doc.add_paragraph()
        add_run(p, langs_text, size=9.5)

    doc.save(path)


_PDF_SIZES = {"h1": 26.0, "h2": 10.5, "h3": 10.5, "li": 9.5, "p": 9.5, "meta": 9.0}
_PDF_COLORS = {"h1": _NAVY_F, "h2": _NAVY_F, "h3": _DARK_F, "li": _DARK_F, "p": _DARK_F, "meta": _GREY_F}


def _resolve_pdf_font(name: str) -> str:
    """Return *name* if it is a valid built-in font, else fall back to helv."""
    try:
        fitz.get_text_length("x", fontname=name, fontsize=10)
        return name
    except Exception:
        logger.debug("PyMuPDF font %r unavailable, falling back to helv", name)
        return "helv"


# Resolve bold/regular PDF fonts once at module load.
_PDF_BOLD = _resolve_pdf_font("tibo")
_PDF_REGULAR = _resolve_pdf_font("tiro")


def export_pdf(resume: ResumeData, path: str) -> None:
    logger.info("Exporting resume to PDF: %s", path)
    doc = fitz.open()
    # A4 page size, matched to the DOCX exporter above.
    page = doc.new_page(width=A4_WIDTH_PT, height=A4_HEIGHT_PT)
    margin_l, margin_r = MARGIN_PT, MARGIN_PT
    margin_t = MARGIN_PT
    left, right = margin_l, page.rect.width - margin_r
    y = margin_t
    page_h = page.rect.height

    def new_page():
        nonlocal y, page
        page = doc.new_page(width=A4_WIDTH_PT, height=A4_HEIGHT_PT)
        y = margin_t

    def check_page(needed=20):
        nonlocal y
        if y + needed > page_h - 36:
            new_page()

    def draw_text(x, text, *, size=9.5, color=_DARK_F, bold=False):
        nonlocal y
        fontname = _PDF_BOLD if bold else _PDF_REGULAR
        page.insert_text((x, y), text, fontsize=size, fontname=fontname, color=color)
        y += size * 1.5

    def draw_centered(text, *, size=9.5, color=_DARK_F, bold=False):
        nonlocal y
        fontname = _PDF_BOLD if bold else _PDF_REGULAR
        w = fitz.get_text_length(text, fontname=fontname, fontsize=size)
        x = (page.rect.width - w) / 2
        page.insert_text((x, y), text, fontsize=size, fontname=fontname, color=color)
        y += size * 1.5

    def section_title(text):
        nonlocal y
        check_page(30)
        y += 4
        draw_text(left, text.upper(), size=10.5, color=_NAVY_F, bold=True)
        y += 2
        page.draw_line((left, y), (right, y), color=_NAVY_F, width=1.0)
        y += 8

    def wrap_text(text, size, bold=False):
        fontname = _PDF_BOLD if bold else _PDF_REGULAR
        max_w = right - left
        words = text.split()
        lines, current = [], ""
        for w in words:
            test = (current + " " + w).strip()
            if fitz.get_text_length(test, fontname=fontname, fontsize=size) <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines or [""]

    name = (resume.contact.name or "Resume").upper()
    draw_centered(name, size=26, color=_NAVY_F, bold=True)
    y += 2

    if resume.headline:
        draw_centered(resume.headline, size=10.5, color=_GREY_F)
        y += 1

    contact = SEP.join(filter(None, [
        resume.contact.location, resume.contact.phone,
        resume.contact.email, resume.contact.linkedin, resume.contact.website,
    ]))
    if contact:
        draw_centered(contact, size=9, color=_GREY_F)
        y += 2

    page.draw_line((left, y), (right, y), color=_NAVY_F, width=1.0)
    y += 8

    if resume.summary:
        section_title("Professional Summary")
        for line in wrap_text(resume.summary, 9.5):
            check_page(12)
            draw_text(left, line, size=9.5)

    if resume.experience:
        section_title("Professional Experience")
        for exp in resume.experience:
            check_page(24)
            dates = " \u2013 ".join(filter(None, [exp.start_date, exp.end_date]))
            title_w = fitz.get_text_length(exp.title, fontname=_PDF_BOLD, fontsize=10.5)
            draw_text(left, exp.title, size=10.5, color=_DARK_F, bold=True)
            if exp.company:
                page.insert_text(
                    (left + title_w + 4, y - 10.5 * 1.5),
                    EXP_SEP + exp.company,
                    fontsize=10, fontname=_PDF_REGULAR, color=_GREY_F,
                )
            if dates:
                dw = fitz.get_text_length(dates, fontname=_PDF_REGULAR, fontsize=9.5)
                page.insert_text((right - dw, y - 10.5 * 1.5), dates, fontsize=9.5, fontname=_PDF_REGULAR, color=_GREY_F)
            for bullet in exp.bullets:
                check_page(12)
                lines = wrap_text(bullet, 9.5)
                for i, bl in enumerate(lines):
                    draw_text(left + 12, bl, size=9.5)
                    if i == 0:
                        page.insert_text((left + 3, y - 9.5 * 1.5), "\u2022", fontsize=9.5, fontname=_PDF_REGULAR, color=_DARK_F)
            y += 4

    if resume.projects:
        section_title("Key Projects")
        for proj in resume.projects:
            check_page(24)
            dates = proj.meta or ""
            draw_text(left, proj.title, size=10.5, color=_DARK_F, bold=True)
            if dates:
                dw = fitz.get_text_length(dates, fontname=_PDF_REGULAR, fontsize=9.5)
                page.insert_text((right - dw, y - 10.5 * 1.5), dates, fontsize=9.5, fontname=_PDF_REGULAR, color=_GREY_F)
            for bullet in proj.bullets:
                check_page(12)
                lines = wrap_text(bullet, 9.5)
                for i, bl in enumerate(lines):
                    draw_text(left + 12, bl, size=9.5)
                    if i == 0:
                        page.insert_text((left + 3, y - 9.5 * 1.5), "\u2022", fontsize=9.5, fontname=_PDF_REGULAR, color=_DARK_F)
            y += 4

    if resume.skills:
        section_title("Technical Skills")
        skill_font = _PDF_REGULAR
        skill_size = 9.5
        page_w = right - left
        num_cols = 6
        col_w = page_w / num_cols
        num_rows = (len(resume.skills) + num_cols - 1) // num_cols
        for row_idx in range(num_rows):
            max_lines = 1
            for col_idx in range(num_cols):
                flat_idx = row_idx * num_cols + col_idx
                if flat_idx < len(resume.skills):
                    sk = resume.skills[flat_idx]
                    text_w = fitz.get_text_length(sk, fontname=skill_font, fontsize=skill_size)
                    max_text_w = col_w - 8
                    if text_w > max_text_w:
                        words = sk.split()
                        line_count = 1
                        current = ""
                        for w in words:
                            test = (current + " " + w).strip()
                            if fitz.get_text_length(test, fontname=skill_font, fontsize=skill_size) <= max_text_w:
                                current = test
                            else:
                                line_count += 1
                                current = w
                        max_lines = max(max_lines, line_count)
            row_h = skill_size * 1.5 * max_lines + 6
            check_page(row_h + 4)
            for col_idx in range(num_cols):
                flat_idx = row_idx * num_cols + col_idx
                x0 = left + col_idx * col_w
                rect = fitz.Rect(x0, y, x0 + col_w, y + row_h)
                page.draw_rect(rect, fill=None, color=(0.8, 0.8, 0.8), width=0.5)
                if flat_idx < len(resume.skills):
                    sk = resume.skills[flat_idx]
                    text_w = fitz.get_text_length(sk, fontname=skill_font, fontsize=skill_size)
                    max_text_w = col_w - 8
                    if text_w <= max_text_w:
                        page.insert_text(
                            (x0 + 4, y + skill_size + 4),
                            sk, fontsize=skill_size, fontname=skill_font, color=_DARK_F,
                        )
                    else:
                        words = sk.split()
                        line1, line2 = "", ""
                        for w in words:
                            test = (line1 + " " + w).strip()
                            if fitz.get_text_length(test, fontname=skill_font, fontsize=skill_size) <= max_text_w:
                                line1 = test
                            else:
                                line2 = (line2 + " " + w).strip()
                        page.insert_text((x0 + 4, y + skill_size + 4), line1, fontsize=skill_size, fontname=skill_font, color=_DARK_F)
                        if line2:
                            page.insert_text((x0 + 4, y + skill_size * 2.5 + 4), line2, fontsize=skill_size, fontname=skill_font, color=_DARK_F)
            y += row_h
        y += skill_size * 2

    if resume.education:
        section_title("Education")
        for edu in resume.education:
            check_page(16)
            line = ", ".join(filter(None, [edu.degree, edu.institution]))
            draw_text(left, line, size=10, color=_DARK_F, bold=True)
            if edu.year:
                dw = fitz.get_text_length(edu.year, fontname=_PDF_REGULAR, fontsize=9)
                page.insert_text((right - dw, y - 10 * 1.5), edu.year, fontsize=9, fontname=_PDF_REGULAR, color=_GREY_F)
            y += 4

    if resume.certifications:
        section_title("Certifications")
        for cert in resume.certifications:
            check_page(12)
            parts = [p.strip() for p in cert.split("|")]
            display = " \u00b7 ".join(filter(None, parts))
            page.insert_text((left + 3, y), "\u2022", fontsize=9.5, fontname=_PDF_REGULAR, color=_DARK_F)
            draw_text(left + 12, display, size=9.5)

    if resume.languages:
        section_title("Languages")
        langs = EXP_SEP.join(resume.languages)
        draw_text(left, langs, size=9.5)

    doc.save(path)
    doc.close()


def export_text_docx(text: str, path: str) -> None:
    """Save plain text (e.g. a cover letter) as a DOCX file, A4 size."""
    logger.info("Exporting text to DOCX: %s", path)
    doc = Document()
    section = doc.sections[0]
    section.page_width = Mm(A4_WIDTH_MM)
    section.page_height = Mm(A4_HEIGHT_MM)
    for paragraph in text.split("\n"):
        doc.add_paragraph(paragraph)
    doc.save(path)