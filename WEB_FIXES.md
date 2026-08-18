# ResumeAI Web Upgrade

## Run

```bash
python -m pip install -e ".[web]"
python web_main.py
```

Open `http://127.0.0.1:8080`.

The application binds to localhost by default. FastAPI interactive documentation and the OpenAPI endpoint are disabled in the production app.

## Unified workflow

The main web application and Resume Builder now use the same SQLite resume records.

1. Build or import a resume.
2. Review and edit the parsed sections in `/builder/`.
3. Save a target job with company, location, source, salary, employment type, posting date, and status.
4. Run explainable ATS analysis.
5. Generate fact-checked optimization suggestions.
6. Accept only accurate changes, recalculate the score, and export.
7. Generate editable career documents or track the application.

## Implemented corrections and improvements

### Data and persistence

- Persistent server-side web sessions stored in SQLite; browser cookies contain only a random session ID.
- Resume Builder autosaves to the same resume record used by ATS and optimization.
- Resume version history with safe restore controls.
- Rich target-job metadata retained when jobs are reselected.
- Complete ATS results and optimization review choices persisted.
- Editable cover-letter and resignation-letter drafts stored with reopenable history.
- Alembic migration `0007` adds the new columns and persistence tables.
- Legacy databases are inferred by actual schema generation instead of being incorrectly stamped at the latest migration.

### Resume and targeting

- Resume import validation for PDF, DOCX, DOC, and TXT up to 15 MB.
- Structured parsed-resume review through the shared builder.
- Saved resume/job use and delete actions with complete downstream-state invalidation.
- ATS category breakdown, keyword evidence, findings, and recommendations.
- Optimization side-by-side review, supported/flagged filters, selective acceptance, score recalculation, and version creation.
- Optimized resume exports: DOCX, PDF, Markdown, TXT, and JSON.

### Career documents

- Cover-letter edits are saved and every export uses the current textarea content.
- Cover-letter exports: TXT, DOCX, and PDF.
- Resignation letters in English or Bahasa Melayu.
- Standard, immediate, and early-release resignation options.
- Notice-period date warning, leave-balance wording, property-return wording, transition support, and saved history.
- Resignation exports: TXT, DOCX, and PDF.

### Application tracker

- Track the currently selected resume and target job.
- Statuses: draft, wishlist, applied, interview, offer, rejected, and withdrawn.
- Editable notes, applied date, vacancy source link, and safe deletion.
- Dashboard pipeline summary.

### Interface and operations

- One ResumeAI brand and design system across the main web app and builder.
- Grouped navigation, responsive mobile sidebar, SVG icons, alerts, confirmations, and toast feedback.
- Recommended-next-action dashboard, active application summary, ATS history, document history, and pipeline activity.
- Blocking-operation overlay with staged progress messages and browser-side cancellation.
- Ollama connection test uses the URL and model currently entered in the form.
- Ollama URLs are limited to localhost or private-network HTTP(S) endpoints.
- Security headers, local-only default binding, restricted external job URLs, and disabled API schema routes.

## Main pages

- Dashboard: `/`
- Resume Builder: `/builder/`
- Resume Library and versions: `/upload`
- Target Jobs: `/jobs`
- ATS Analysis: `/ats`
- Optimization: `/optimize`
- Application Tracker: `/applications`
- Cover Letters: `/cover-letter`
- Resignation Letters: `/resignation-letter`
- Settings: `/settings`

## Verification

- Python compilation and JavaScript syntax checks passed.
- All Jinja templates compiled.
- Fresh-install and legacy-database migrations passed.
- FastAPI integration tests cover shared builder storage, ATS workflow, rich job metadata, application tracking, version restoration, resignation editing/exports, disabled OpenAPI access, and current-form Ollama testing.
- Non-desktop regression suite: 685 tests passed in this runtime.
- Desktop-only test modules could not be collected here because `PySide6` and `circuitbreaker` are not installed in the execution environment. They remain declared project dependencies.

## Real-world DOCX validation (22 July 2026)

The application was validated with a multi-page network-engineering DOCX and an Accenture Deployment Network Engineer vacancy. This pass corrected two-line employment metadata, long project/certification headings, project date association, pipe-separated education fields, scheduled certification dates, and punctuation-normalized keyword evidence. See `REAL_DATA_TEST_REPORT.md`.
