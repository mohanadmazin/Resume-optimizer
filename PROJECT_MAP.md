# Resume Optimizer — PROJECT_MAP.md

## 1. PRODUCT_OVERVIEW

Resume Optimizer is a privacy-first desktop application for managing resumes, analyzing job descriptions, improving ATS compatibility, generating application materials, and tracking job applications.

The application uses deterministic analysis for measurable ATS scoring and local Ollama models for language generation and semantic evaluation.

### Core Principles

* **Local-first:** Resume and job-search data remain on the user's device.
* **Explainable scoring:** ATS scores must show how they were calculated.
* **Human-controlled AI:** AI suggestions are reviewable and never overwrite source data automatically.
* **Versioned documents:** Original and optimized resumes remain recoverable.
* **Structured data:** AI outputs are validated before entering the database.
* **Graceful degradation:** Non-AI features continue working when Ollama is unavailable.
* **Source transparency:** Salary, skill-demand, and job-market claims identify their data source.
* **Modular monolith:** Maintain a simple desktop deployment while separating domains cleanly.

---

## 2. FEATURE_STATUS

Legend:

* ✅ Implemented
* 🚧 Planned
* 🔭 Future
* ⚠️ Requires validation or redesign

| Feature                             | Status |
| ----------------------------------- | ------ |
| Resume PDF/DOCX/TXT import          | ✅      |
| Resume parsing (heuristic + AI)     | ✅      |
| Job-description import (paste/file) | ✅      |
| Job-description URL fetch           | ✅      |
| Deterministic ATS analysis          | ✅      |
| ATS score before/after comparison   | ✅      |
| Keyword heatmap visualization       | ✅      |
| AI resume optimization              | ✅      |
| Resume comparison and diff          | ✅      |
| Cover-letter generation             | ✅      |
| Skill-gap analysis                  | ✅      |
| Salary estimation                   | ⚠️     |
| DOCX/PDF/Markdown export            | ✅      |
| One-click optimization pipeline     | ✅      |
| Ollama connection status indicator  | ✅      |
| Loading overlays for async ops      | ✅      |
| Model pre-warming on startup        | ✅      |
| Resume library and version history  | 🚧     |
| Job library                         | 🚧     |
| Application tracker                 | 🚧     |
| Batch job comparison                | 🚧     |
| Interview preparation               | 🚧     |
| Achievement bullet generator        | 🚧     |
| Resume quality checker              | 🚧     |
| Keyword placement analysis          | 🚧     |
| Career analytics dashboard          | 🚧     |
| Backup and restore                  | 🚧     |
| Prompt and model diagnostics        | 🚧     |
| Optional encrypted sensitive fields | 🔭     |
| Optional job-board integrations     | 🔭     |

---

## 3. TECH_STACK

### Core Runtime

| Package     | Version Policy         | Purpose                               |
| ----------- | ---------------------- | ------------------------------------- |
| Python      | 3.12+                  | Application runtime                   |
| PySide6     | Compatible 6.x release | Qt desktop GUI                        |
| SQLAlchemy  | Compatible 2.x release | ORM and SQLite access                 |
| Pydantic    | Compatible 2.x release | Validation and structured AI output   |
| PyMuPDF     | Compatible 1.x release | PDF extraction, rendering, and export |
| python-docx | Compatible 1.x release | DOCX import and export                |
| requests    | Compatible 2.x release | Ollama HTTP communication             |
| beautifulsoup4 | Compatible 4.x release | HTML parsing for URL job fetch     |
| lxml           | Compatible 5.x release | Fast HTML parser backend            |
| Alembic     | Compatible 1.x release | Database schema migrations            |
| pytest      | Compatible 9.x release | Automated testing                     |

### Recommended Additions

| Package      | Purpose                                   | Status |
| ------------ | ----------------------------------------- | ------ |
| platformdirs | Cross-platform application directories    | 🚧     |
| keyring      | Secure storage for future API credentials | 🔭     |
| RapidFuzz    | Skill and keyword normalization           | 🚧     |
| Jinja2       | Maintainable prompt and export templates  | 🚧     |
| dateparser   | Flexible employment-date parsing          | 🚧     |
| tenacity     | Retry policies for local AI requests      | 🚧     |
| pytest-qt    | PySide6 UI testing                        | 🚧     |
| pytest-cov   | Coverage reporting                        | 🚧     |
| ruff         | Linting and formatting checks             | 🚧     |
| mypy         | Static type checking                      | 🚧     |
| pre-commit   | Automated repository checks               | 🚧     |

### Packaging

| Tool                         | Purpose                                               |
| ---------------------------- | ----------------------------------------------------- |
| `pyproject.toml`             | Project metadata, dependencies, tooling configuration |
| PyInstaller                  | Standalone application builds                         |
| GitHub Actions or equivalent | Automated tests and release builds                    |
| Alembic                      | Database upgrade compatibility                        |

Versions should be pinned in a lock file for reproducible builds rather than documented as exact versions in this map.

---

## 4. SYSTEM_CONTEXT

```text
┌────────────────────────────────────────────────────────────┐
│                         USER                               │
└──────────────┬─────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────────┐
│                    PySide6 Desktop UI                      │
│                                                            │
│ Dashboard │ Resumes │ Jobs │ Analysis │ Optimize           │
│ Letters   │ Interview │ Applications │ Analytics │ Settings│
└──────────────┬─────────────────────────────────────────────┘
               │ Commands / Queries
               ▼
┌────────────────────────────────────────────────────────────┐
│                  Application Services                      │
│                                                            │
│ ResumeService       JobService        AnalysisService      │
│ OptimizationService LetterService     InterviewService     │
│ ApplicationService  ExportService     BackupService        │
└──────────┬───────────────────┬─────────────────────┬───────┘
           │                   │                     │
           ▼                   ▼                     ▼
┌──────────────────┐ ┌───────────────────┐ ┌─────────────────┐
│ Domain Engines   │ │ AI Infrastructure │ │ Persistence     │
│                  │ │                   │ │                 │
│ ATS scoring      │ │ Ollama client     │ │ SQLAlchemy      │
│ Keyword matching │ │ Prompt registry   │ │ Repositories    │
│ Quality checks   │ │ Output validation │ │ SQLite          │
│ Diff engine      │ │ Retry/fallback    │ │ Migrations      │
└──────────────────┘ └───────────────────┘ └─────────────────┘
           │                   │                     │
           └───────────────────┴─────────────────────┘
                               │
                               ▼
                    DOCX / PDF / Markdown / JSON
```

---

## 5. PRIMARY_SYSTEM_FLOWS

### 5.1 Resume Import

```text
Select File
    → Validate file type and size
    → Extract text
    → Detect extraction quality
    → Parse structured sections
    → Validate ResumeData
    → Show correction screen
    → Save Resume
    → Create ResumeVersion
    → Index normalized skills and keywords
```

### 5.2 Job Description Import

```text
Paste or Upload Job Description
    → Extract and normalize text
    → Detect role, company, location, and seniority
    → Extract required and preferred skills
    → Separate responsibilities and qualifications
    → User review
    → Save Job
```

### 5.3 ATS Analysis

```text
Select Resume Version + Job
    → Normalize text and skills
    → Extract weighted job requirements
    → Calculate deterministic sub-scores
    → Detect keyword placement and evidence
    → Identify formatting risks
    → Generate explainable recommendations
    → Save AnalysisRun
```

### 5.4 Resume Optimization

```text
Select Resume Version + Job
    → Load ATS findings
    → Select optimization intensity
    → Build constrained AI request
    → Generate structured proposed changes
    → Validate facts against source resume
    → Flag unsupported claims
    → Show side-by-side diff
    → Accept or reject individual changes
    → Save new ResumeVersion
```

### 5.5 Cover Letter

```text
Select Resume Version + Job
    → Select tone and length
    → Choose achievements to emphasize
    → Generate draft
    → Run unsupported-claim check
    → Edit and save LetterVersion
    → Export or copy
```

### 5.6 Skill-Gap Analysis

```text
Select Resume + Target Job or Role Profile
    → Extract candidate skills
    → Extract target skills
    → Normalize aliases
    → Match exact and related skills
    → Rank gaps by importance
    → Build learning recommendations
    → Save SkillGapRun
```

The result must distinguish between:

* Skills directly evidenced in the resume
* Skills inferred by AI
* Skills required by the selected job
* Skills obtained from an external or user-provided market dataset

### 5.7 Salary Guidance

```text
Role + Location + Experience
    → Select salary data source
    → Normalize currency and period
    → Calculate range
    → Show confidence and data date
    → Explain influencing factors
    → Save SalaryEstimateRun
```

An Ollama model alone cannot provide reliable current salary data. AI may explain supplied data, but salary ranges must come from one of the following:

* User-entered market data
* Bundled salary dataset
* Cached external dataset
* Optional salary-provider integration

Every estimate must display source, date, confidence, and limitations.

### 5.8 Application Tracking

```text
Select Job
    → Attach Resume Version
    → Attach Cover Letter Version
    → Set application stage
    → Record dates, contacts, notes, and follow-ups
    → Add interview events
    → Update outcome
    → Feed dashboard analytics
```

---

## 6. ARCHITECTURE

```text
Pattern:      Modular monolith with layered boundaries
UI:           PySide6 QMainWindow + route registry + QStackedWidget
State:        Session-scoped AppState containing IDs, not full domain objects
Domain:       Pure scoring, matching, validation, and transformation logic
Services:     Application use cases and transaction coordination
Persistence:  Repository interfaces backed by SQLAlchemy
Database:     SQLite with Alembic migrations
AI:           Ollama through a provider-neutral AI gateway
Exports:      Renderer-based DOCX, PDF, Markdown, JSON, and plain text
Config:       One typed settings service
Logging:      Rotating application log with privacy-safe context
```

### Dependency Direction

```text
UI
 ↓
Application Services
 ↓
Domain Models and Domain Engines
 ↑
Infrastructure Implementations
```

Rules:

1. UI modules do not issue SQL queries directly.
2. UI modules do not call Ollama directly.
3. Domain engines do not import PySide6, SQLAlchemy, or requests.
4. Services operate on validated schemas and repository interfaces.
5. AI-generated values are validated before persistence.
6. Exporters consume canonical resume schemas, not UI widgets.
7. Database ORM models remain separate from Pydantic domain schemas.
8. Long-running work executes outside the UI thread.
9. Every saved AI result records the model and prompt version used.
10. Original imported content is immutable.

---

## 7. MODULE_RESPONSIBILITIES

| Module          | Responsibility                                                 |
| --------------- | -------------------------------------------------------------- |
| `app/core/`     | Paths, settings (Pydantic), app constants                      |
| `app/domain/`   | Pydantic schemas (resume, salary, skill gap, pipeline)         |
| `app/ai/`       | Ollama HTTP client, prompt templates, JSON validation          |
| `app/database/` | ORM models, engine, session, repositories, legacy CRUD facade  |
| `app/services/` | ATS engine, optimizer, cover letter, parser, security, HTML extraction, metadata, job fetcher, etc. |
| `app/config/`   | Legacy config compatibility shim (delegates to `app/core/`)    |
| `app/ui/`       | Main window, state, workers, theme, components, pages          |
| `app/exports/`  | DOCX/PDF/Markdown export (via `app/services/exporter.py`)      |
| `tests/`        | Unit tests for ATS, parser, exporter, schemas                  |

---

## 8. ACTUAL_FILE_MAP

```text
resume-optimizer-main/
├── main.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── PROJECT_MAP.md
├── .gitignore
├── alembic.ini
│
├── migrations/
│   ├── env.py
│   └── versions/
│       ├── 0001_initial_schema.py
│       ├── 0002_add_resume_tracking.py
│       └── 0003_add_cascade_delete.py
│
├── app/
│   ├── __init__.py
│   ├── schemas.py                     # Backward-compatible re-exports from app/domain/
│   ├── validators.py                  # ResumeData validation helpers
│   ├── logging_config.py              # Rotating file + console logging
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── settings.py                # Pydantic AppSettings (AI, Appearance)
│   │   └── paths.py                   # DB_PATH, CONFIG_PATH, LOG_DIR, etc.
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── resume.py                  # ContactInfo, ExperienceItem, EducationItem, ProjectItem, ResumeData
│   │   ├── skill_gap.py               # SkillGapItem, SkillGapResult
│   │   ├── salary.py                  # SalaryEstimate (Decimal fields)
│   │   ├── analysis.py                # ATSResult domain model
│   │   ├── fact_guard.py              # ChangeType, ProposedChange, FactGuardResult
│   │   └── pipeline.py                # PipelineResult dataclass
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── ollama_client.py           # OllamaClient: generate(), generate_json(), generate_structured(), pre_warm()
│   │   └── prompts.py                 # All prompt templates (471 lines)
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── engine.py                  # SQLAlchemy SQLite engine
│   │   ├── session.py                 # SessionLocal, get_session() context manager
│   │   ├── models.py                  # Resume, JobDescription, Analysis, Optimization ORM
│   │   ├── db.py                      # Backward-compatible CRUD facade
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── base.py                # Abstract base repository
│   │       ├── resume_repository.py   # Resume CRUD + SHA-256 content hash
│   │       ├── job_repository.py      # JobDescription CRUD
│   │       └── analysis_repository.py # Analysis CRUD with JOIN queries
│   │
│   ├── config/                        # Legacy compatibility layer
│   │   ├── __init__.py                # Re-exports from app.core.*
│   │   └── config_manager.py          # Old JSON config (superseded)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ats_engine.py              # ATS keyword analysis + scoring
│   │   ├── optimizer.py               # AI resume optimization (safe-only apply)
│   │   ├── cover_letter.py            # AI cover letter generation + fact checking
│   │   ├── resume_parser.py           # Heuristic + AI resume parsing
│   │   ├── fact_guard.py              # Deterministic fact validation (SequenceMatcher)
│   │   ├── document_reader.py         # PDF/DOCX/TXT text extraction
│   │   ├── job_fetcher.py             # URL fetch orchestrator with SSRF protection
│   │   ├── security.py               # SSRF protection, DNS resolution, port blocking
│   │   ├── html_extractor.py          # HTML text extraction, noise filtering
│   │   ├── metadata.py               # Title parsing, JSON-LD, metadata extraction
│   │   ├── salary_estimator.py        # AI salary estimation
│   │   ├── skill_gap.py               # AI skill gap analysis
│   │   ├── diff_highlight.py          # HTML diff between original and optimized
│   │   └── exporter.py                # DOCX/PDF/Markdown export
│   │
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py             # QMainWindow with sidebar nav + stack
│       ├── state.py                   # AppState (resume, job, ats, pipeline, etc.)
│   ├── workers.py                 # Worker + PipelineWorker (QThread) + cancel support
│   ├── theme.py                   # DARK_STYLESHEET + LIGHT_STYLESHEET
│       │
│       ├── components/
│       │   ├── __init__.py
│       │   ├── ollama_status.py       # OllamaCheckerThread + OllamaStatusLabel
│       │   └── loading_overlay.py     # LoadingOverlay + LoadingOverlayManager
│       │
│       └── pages/
│           ├── __init__.py
│           ├── dashboard.py           # One-click pipeline, score cards, recent table
│           ├── resume_upload.py       # PDF/DOCX import + parse + save
│           ├── job_description.py     # Paste/upload/URL fetch + save
│           ├── ats_analysis.py        # Score cards, keyword heatmap, suggestions
│           ├── optimization.py        # Before/after ATS comparison, diff preview
│           ├── cover_letter.py        # AI cover letter generation
│           ├── skill_gap.py           # Skill gap analysis
│           ├── salary_estimate.py     # Salary estimation
│           └── settings.py            # Ollama URL, model, temperature, theme
│
└── tests/
    ├── __init__.py
    ├── test_ats_engine.py             # 15 tests (ATS scoring, skill matching, suggestions)
    ├── test_cover_letter.py           # 11 tests (fact checking, generation, warnings)
    ├── test_exporter.py               # 2 tests
    ├── test_fact_guard.py             # 22 tests (normalization, entities, skills, changes)
    ├── test_job_fetcher.py            # 51 tests (security, HTML extraction, metadata, fetcher)
    ├── test_migrations.py             # 23 tests (schema, backup, restore, cascade delete)
    ├── test_optimizer.py              # 7 tests (safe-only apply, accepted changes)
    ├── test_parser.py                 # 4 tests
    ├── test_parser_fallback.py        # 8 tests (OllamaError fallback, edge cases)
    ├── test_settings.py               # 29 tests (atomic write, backup, recovery, concurrency)
    └── test_skill_gap_salary.py       # 5 tests
```
├── main.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── PROJECT_MAP.md
├── .gitignore
├── alembic.ini
│
├── migrations/
│   ├── env.py
│   └── versions/
│       ├── 0001_initial_schema.py
│       ├── 0002_add_resume_tracking.py
│       └── 0003_add_cascade_delete.py
│
├── app/
│   ├── __init__.py
│   ├── schemas.py                     # Backward-compatible re-exports from app/domain/
│   ├── validators.py                  # ResumeData validation helpers
│   ├── logging_config.py              # Rotating file + console logging
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── settings.py                # Pydantic AppSettings + SettingsService singleton
│   │   └── paths.py                   # DB_PATH, CONFIG_PATH, LOG_DIR, etc.
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── resume.py                  # ContactInfo, ExperienceItem, EducationItem, ProjectItem, ResumeData
│   │   ├── skill_gap.py               # SkillGapItem, SkillGapResult
│   │   ├── salary.py                  # SalaryEstimate (Decimal fields)
│   │   ├── analysis.py                # ATSResult domain model
│   │   ├── fact_guard.py              # ChangeType, ProposedChange, FactGuardResult
│   │   ├── job_requirements.py        # JobRequirements domain model
│   │   └── pipeline.py                # PipelineResult dataclass
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── ollama_client.py           # OllamaClient: generate(), generate_json(), generate_structured(), pre_warm()
│   │   └── prompts.py                 # All prompt templates (471 lines)
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── engine.py                  # SQLAlchemy SQLite engine
│   │   ├── session.py                 # SessionLocal, get_session() context manager
│   │   ├── models.py                  # Resume, JobDescription, Analysis, Optimization ORM
│   │   ├── db.py                      # Backward-compatible CRUD facade
│   │   ├── migrate.py                 # Alembic migration helper
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── base.py                # Abstract base repository
│   │       ├── resume_repository.py   # Resume CRUD + SHA-256 content hash
│   │       ├── job_repository.py      # JobDescription CRUD
│   │       └── analysis_repository.py # Analysis CRUD with JOIN queries
│   │
│   ├── config/                        # Legacy compatibility layer
│   │   ├── __init__.py                # Re-exports from app.core.*
│   │   └── config_manager.py          # Old JSON config (superseded)
│   │
│   ├── application/                   # Use-case layer
│   │   ├── __init__.py
│   │   ├── import_resume.py           # ImportResumeUseCase
│   │   ├── analyze_resume.py          # AnalyzeResumeUseCase
│   │   └── optimize_resume.py         # OptimizeResumeUseCase + RunPipelineUseCase
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ats_engine.py              # ATS keyword analysis + scoring
│   │   ├── optimizer.py               # AI resume optimization (safe-only apply)
│   │   ├── cover_letter.py            # AI cover letter generation + fact checking
│   │   ├── resume_parser.py           # Heuristic + AI resume parsing
│   │   ├── fact_guard.py              # Deterministic fact validation (SequenceMatcher)
│   │   ├── document_reader.py         # PDF/DOCX/TXT text extraction
│   │   ├── job_fetcher.py             # URL fetch orchestrator with SSRF protection
│   │   ├── security.py               # SSRF protection, DNS resolution, port blocking
│   │   ├── html_extractor.py          # HTML text extraction, noise filtering
│   │   ├── metadata.py               # Title parsing, JSON-LD, metadata extraction
│   │   ├── salary_estimator.py        # AI salary estimation
│   │   ├── skill_gap.py               # AI skill gap analysis
│   │   ├── diff_highlight.py          # HTML diff between original and optimized
│   │   └── exporter.py                # DOCX/PDF/Markdown export
│   │
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py             # QMainWindow with sidebar nav + stack
│       ├── state.py                   # AppState (resume, job, ats, pipeline, etc.)
│       ├── workers.py                 # Worker + PipelineWorker (QThread) + cancel support
│       ├── theme.py                   # DARK_STYLESHEET + LIGHT_STYLESHEET
│       │
│       ├── components/
│       │   ├── __init__.py
│       │   ├── ollama_status.py       # OllamaCheckerThread + OllamaStatusLabel
│       │   └── loading_overlay.py     # LoadingOverlay + LoadingOverlayManager
│       │
│       └── pages/
│           ├── __init__.py
│           ├── dashboard.py           # One-click pipeline, score cards, recent table
│           ├── resume_upload.py       # PDF/DOCX import + parse + save
│           ├── job_description.py     # Paste/upload/URL fetch + save
│           ├── ats_analysis.py        # Score cards, keyword heatmap, suggestions
│           ├── optimization.py        # Before/after ATS comparison, diff preview, Accept/Reject
│           ├── cover_letter.py        # AI cover letter generation + fact-check warnings
│           ├── skill_gap.py           # Skill gap analysis with disclaimer
│           ├── salary_estimate.py     # Salary estimation with disclaimer
│           └── settings.py            # Ollama URL, model, temperature, theme
│
└── tests/
    ├── __init__.py
    ├── test_ats_engine.py             # 15 tests (scoring, skill matching, suggestions)
    ├── test_cover_letter.py           # 11 tests (fact checking, generation, warnings)
    ├── test_exporter.py               #  2 tests
    ├── test_fact_guard.py             # 22 tests (normalization, entities, skills, changes)
    ├── test_job_fetcher.py            # 51 tests (security, HTML extraction, metadata, fetcher)
    ├── test_migrations.py             # 23 tests (schema, backup, restore, cascade delete)
    ├── test_optimizer.py              #  7 tests (safe-only apply, accepted changes)
    ├── test_parser.py                 #  4 tests
    ├── test_parser_fallback.py        #  8 tests (OllamaError fallback, edge cases)
    ├── test_settings.py               # 29 tests (atomic write, backup, recovery, concurrency)
    └── test_skill_gap_salary.py       #  5 tests
    # Total: 200 tests across 11 test files
```

---

## 9. CURRENT_STRUCTURE_CLEANUP

The following inconsistencies should be fixed before adding more features.

### 9.1 Duplicate ATS Engine — RESOLVED (2026-07-16)

`app/ats_engine.py` deleted. Only `app/services/ats_engine.py` remains.

### 9.2 Duplicate Configuration Sources — RESOLVED (2026-07-16)

Settings consolidated into `app/core/settings.py` with typed `AppSettings`.

### 9.3 ATS Page Filename Mismatch — RESOLVED (2026-07-16)

Only `ats_analysis.py` exists. No mismatch.

### 9.4 Oversized Shared Schema File — RESOLVED (2026-07-16)

Split into domain modules: `resume.py`, `salary.py`, `skill_gap.py`, `fact_guard.py`, `pipeline.py`, `analysis.py`, `job_requirements.py`.

### 9.5 Database Helper Concentration — RESOLVED (2026-07-16)

Split into `engine.py`, `session.py`, and `repositories/`.

### 9.6 Config Stored in Source Directory

User-modifiable configuration should not be written inside the packaged application directory.

Recommended runtime paths:

```text
<user-data-dir>/
├── resume_optimizer.db
├── config.json
├── logs/
├── backups/
├── exports/
└── cache/
```

Use `platformdirs` to resolve operating-system-specific locations.

---

## 10. DOMAIN_MODELS

All persistent entities should use UUID strings and timestamps.

Common metadata:

```python
id: str
created_at: datetime
updated_at: datetime
```

### 10.1 ContactInfo

```python
ContactInfo:
  full_name: str
  email: str
  phone: str
  location: str
  linkedin_url: str
  portfolio_url: str
  github_url: str
  website_url: str
```

### 10.2 ResumeData

```python
ResumeData:
  contact: ContactInfo
  headline: str
  summary: str
  skills: list[SkillEntry]
  experience: list[ExperienceItem]
  education: list[EducationItem]
  certifications: list[CertificationItem]
  projects: list[ProjectItem]
  languages: list[LanguageItem]
  publications: list[PublicationItem]
  awards: list[AwardItem]
  volunteer_experience: list[ExperienceItem]
  custom_sections: list[CustomSection]
```

Do not store `raw_text` directly in the reusable domain model. Store source extraction data in the resume version or import record.

### 10.3 Resume

```python
Resume:
  id: str
  display_name: str
  target_role: str
  active_version_id: str
  archived: bool
  created_at: datetime
  updated_at: datetime
```

### 10.4 ResumeVersion

```python
ResumeVersion:
  id: str
  resume_id: str
  version_number: int
  parent_version_id: str | None
  label: str
  source_type: str
  source_filename: str | None
  source_hash: str | None
  raw_text: str
  data: ResumeData
  change_summary: str
  created_by: str
  ai_run_id: str | None
  is_locked: bool
  created_at: datetime
```

`created_by` values:

```text
import
user
ai
migration
```

### 10.5 JobDescription

```python
JobDescription:
  id: str
  title: str
  company: str
  location: str
  work_mode: str
  employment_type: str
  seniority: str
  source_url: str
  source_name: str
  description_text: str
  responsibilities: list[str]
  required_skills: list[JobSkill]
  preferred_skills: list[JobSkill]
  education_requirements: list[str]
  experience_requirements: list[str]
  compensation_text: str
  status: str
  posted_at: datetime | None
  imported_at: datetime
```

### 10.6 JobSkill

```python
JobSkill:
  name: str
  normalized_name: str
  importance: str
  requirement_type: str
  frequency: int
  context: list[str]
```

### 10.7 ATSResult

```python
ATSResult:
  overall_score: float
  keyword_score: float
  experience_score: float
  skills_score: float
  education_score: float
  formatting_score: float
  impact_score: float
  readability_score: float

  matched_keywords: list[KeywordMatch]
  missing_keywords: list[KeywordGap]
  weak_keywords: list[KeywordGap]
  section_findings: list[SectionFinding]
  formatting_risks: list[FormattingFinding]
  recommendations: list[Recommendation]
  score_explanation: list[ScoreComponent]
```

### 10.8 AnalysisRun

```python
AnalysisRun:
  id: str
  resume_version_id: str
  job_id: str
  ats_engine_version: str
  result: ATSResult
  input_hash: str
  created_at: datetime
```

The input hash allows identical analyses to be cached.

### 10.9 SkillGapResult

```python
SkillGapResult:
  target_role: str
  source_type: str
  source_label: str
  source_date: datetime | None
  required_skills: list[SkillRequirement]
  evidenced_skills: list[SkillEvidence]
  inferred_skills: list[SkillEvidence]
  matched: list[SkillMatch]
  missing: list[SkillGapItem]
  transferable_skills: list[SkillMatch]
  learning_plan: list[LearningStep]
  summary: str
  confidence: float
```

### 10.10 SalaryEstimate

```python
SalaryEstimate:
  role: str
  location: str
  experience_years: float
  employment_type: str
  work_mode: str

  salary_min: Decimal
  salary_mid: Decimal
  salary_max: Decimal
  currency: str
  period: str

  data_source: str
  source_date: date | None
  confidence: str
  sample_size: int | None

  factors: list[SalaryFactor]
  assumptions: list[str]
  limitations: list[str]
```

Use numeric fields instead of storing values such as `"60,000 - 80,000"` as the canonical representation.

### 10.11 Application

```python
Application:
  id: str
  job_id: str
  resume_version_id: str
  cover_letter_version_id: str | None
  stage: str
  applied_at: datetime | None
  next_action_at: datetime | None
  source: str
  recruiter_name: str
  recruiter_email: str
  notes: str
  outcome_reason: str
  created_at: datetime
  updated_at: datetime
```

Application stages:

```text
saved
preparing
applied
screening
assessment
interview
offer
accepted
rejected
withdrawn
archived
```

### 10.12 AIRun

```python
AIRun:
  id: str
  feature: str
  provider: str
  model: str
  prompt_version: str
  temperature: float
  input_hash: str
  duration_ms: int
  status: str
  error_type: str | None
  validation_errors: list[str]
  created_at: datetime
```

Prompt content containing personal resume data should not be written to normal logs.

---

## 11. DATABASE_TABLES

### Core Tables

```text
resumes
resume_versions
jobs
analysis_runs
applications
cover_letters
cover_letter_versions
interview_sessions
interview_questions
skill_gap_runs
salary_estimate_runs
ai_runs
app_settings
schema_metadata
```

### Relationships

```text
Resume
  └── ResumeVersion
        ├── AnalysisRun
        ├── Application
        └── CoverLetterVersion

JobDescription
  ├── AnalysisRun
  ├── Application
  ├── CoverLetter
  ├── SkillGapRun
  └── InterviewSession
```

### Database Requirements

* Foreign-key enforcement enabled
* WAL mode enabled where supported
* Automatic migrations
* Transaction boundaries in services
* Indexes on foreign keys and frequently filtered fields
* Soft archive for resumes and jobs
* Hard delete only through explicit user action
* Database backup before destructive migration

---

## 12. NAVIGATION

Current navigation contains 9 pages.

| Index | Page             | Class                | Responsibility                                              |
| ----: | ---------------- | -------------------- | ----------------------------------------------------------- |
|     0 | Dashboard        | `DashboardPage`      | One-click pipeline, score cards, recent analyses            |
|     1 | Resume Upload    | `ResumeUploadPage`   | Import PDF/DOCX, parse, save                                |
|     2 | Job Description  | `JobDescriptionPage` | Paste, upload, or fetch job description from URL            |
|     3 | ATS Analysis     | `ATSAnalysisPage`    | Keyword heatmap, score cards, suggestions                   |
|     4 | Optimization     | `OptimizationPage`   | Before/after ATS comparison, AI diff preview                |
|     5 | Cover Letter     | `CoverLetterPage`    | Generate tailored cover letter via AI                       |
|     6 | Skill Gap        | `SkillGapPage`       | Match skills vs market demand, learning recommendations     |
|     7 | Salary Estimate  | `SalaryEstimatePage` | Salary range estimation via AI                              |
|     8 | Settings         | `SettingsPage`       | Ollama URL, model, temperature, theme                       |

### Planned pages (future)

| Page             | Class                | Responsibility                                   |
| ---------------- | -------------------- | ------------------------------------------------ |
| Resume Library   | `ResumeLibraryPage`  | Resume list, version history, archive            |
| Job Library      | `JobLibraryPage`     | Saved jobs, statuses, requirements               |
| Interview Prep   | `InterviewPrepPage`  | Questions, STAR drafts, practice sessions        |
| Applications     | `ApplicationsPage`   | Pipeline, notes, stages, follow-ups              |
| Analytics        | `AnalyticsPage`      | Scores, outcomes, conversion metrics             |
| Export Center    | `ExportCenterPage`   | Batch and template-based exports                 |

---

## 13. UI_WORKFLOW

### Global Context Bar

Pages that operate on resume-job pairs should share a persistent context selector:

```text
Resume: [Software Engineer Resume v4 ▼]
Job:    [Backend Engineer — Example Corp ▼]
```

Changing context emits a state event and refreshes dependent pages.

### AppState

```python
AppState:
  selected_resume_id: str | None
  selected_resume_version_id: str | None
  selected_job_id: str | None
  selected_analysis_id: str | None
  selected_application_id: str | None
```

Do not keep full mutable ORM models in global UI state.

### Navigation Guards

Examples:

* ATS Analysis requires a selected resume and job.
* Optimization requires a completed ATS analysis.
* Cover Letter requires a selected resume and job.
* Interview Prep requires a selected job.
* Export requires a selected document version.

Pages should display actionable empty states rather than failing silently.

---

## 14. ATS_ENGINE_V2

ATS scoring must remain deterministic and testable.

### Proposed Score Composition

```text
Overall ATS Score
├── Required keyword coverage       25%
├── Skills alignment                20%
├── Experience alignment            20%
├── Achievement and impact quality  10%
├── Job-title and seniority fit      8%
├── Education/certification fit      7%
├── Resume structure                 5%
└── Readability and formatting       5%
```

Weights should be configurable and versioned.

### Keyword Classification

```text
Hard skills
Tools and technologies
Certifications
Domain terms
Responsibilities
Action verbs
Education requirements
Experience-level terms
Location and work eligibility terms
```

### Matching Levels

* Exact match
* Normalized match
* Alias match
* Acronym match
* Related-skill match
* Context-only match
* Missing

Examples:

```text
PostgreSQL ↔ Postgres
Amazon Web Services ↔ AWS
CI/CD ↔ continuous integration and deployment
JavaScript ↔ JS
```

Related-skill matches should receive less weight than exact or alias matches.

### Evidence Rules

A keyword should receive stronger credit when it appears:

1. In a recent experience bullet
2. With a measurable achievement
3. In both skills and experience
4. In the summary and experience
5. In a project with supporting context

A keyword appearing only in the skills list receives partial credit.

### ATS Findings

Each finding should contain:

```python
Recommendation:
  category: str
  severity: str
  message: str
  evidence: str
  suggested_action: str
  estimated_score_impact: float | None
```

Avoid promising that a specific change guarantees an interview.

---

## 15. RESUME_QUALITY_ENGINE

Add a deterministic quality engine independent of job matching.

### Checks

* Missing or invalid contact fields
* Weak or absent headline
* Summary length
* First-person pronouns
* Passive language
* Repeated action verbs
* Long bullet points
* Bullets without outcomes
* Missing metrics
* Unexplained employment gaps
* Inconsistent date formats
* Duplicate skills
* Unsupported proficiency claims
* Outdated or irrelevant content
* Excessive section count
* Missing recent experience details
* Potentially ATS-hostile formatting
* Suspicious keyword repetition
* Placeholder text
* Spelling consistency
* Tense consistency

### Output

```python
ResumeQualityResult:
  score: float
  category_scores: dict[str, float]
  findings: list[QualityFinding]
  statistics: ResumeStatistics
```

---

## 16. AI_ARCHITECTURE

### Provider Interface

```python
class AIProvider(Protocol):
    def health_check(self) -> ProviderHealth: ...
    def list_models(self) -> list[ModelInfo]: ...
    def generate_text(self, request: AIRequest) -> AIResponse: ...
    def generate_structured(
        self,
        request: AIRequest,
        output_schema: type[BaseModel],
    ) -> BaseModel: ...
```

Ollama is the initial provider, but services should depend on `AIProvider`, not `OllamaClient`.

### AI Request Pipeline

```text
Service
  → Select prompt template
  → Build minimal context
  → Apply privacy rules
  → Submit to provider
  → Parse response
  → Validate against Pydantic schema
  → Apply domain validation
  → Run fact guard
  → Retry repair prompt when appropriate
  → Return result or typed error
```

### Prompt Registry

Every prompt should define:

```text
feature
version
output schema
minimum model capability
default temperature
maximum context policy
required variables
```

Example prompt ID:

```text
resume.optimize.v2
```

### Structured Output Rules

* Prefer JSON for machine-readable features.
* Reject unknown mandatory structures.
* Allow controlled repair attempts.
* Preserve raw AI responses only in temporary diagnostic mode.
* Never save invalid data as a successful result.
* Never silently replace missing fields with invented content.

### Model Health Panel

Settings should display:

* Ollama connection state
* Ollama version when available
* Selected model availability
* Model context length when known
* Structured-output test result
* Average response time
* Last error
* Test prompt button

---

## 17. FACT_GUARD

AI optimization must not invent:

* Employers
* Job titles
* Employment dates
* Degrees
* Certifications
* Projects
* Technologies
* Metrics
* Responsibilities
* Awards
* Languages
* Security clearances

### Change Classification

```text
Safe rewrite
Formatting change
Reordered content
Reasonable paraphrase
Unsupported detail
Possible exaggeration
New factual claim
User verification required
```

### Optimization Output

```python
OptimizationResult:
  proposed_resume: ResumeData
  changes: list[ResumeChange]
  unsupported_claims: list[ClaimFinding]
  warnings: list[str]
  summary: str
```

### ResumeChange

```python
ResumeChange:
  path: str
  operation: str
  before: str
  after: str
  reason: str
  source_evidence: list[str]
  confidence: float
  requires_review: bool
```

Users should be able to accept or reject changes individually.

---

## 18. NEW_FEATURES

### 18.1 Resume Library and Version History

Capabilities:

* Manage multiple resumes
* Name resumes by target role
* Duplicate resume
* Archive resume
* Lock important versions
* Compare any two versions
* Restore an older version
* Label versions
* View optimization history
* Track ATS scores by version

### 18.2 Job Library

Capabilities:

* Save multiple job descriptions
* Detect duplicate postings
* Add status and priority
* Extract requirements
* Add notes
* Archive expired jobs
* Link jobs to applications
* Compare jobs against one resume

### 18.3 Batch Job Comparison

Select one resume and multiple jobs.

Output:

```python
JobComparisonResult:
  resume_version_id: str
  jobs: list[JobFitSummary]
  strongest_shared_skills: list[str]
  common_skill_gaps: list[str]
  generated_at: datetime
```

Display:

* ATS score by job
* Required keyword coverage
* High-priority missing skills
* Resume version used
* Analysis date

The interface may sort by objective score but should avoid implying guaranteed hiring outcomes.

### 18.4 Achievement Bullet Builder

Input:

```text
What did you do?
Why did it matter?
What tools did you use?
What changed?
Can the result be measured?
```

Output:

* Action + task
* Action + task + result
* STAR-style bullet
* Technical bullet
* Leadership bullet

Generated metrics must never be invented.

### 18.5 Interview Preparation

Capabilities:

* Generate role-specific questions
* Generate questions from the job description
* Generate questions from resume experience
* Draft STAR response outlines
* Detect weak or unsupported answers
* Save practice sessions
* Track confidence by topic
* Generate questions for the interviewer
* Produce a pre-interview briefing sheet

### 18.6 Application Tracker

Views:

* Table
* Kanban pipeline
* Timeline
* Follow-up calendar

Metrics:

* Applications submitted
* Response rate
* Screening rate
* Interview rate
* Offer rate
* Average days by stage
* Resume version performance
* Source performance

### 18.7 Career Analytics

Charts:

* ATS score over time
* Keyword coverage over time
* Most frequent missing skills
* Applications by stage
* Interviews by resume version
* Outcomes by job source
* Time spent in each stage
* Weekly application activity

Analytics must state when sample sizes are too small for meaningful conclusions.

### 18.8 Export Center

Capabilities:

* Choose resume version
* Select template
* Choose page size
* Select included sections
* Preview page count
* Export multiple formats
* Export application package
* Save export presets

Application package:

```text
CandidateName_Company_Role/
├── CandidateName_Resume.pdf
├── CandidateName_Resume.docx
├── CandidateName_Cover_Letter.pdf
└── application_notes.txt
```

### 18.9 Backup and Restore

Capabilities:

* Manual backup
* Automatic scheduled backup
* Backup before migration
* Configurable retention
* Restore preview
* Export all data as JSON
* Import JSON backup
* Validate backup integrity

---

## 19. DOCUMENT_IMPORT

### Supported Formats

| Format         | Method                                |
| -------------- | ------------------------------------- |
| PDF            | PyMuPDF text blocks                   |
| DOCX           | python-docx paragraphs and tables     |
| TXT            | Encoding-aware text read              |
| Markdown       | Plain-text parsing                    |
| Image-only PDF | Detect and report; optional OCR later |

### Import Quality Result

```python
DocumentReadResult:
  text: str
  page_count: int | None
  metadata: dict[str, str]
  warnings: list[str]
  quality_score: float
  extraction_method: str
  is_probably_scanned: bool
```

### Validation

* Maximum file size
* Supported extension
* MIME-type inspection
* Empty document detection
* Encrypted PDF detection
* Corrupted file handling
* Extraction-quality warning
* Hash-based duplicate detection

Never execute macros or embedded document content.

---

## 20. EXPORT_SYSTEM

### Exporter Interface

```python
class ResumeExporter(Protocol):
    format_name: str

    def export(
        self,
        resume: ResumeData,
        destination: Path,
        options: ExportOptions,
    ) -> ExportResult:
        ...
```

### Export Options

```python
ExportOptions:
  template: str
  page_size: str
  font_family: str
  base_font_size: float
  margins: MarginSettings
  section_order: list[str]
  hidden_sections: list[str]
  include_page_numbers: bool
  include_links: bool
  metadata: dict[str, str]
```

### Formats

* DOCX
* PDF
* Markdown
* Plain text
* JSON
* Application package ZIP

### Templates

Initial templates:

* Classic ATS
* Modern ATS
* Compact ATS

All templates should avoid:

* Text boxes for essential content
* Multi-column experience sections
* Icons without text equivalents
* Header-only contact information
* Images containing text
* Tables for core employment history

---

## 21. ERROR_HANDLING

### Error Hierarchy

```python
ResumeOptimizerError
├── ConfigurationError
├── DatabaseError
├── MigrationError
├── DocumentReadError
├── DocumentValidationError
├── ResumeParseError
├── AnalysisError
├── ExportError
├── AIProviderError
│   ├── AIConnectionError
│   ├── AIModelUnavailableError
│   ├── AITimeoutError
│   ├── AIResponseError
│   └── AIValidationError
└── BackupError
```

### UI Error Requirements

Every recoverable error should show:

* What failed
* Why it may have failed
* Whether user data was saved
* Recommended next action
* Optional technical details
* Retry action when applicable

Do not display raw stack traces in normal user dialogs.

---

## 22. BACKGROUND_WORKERS

Long-running tasks:

* Document extraction
* AI generation
* ATS analysis for large batches
* Export
* Backup
* Database migration
* Batch comparison

### Worker Events

```text
started
progress
status_changed
result
cancelled
failed
finished
```

### Worker Requirements

* Cooperative cancellation
* Safe exception transport
* No UI widget access from worker threads
* Disable duplicate submissions
* Progress overlay for blocking operations
* Idempotent save behavior
* Timeout handling for Ollama requests

---

## 23. CONFIGURATION

### Typed Settings

```python
AppSettings:
  appearance: AppearanceSettings
  ai: AISettings
  export: ExportSettings
  privacy: PrivacySettings
  backup: BackupSettings
  analysis: AnalysisSettings
```

### AISettings

```python
AISettings:
  provider: str
  base_url: str
  model: str
  temperature: float
  request_timeout_seconds: int
  max_retries: int
  keep_alive: str
  structured_output_enabled: bool
```

### PrivacySettings

```python
PrivacySettings:
  redact_logs: bool
  save_ai_diagnostics: bool
  diagnostics_retention_days: int
  confirm_before_external_request: bool
  clear_temporary_files_on_exit: bool
```

### AnalysisSettings

```python
AnalysisSettings:
  scoring_profile: str
  fuzzy_match_threshold: int
  related_skill_weight: float
  keyword_stuffing_penalty: float
```

---

## 24. PRIVACY_AND_SECURITY

### Local-First Defaults

* Store data locally
* Do not require an account
* Do not send analytics by default
* Do not upload documents automatically
* Do not log resume text
* Do not log job-description text
* Do not log AI prompts containing personal data
* Make external integrations opt-in

### Sensitive Data Controls

* Clear all application data
* Delete individual resume permanently
* Delete individual job permanently
* Clear AI diagnostic cache
* Open data directory
* Export personal data
* Disable recent-file history
* Optional database encryption in a future release

### Log Redaction

Redact:

* Email addresses
* Phone numbers
* Home addresses
* Full resume content
* Full job-description content
* Authentication tokens
* API keys
* Prompt bodies

Allow:

* Record IDs
* Feature names
* Model names
* Durations
* Error categories
* Validation counts

---

## 25. LOGGING_AND_DIAGNOSTICS

### Log Files

```text
logs/
├── application.log
└── application.log.1
```

### Log Context

```text
timestamp
level
module
operation
record_id
ai_run_id
duration_ms
error_type
```

### Rotation

* Maximum file size: 5 MB
* Retained files: 3
* UTF-8 encoding
* Console logging enabled in development
* Personal data redaction enabled by default

### Diagnostics Screen

Display:

* Application version
* Python version
* Qt version
* Database path
* Database schema version
* Ollama connection
* Selected model
* Log directory
* Last backup
* Export directory
* Copy diagnostics button

---

## 26. TEST_STRATEGY

### Unit Tests

Test pure behavior:

* Keyword extraction
* Skill normalization
* ATS scoring
* Score weighting
* Quality checks
* Fact-guard classification
* Pydantic validation
* Date normalization
* Salary numeric validation
* Export text measurement
* Diff generation

### Integration Tests

Test connected components:

* File import to database
* Resume parsing workflow
* Job parsing workflow
* ATS analysis persistence
* Optimization version creation
* Export generation
* Database migration
* Backup and restore
* AI response repair using mocked Ollama

### Regression Tests

Maintain anonymized fixtures for:

* One-page resume
* Two-page resume
* Resume with tables
* Resume with unusual section names
* Graduate resume
* Executive resume
* Technical resume
* Resume with no summary
* Empty or corrupted document
* Job description with no explicit skills
* Very long job description
* Multilingual resume

### UI Tests

Using `pytest-qt`:

* Page navigation
* Empty states
* Context selector changes
* Worker progress
* Error dialogs
* Save and cancel flows
* Version selection
* Theme switching
* Keyboard navigation

### Quality Gates

```text
ruff check .
mypy app
pytest
pytest --cov=app
```

Recommended minimum coverage:

```text
Domain engines:        90%
Services:              80%
Readers and exporters: 75%
Overall:                80%
```

---

## 27. PERFORMANCE_TARGETS

| Operation                |                                Target |
| ------------------------ | ------------------------------------: |
| Application startup      |                       Under 2 seconds |
| Resume library load      |          Under 300 ms for 500 resumes |
| Job library load         |           Under 300 ms for 1,000 jobs |
| ATS analysis             |           Under 1 second excluding AI |
| Database save            |                          Under 200 ms |
| Basic DOCX export        |                       Under 2 seconds |
| Basic PDF export         |                       Under 3 seconds |
| UI input response        |                          Under 100 ms |
| AI cancellation response | Under 1 second where provider permits |

AI generation time depends on the selected model and hardware and should not block the UI.

---

## 28. ACCESSIBILITY

* Complete keyboard navigation
* Visible focus indicators
* Screen-reader labels
* Sufficient text contrast
* Do not rely on color alone for status
* Scalable fonts
* Minimum interactive target sizes
* Accessible score explanations
* Light, dark, and system theme options
* Reduced-animation option
* Copyable error messages

---

## 29. DEVELOPMENT_RULES

1. No business logic in Qt widgets.
2. No database calls directly from pages.
3. No Ollama calls directly from pages.
4. No mutable global domain objects.
5. No AI output saved without validation.
6. No original resume version overwritten.
7. No salary estimate without source metadata.
8. No invented metrics in resume bullets.
9. No silent exception handling.
10. No schema change without migration.
11. No personal content in routine logs.
12. No blocking network or export calls on the UI thread.
13. Every scoring rule requires a unit test.
14. Every prompt change increments its prompt version.
15. Every analysis records its engine version.
16. Every exporter receives the same canonical resume model.
17. Every destructive action requires explicit confirmation.
18. New features must define loading, empty, success, and error states.

---

## 30. IMPLEMENTATION_ROADMAP

### Phase 1 — Structural Stabilization

* Remove duplicate `ats_engine.py`
* Rename `at_analysis.py` to `ats_analysis.py`
* Consolidate configuration
* Introduce application data directories
* Split schemas by domain
* Introduce repository layer
* Add typed error hierarchy
* Add Alembic
* Add Ruff and mypy
* Add database backup before migration

### Phase 2 — Resume and Job Libraries

* Add `Resume` and `ResumeVersion`
* Add resume-library page
* Add job-library page
* Add version comparison
* Add archive and restore
* Add duplicate detection
* Add global context selectors
* Migrate existing records

### Phase 3 — Analysis Quality

* Implement ATS Engine V2
* Add score explanations
* Add keyword evidence
* Add skill aliases
* Add resume-quality engine
* Add score caching
* Add regression fixtures
* Add engine versioning

### Phase 4 — Safe AI Optimization

* Introduce provider interface
* Add prompt registry
* Add AI run records
* Add structured-output validation
* Add response repair
* Add fact guard
* [x] Add per-change acceptance
* Add model diagnostics

### Phase 5 — Application Workflow

* Add cover-letter versioning
* Add interview preparation
* Add application tracker
* Add stage history
* Add follow-up dates
* Add export packages
* Add dashboard metrics

### Phase 6 — Analytics and Market Data

* Add application analytics
* Add resume-performance analytics
* Add batch job comparison
* Redesign salary guidance around sourced data
* Add skill-demand dataset support
* Add confidence indicators
* Add data-source management

### Phase 7 — Release Readiness

* Add accessibility review
* Add automatic backups
* Add restore flow
* Add packaged-app tests
* Add Windows, macOS, and Linux builds
* Add upgrade tests
* Add crash-safe recovery
* Add user documentation
* Add release checklist

---

## 31. IMMEDIATE_PRIORITY_BACKLOG

### P0 — Correctness

* [x] Remove duplicate ATS engine (`app/ats_engine.py` deleted 2026-07-16)
* [x] Resolve ATS page filename mismatch (already correct: `ats_analysis.py`)
* [x] Split `database/db.py` into engine/session/repositories (2026-07-16)
* [x] Consolidate settings files (2026-07-16)
* [x] Add database migrations with Alembic (2026-07-16)
* [x] Preserve original resume imports (2026-07-16)
* [x] Validate all AI JSON before saving (2026-07-16)
* [x] Redesign salary values as numeric fields (2026-07-16)
* [x] Add salary source and confidence fields (2026-07-16)
* [x] Prevent AI-generated unsupported claims (#2: safe-only apply + fact guard)
* [x] Add transaction-safe saves (2026-07-16)

### P1 — Maintainability

* [x] Split `schemas.py` (2026-07-16)
* [x] Split `database/db.py` (2026-07-16)
* [x] Add repository interfaces (2026-07-16)
* [x] Add reusable UI components (2026-07-17) — LoadingOverlay, OllamaStatusLabel
* [ ] Add provider-neutral AI interface
* [ ] Move prompts to versioned template files
* [ ] Add centralized exception handling
* [x] Add typed AppState IDs (2026-07-17)
* [ ] Add prompt and engine version tracking

### P2 — Product Value

* [ ] Add resume library
* [ ] Add resume version history
* [ ] Add job library
* [ ] Add resume-quality checker
* [ ] Add achievement bullet builder
* [ ] Add application tracker
* [ ] Add interview preparation
* [ ] Add batch job comparison
* [ ] Add export center
* [ ] Add backup and restore

### P3 — Release Quality

* [x] Add pytest-qt tests
* [x] Add migration tests (23 tests)
* [x] Add regression fixtures
* [x] Add CI checks (2026-07-17)
* [ ] Add PyInstaller builds
* [ ] Add accessibility checks
* [ ] Add diagnostics page
* [ ] Add upgrade and rollback documentation

---

## 32. DEFINITION_OF_DONE

A feature is complete only when:

* Domain schema exists
* Database changes include a migration
* Service-level use case exists
* UI has loading, empty, success, and error states
* Long-running work is moved off the UI thread
* Inputs and AI outputs are validated
* Errors are logged without personal content
* Unit tests cover core behavior
* Integration tests cover persistence
* Documentation is updated
* Existing data can still be opened
* User can cancel or recover where applicable
* No original resume data is overwritten
* Accessibility labels and keyboard flow are implemented

---

## 33. COMPLETED_WORK

### Cleanup Completed — 2026-07-15

* [x] Deleted orphaned root files
* [x] Deleted obsolete application modules
* [x] Added `pyproject.toml`
* [x] Removed Playwright-based URL fetching
* [x] Removed unused job-description import

### Features Completed — 2026-07-16

* [x] Improved certifications parsing
* [x] Improved experience parsing
* [x] Improved projects parsing
* [x] Improved skills parsing
* [x] Improved language parsing
* [x] Rewritten DOCX export
* [x] Rewritten PDF export
* [x] Added Skill Gap Analysis
* [x] Added Salary Estimation prototype

### Cleanup Completed — 2026-07-16 (continued)

* [x] Removed duplicate ATS engine (`app/ats_engine.py`)
* [x] Split `database/db.py` into engine/session/repositories
* [x] Consolidated settings files (`app/core/settings.py`, `app/core/paths.py`)
* [x] Added Alembic database migrations
* [x] Split `schemas.py` into domain modules (`app/domain/`)
* [x] Added resume import source tracking fields
* [x] Added AI JSON validation with retry logic
* [x] Redesigned salary estimation with numeric fields and source metadata
* [x] Added transaction-safe saves with rollback

The salary feature remains a prototype until it uses a dated and identified salary-data source.

### Features Completed — 2026-07-17

* [x] Ollama connection status indicator (OllamaCheckerThread + OllamaStatusLabel)
* [x] Loading overlays for all async AI operations (LoadingOverlay + LoadingOverlayManager)
* [x] Job description URL fetcher (JobFetcher service + _FetchWorker thread)
* [x] ATS score before/after comparison on optimization page
* [x] Keyword heatmap visualization (matched=green, missing=red) on ATS analysis page
* [x] One-click optimization pipeline (ATS → Optimize → Cover Letter with progress bar)
* [x] Model pre-warming on app startup (background OllamaClient.pre_warm())
* [x] Pipeline state fields in AppState
* [x] Pipeline button + cancel + progress UI on Dashboard page
* [x] Theme styles for pipeline button, cancel button, step label
* [x] Added beautifulsoup4 dependency
* [x] Synced requirements.txt with pyproject.toml

### Bug Audit Fixes — 2026-07-17

25-issue comprehensive bug audit covering crashes, data integrity, UX, parser correctness, and test coverage:

* [x] **#1** Fixed `OllamaError` import in `resume_parser.py`
* [x] **#2** Optimizer now only applies safe changes; flagged changes require user review (Accept/Reject UI)
* [x] **#3** Fact guard uses `SequenceMatcher` for inserted/rewritten bullet detection; all bullets checked
* [x] **#4** ATS scoring uses structured resume data only; falls back to raw_text only when structured is empty
* [x] **#5** Migration 0002 already exists for source columns (was already fixed)
* [x] **#6** Fixed `pyproject.toml` build backend to `setuptools.build_meta`
* [x] **#7** Added `_sync_selected_keywords()` to ATS page for keyword checkbox sync
* [x] **#8** Fixed salary experience range to apply min floor before max calculation
* [x] **#9** Entity detection requires multi-word proper nouns or company suffixes; skill normalization with aliases
* [x] **#10** Headline added to diff highlight comparison preview
* [x] **#11** Cover letter fact-checking for numbers and company names; warnings appended to output
* [x] **#12** `RunPipelineUseCase` sets `requires_review=True` and skips DB save when flagged
* [x] **#13** Global `threading.Event` cancel mechanism in workers; `OllamaClient.set_cancel_event()`
* [x] **#14** Ollama status check guards against overlapping threads; cleanup on finish
* [x] **#15** `load_settings()` returns `model_copy(deep=True)` in all fallback paths
* [x] **#16** `_quarantine_settings()` renames broken file to `.invalid.json`
* [x] **#17** `AppState.reload_settings()` added; `SettingsPage` calls it after save
* [x] **#18** Project parser detects new title-like lines before merging into previous bullet
* [x] **#19** Experience parser detects new job entries by checking length, case, digits, bullets
* [x] **#20** `_KNOWN_SKILLS` curated vocabulary for skill extraction from JDs
* [x] **#21** Token-based highlighting in ATS heatmap avoids matching inside HTML tags
* [x] **#22** Salary disclaimer updated to explicit WARNING about no external data source
* [x] **#23** Skill gap disclaimer already present (from earlier work)
* [x] **#24** Job description page runs analyses sequentially (ATS first, then skill gap, then salary)
* [x] **#25** Test coverage expanded: 161 tests across 11 test files (was 15 tests across 5 files)

### Infrastructure Fixes — 2026-07-17

* [x] Fixed `migrations/env.py` — uses `context.config` instead of stale module-level variable
* [x] Added SSRF protection to `job_fetcher.py` — IP validation, redirect protection, content-type checks
* [x] Fixed `test_migrations.py` — 23 tests all passing
* [x] Fixed `test_job_fetcher.py` — 30 tests all passing

---

## 34. TARGET_RELEASE_MILESTONES

### v0.2 — Stable Core

* Consolidated architecture
* Database migrations
* Resume versioning
* Job library
* Explainable ATS scoring
* Reliable exports

### v0.3 — Safe AI

* Provider abstraction
* Prompt versioning
* Structured-output repair
* Fact guard
* Selective optimization changes
* Model diagnostics

### v0.4 — Job Search Workspace

* Application tracker
* Interview preparation
* Cover-letter versioning
* Export packages
* Dashboard analytics

### v0.5 — Insights

* Batch job comparison
* Resume performance trends
* Skill-demand datasets
* Sourced salary guidance
* Backup and restore

### v1.0 — Production Desktop Release

* Cross-platform packaging
* Migration compatibility
* Accessibility review
* Full user documentation
* Automated release verification
* Stable backup and recovery process

---

# ============================================================
# FUTURE ROADMAP
# ADDITIONAL FEATURES (POST V1)
# ============================================================

This section contains future ideas that extend Resume Optimizer into a complete
Career Operating System. None of these features are required for the initial
release, but the architecture should be designed so they can be added without
major refactoring.

---

# 1. AI CAREER COACH

An AI assistant that understands the user's entire career instead of only a
single resume.

Capabilities

- Career progression planning
- Promotion readiness analysis
- Skill investment recommendations
- Salary improvement recommendations
- Career transition guidance
- Industry trend analysis
- Long-term career planning
- Burnout risk indicators
- Career goal tracking

Example

Current Position
Backend Engineer

Target
Senior Backend Engineer

Progress
67%

Missing Skills

- Kubernetes
- System Design
- Leadership
- AWS
- Distributed Systems

---

# 2. RECRUITER SIMULATOR

Run multiple simulated reviewers.

Reviewer Types

- ATS
- HR Recruiter
- Hiring Manager
- Engineering Manager
- CTO
- Startup Founder
- Enterprise Recruiter

Each reviewer provides

- Positive feedback
- Concerns
- Missing information
- Suggested improvements
- Overall recommendation

---

# 3. RESUME HEATMAP

Visualize recruiter attention.

Sections receive color coding.

Green

Excellent

Yellow

Needs Improvement

Red

Likely Ignored

Heatmaps available for

- Summary
- Experience
- Skills
- Projects
- Education
- Certifications

---

# 4. RESUME HEALTH SCORE

Independent of ATS.

Categories

- Grammar
- Readability
- Formatting
- Technical Depth
- Leadership
- Measurable Impact
- Resume Density
- Keyword Balance
- Resume Length
- Consistency

---

# 5. RESUME BENCHMARKING

Compare resumes against datasets.

Benchmarks

- Junior
- Mid-Level
- Senior
- Staff Engineer
- Engineering Manager
- Data Scientist
- Product Manager

Results

Top 12%

Technical Skills

Top 7%

Leadership

Top 30%

Communication

Top 18%

---

# 6. RESUME PERFORMANCE ANALYTICS

Track resume performance over time.

Metrics

- Applications
- Interviews
- Technical Interviews
- Final Interviews
- Offers
- Rejections
- Ghosting Rate
- Response Rate

Compare

Resume Version A

vs

Resume Version B

---

# 7. AI PORTFOLIO GENERATOR

Automatically generate

- Portfolio Website
- GitHub Profile README
- About Me
- Personal Bio
- Landing Page
- Project Pages

---

# 8. LINKEDIN OPTIMIZER

Generate

- Headline
- About Section
- Experience
- Skills
- Featured Section
- Banner Suggestions
- Profile Score

---

# 9. GITHUB PROFILE OPTIMIZER

Generate

README

Pinned Projects

Contribution Summary

Open Source Recommendations

Repository Descriptions

---

# 10. STAR STORY DATABASE

Store reusable interview stories.

Each story includes

Situation

Task

Action

Result

Tags

- Leadership
- Conflict
- Failure
- Success
- Architecture
- Optimization
- Scaling

---

# 11. INTERVIEW SIMULATOR

Practice interviews.

Modes

Behavioral

Technical

System Design

Coding

Leadership

Voice Practice

Future

Webcam Practice

---

# 12. APPLICATION CRM

Advanced tracking.

Store

Recruiters

Referrals

Contacts

Emails

Interview Notes

Negotiation Notes

Offer Documents

---

# 13. NEGOTIATION ASSISTANT

Provide

Salary Comparison

Market Data

Negotiation Scripts

Counter Offer Suggestions

Benefits Comparison

---

# 14. COMPANY INTELLIGENCE

Automatically summarize

Company Size

Funding

Tech Stack

Culture

Interview Process

Recent News

Hiring Trends

Glassdoor Summary

---

# 15. JOB INTELLIGENCE

Analyze thousands of jobs.

Show

Common Skills

Trending Technologies

Salary Trends

Location Demand

Remote Availability

Experience Distribution

---

# 16. SKILL GRAPH

Create relationships.

Example

Python

├── FastAPI

├── Django

├── Flask

├── SQLAlchemy

├── AsyncIO

└── Docker

Suggest

Adjacent Skills

Learning Order

Difficulty

---

# 17. LEARNING PLANNER

Generate learning roadmap.

Example

Week 1

Docker

Week 2

Compose

Week 3

Networking

Week 4

Deployment

Estimated Hours

Resources

Progress Tracking

---

# 18. CAREER TIMELINE

Interactive timeline.

Education

Experience

Projects

Promotions

Certifications

Achievements

Interviews

Offers

---

# 19. KNOWLEDGE GRAPH

Represent relationships.

Resume

↓

Projects

↓

Skills

↓

Technologies

↓

Companies

↓

Jobs

↓

Recruiters

↓

Applications

---

# 20. AI AGENTS

Specialized agents.

Resume Agent

Interview Agent

Learning Agent

Career Coach Agent

Application Agent

Analytics Agent

Export Agent

Research Agent

---

# 21. MULTI-MODEL AI SUPPORT

Supported Providers

Ollama

LM Studio

llama.cpp

OpenAI Compatible

Anthropic Compatible

Custom Local Providers

---

# 22. LOCAL RAG

Local Retrieval-Augmented Generation.

Index

Resumes

Job Descriptions

Projects

Interview Notes

Learning Notes

Career History

Personal Documentation

---

# 23. SEMANTIC SEARCH

Search naturally.

Examples

"Show all resumes mentioning Kubernetes"

"Find every project using Python"

"Find interview notes about leadership"

---

# 24. EMBEDDING DATABASE

Support

BGE

Nomic

E5

MiniLM

Custom Embeddings

Caching

Reindexing

---

# 25. RESUME KNOWLEDGE BASE

Automatically extract

Technologies

Domains

Achievements

Leadership Examples

Architecture Examples

Tools

Certifications

---

# 26. AI WORKFLOW BUILDER

Visual automation.

Resume Imported

↓

Parse

↓

ATS Analysis

↓

Optimization

↓

Cover Letter

↓

Export

↓

Application Package

---

# 27. PLUGIN SDK

Plugin Categories

AI Providers

Exporters

Importers

Themes

ATS Rules

Language Packs

Analytics

Interview Packs

Learning Providers

---

# 28. MARKETPLACE

Community plugins.

Resume Templates

Prompt Packs

Interview Packs

Themes

Skill Libraries

Industry Packs

---

# 29. EXPORT SUITE

Generate

PDF

DOCX

Markdown

HTML

Website

Portfolio

ZIP Package

Application Bundle

---

# 30. VOICE FEATURES

Speech Recognition

Interview Practice

Speaking Speed

Confidence Analysis

Filler Word Detection

Pronunciation Feedback

---

# 31. MOBILE COMPANION (FUTURE)

Read-only synchronization.

Dashboard

Applications

Interview Notes

Career Progress

Notifications

---

# 32. TEAM FEATURES

Career Coaches

Recruiters

University Advisors

Mentors

Review Requests

Shared Templates

---

# 33. SECURITY ENHANCEMENTS

Encrypted Database

Secure Vault

Secrets Manager

Encrypted Backups

Audit Logs

Secure Delete

---

# 34. ADVANCED ANALYTICS

Resume Score Trends

Career Growth

Application Funnel

Offer Rate

Interview Rate

Most Valuable Skills

Best Resume Version

---

# 35. FUTURE AI CAPABILITIES

Autonomous Resume Improvement

Automatic Job Prioritization

Daily Career Briefing

Weekly Skill Report

Monthly Resume Audit

Career Opportunity Detection

Automatic Interview Preparation

Goal Tracking

---

# LONG-TERM VISION

Resume Optimizer evolves into a complete offline-first Career Operating System.

It becomes a personal AI platform that helps users

- Build resumes
- Optimize applications
- Track career growth
- Prepare interviews
- Learn new skills
- Manage opportunities
- Analyze market trends
- Plan long-term career development

while ensuring complete privacy through a local-first architecture.
