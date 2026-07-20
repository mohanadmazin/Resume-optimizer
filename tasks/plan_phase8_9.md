# Implementation Plan: Phase 8 + Phase 9

## Overview
Phase 8 adds design control, templates, and export polish to make the app production-ready.
Phase 9 adds the AI content engine — bullet writer integration, real-time content checker, and 23-factor scoring.

## Key Findings
- PDF/DOCX export already exist (PyMuPDF + python-docx) but are hardcoded to Arial/Navy
- Bullet writer service already exists (`bullet_writer.py`)
- ATS scoring exists but needs 23-factor enhancement
- No content quality checking (grammar, weak words, passive voice)

---

## Phase 8: Export & Design Control

### Task 8.1: Configurable Export Theme
**Description:** Extract hardcoded colors/fonts into an `ExportTheme` dataclass. Add font family, accent color, and font size parameters to `export_pdf()` and `export_docx()`.

**Acceptance criteria:**
- [ ] `ExportTheme` dataclass with font_family, accent_color, font_size, name
- [ ] Default theme matches current behavior (Arial, Navy)
- [ ] `export_pdf()` and `export_docx()` accept optional `theme` parameter
- [ ] Existing tests still pass

**Files:** `app/exports/exporter.py`

### Task 8.2: Built-in Templates
**Description:** Create 3 named templates: Classic (current), Modern (Calibri, darker accent), Compact (smaller margins, 10pt).

**Acceptance criteria:**
- [ ] `TEMPLATES` dict with "Classic", "Modern", "Compact" themes
- [ ] `get_template(name)` function returns an `ExportTheme`
- [ ] Each template produces visually distinct output

**Files:** `app/exports/exporter.py`

### Task 8.3: Export UI in Studio
**Description:** Add Export button to Studio page with format dropdown (PDF/DOCX/Markdown) and template picker.

**Acceptance criteria:**
- [ ] Export button in Studio bottom bar
- [ ] Clicking opens format + template selection
- [ ] Export saves to user-chosen path via file dialog
- [ ] Status feedback on success/failure

**Files:** `app/ui/pages/studio.py`

### Task 8.4: Page Count Auto-Resizer
**Description:** After generating PDF, check page count. If content overflows, reduce font size by 0.5pt and regenerate. Repeat until fits target (default 1 page, max 2).

**Acceptance criteria:**
- [ ] `export_pdf()` accepts `target_pages` parameter (default 1)
- [ ] Auto-reduces font size if content overflows
- [ ] Minimum font size floor (7.5pt) to prevent unreadable output

**Files:** `app/exports/exporter.py`

---

## Phase 9: AI Content Engine

### Task 9.1: Real-Time Content Checker
**Description:** Build a deterministic (no AI) content quality checker that flags weak words, passive voice, short bullets, and missing metrics on every edit.

**Acceptance criteria:**
- [ ] `check_content(resume) -> ContentCheckResult` function
- [ ] Detects: weak words (responsible for, assisted, helped), passive voice, bullets < 40 chars, bullets without numbers, summary < 50 chars
- [ ] Returns list of issues with severity, path, message
- [ ] Integrates with Studio insights panel

**Files:** `app/services/content_checker.py`, `app/domain/content_check.py`

### Task 9.2: 23-Factor Resume Score
**Description:** Enhance ATS scoring to a 23-factor system like rezi.ai. Each factor is weighted and contributes to an overall score out of 100.

**Acceptance criteria:**
- [ ] `calculate_resume_score(resume, job_text) -> ResumeScore` with 23 factors
- [ ] Factors: contact completeness, summary length, summary keywords, skills count, skills match, experience count, bullet count, bullet length, bullet metrics, date consistency, education present, certifications, keywords matched, keyword density, action verbs, quantified achievements, no typos (basic), section order, page count, font consistency, URL present, phone present, email present
- [ ] Overall score 0-100 with per-factor breakdown
- [ ] Score displayed in Studio insights panel

**Files:** `app/services/resume_scorer.py`, `app/domain/scoring.py`

### Task 9.3: Enhanced AI Summary v2
**Description:** Improve summary generator to produce longer, more detailed summaries with metrics and role-specific language.

**Acceptance criteria: [x] Already exists
- [ ] Update prompt to generate 3-4 sentence summaries
- [ ] Include metrics and achievements in summary
- [ ] Role-specific language (different for engineers vs managers)

**Files:** `app/ai/prompts.py`, `app/services/summary_generator.py`

### Task 9.4: AI Skills Explorer
**Description:** Given a job description, suggest 5-10 additional skills the candidate should add to their resume.

**Acceptance criteria:**
- [ ] `explore_skills(resume, job_text) -> list[SkillSuggestion]` function
- [ ] Each suggestion has: skill name, reason, importance (1-5)
- [ ] Deduplicates against existing skills
- [ ] Integrates with Studio insights panel suggestions

**Files:** `app/services/skill_explorer.py`, `app/domain/skill_gap.py`

---

## Checkpoint: Phase 8 Complete
- [ ] All 802 tests pass + new tests
- [ ] ruff clean
- [ ] Can export PDF/DOCX with template selection from Studio

## Checkpoint: Phase 9 Complete
- [ ] All tests pass
- [ ] Content checker runs on every edit
- [ ] 23-factor score displayed in insights
- [ ] Skills explorer suggests relevant skills
