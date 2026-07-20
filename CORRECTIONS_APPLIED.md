# Corrections applied

This package is based on the uploaded `Resume-optimizer-current.zip` source.

## Resume Studio workflow

- Reconnected the main top section tabs to the existing feature-rich Resume Studio.
- Removed runtime use of duplicate Contact/“Coming Soon” section pages.
- Top navigation now opens Contact, Summary, Experience, Projects, Education,
  Skills, Certifications, Languages, and Review in the same Studio instance.
- Preserved autosave, explicit version saving, duplication, AI summary/headline
  generation, live scoring, ATS insights, templates, section ordering, and custom headings.
- Kept the old section manager available behind **Manage Sections**, hidden by default.

## Review and export safety

- Added a final Review destination with a read-only preview.
- Approval is tied to an exact resume revision.
- Editing, undo, redo, AI generation, or structural changes invalidate approval.
- DOCX, PDF, and Markdown export consume a defensive copy of the approved snapshot.
- Export is blocked when the name/email is missing or Fact Guard changes remain pending.
- Export filenames are sanitized for Windows and other desktop platforms.

## Editor reliability

- Fixed section-tab overlap by replacing the scroll-area editor container atomically.
- Removed duplicate section rendering caused by both navigation code and the view-model signal loading the same section.
- Added top alignment so action controls keep their intended height instead of expanding into unused space.

- Fixed stale editor references before first navigation.
- Made existing list entries editable.
- Fixed list reorder commits so intermediate remove/insert events do not corrupt undo history.
- Ensured consecutive Contact edits use the immediately previous value as the undo baseline.
- Added draft preview updates without creating an undo command on every keystroke.

## Other fixes

- Browser fetcher now reports a missing/crashed Playwright installation deterministically
  while still performing SSRF validation immediately before navigation.
- Corrected QThread tests to use millisecond wait values and avoid leaving threads running.
- Expanded CI to feature/fix/update branches, headless Qt, migrations, and project dev extras.

## Security cleanup

- Removed the uploaded `opencode.json`, which contained plaintext provider keys.
- Added `opencode.example.json` with environment-variable placeholders.
- Added `SECURITY_NOTICE.md` with key-rotation guidance.

## Validation performed

- `python -m compileall -q app tests`
- Offscreen GUI smoke test for MainWindow → Skills → Review navigation
- `pytest -q tests/test_studio.py tests/test_studio_review.py tests/test_cv_import_regressions.py`: **118 passed**
- `pytest -q`: **876 passed**

The test suite still reports existing SQLAlchemy warnings about `datetime.utcnow()`;
these warnings are unrelated to the Studio integration and do not fail tests.

## Resume import and ATS corrections (v3)

- Improved DOCX import for combined contact lines such as
  `Kuala Lumpur,Malaysia | phone | email | LinkedIn`; location is now normalized
  to `Kuala Lumpur, Malaysia`.
- Recognizes `CORE TECHNICAL SKILLS` as the Skills section and
  `SELECTED PROJECT DELIVERY` / `SELECTED PROJECTS` as Projects.
- Improved experience-header parsing for role, company, location, and dates.
- Prevented explanatory experience notes from being imported as fake jobs.
- Education now preserves institution location, CGPA/GPA, and attendance years.
- Certifications now preserve certificate title, issuer, and year obtained.
- Added structured Studio editors for certification issuer/year, education
  location/CGPA, and project context/dates/bullets.
- ATS requirement extraction now favors known skills and explicit requirement
  sections instead of treating locations and arbitrary adjacent words as keywords.
- ATS scoring now analyzes the current structured resume; stale imported raw text
  is used only as a fallback.
- Accepting or rejecting an optimization change immediately rebuilds the
  provisional resume and recalculates the optimized ATS score.
- Cover letters can now be saved as PDF in addition to DOCX, TXT, and Markdown.
- Added a reusable text-to-PDF exporter and visually checked the rendered PDF.

## v3 validation

- Imported the supplied CV structure successfully: location, 28 skills,
  3 experience entries, 2 projects, 2 education entries, and 8 certifications.
- GUI smoke-tested Skills, Projects, Education, and Certifications using the
  supplied CV structure.
- `python -m compileall -q app tests`
- `pytest -q`: **876 passed**
