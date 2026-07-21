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
* 🔭 Future

| Feature                              | Status |
| ------------------------------------ | ------ |
| Resume PDF/DOCX/TXT import           | ✅      |
| Resume parsing (heuristic + AI)      | ✅      |
| Job-description import (paste/file)  | ✅      |
| Job-description URL fetch            | ✅      |
| Deterministic ATS analysis           | ✅      |
| ATS score before/after comparison    | ✅      |
| Keyword heatmap visualization        | ✅      |
| AI resume optimization               | ✅      |
| Per-change accept/reject review      | ✅      |
| Resume comparison and diff           | ✅      |
| Cover-letter generation              | ✅      |
| Cover-letter library                 | ✅      |
| Skill-gap analysis                   | ✅      |
| Salary estimation with benchmarks    | ✅      |
| Salary benchmark data service        | ✅      |
| DOCX/PDF/Markdown export             | ✅      |
| One-click optimization pipeline      | ✅      |
| Ollama connection status indicator   | ✅      |
| Loading overlays for async ops       | ✅      |
| Model pre-warming on startup         | ✅      |
| ResumeAI Resume Studio (MVVM)        | ✅      |
| ResumeAI dark-navy UI theme          | ✅      |
| ResumeAI design system (9 components)| ✅      |
| Section tabs + section menu          | ✅      |
| Sidebar icon navigation              | ✅      |
| Top nav with resume dropdown         | ✅      |
| Toggle switch component              | ✅      |
| Form field component                 | ✅      |
| Dropdown component                   | ✅      |
| Card component                       | ✅      |
| Toast notifications                  | ✅      |
| Section-based editor                 | ✅      |
| Live resume preview                  | ✅      |
| Undo and redo                        | ✅      |
| Real-time issue panel                | ✅      |
| Five-category explainable score      | ✅      |
| ResumeAI keyword targeting           | ✅      |
| Evidence paths for matched keywords  | ✅      |
| Three bullet alternatives            | ✅      |
| Bullet writer with keyword highlight | ✅      |
| Side-by-side diff                    | ✅      |
| Template manifests (7 presets)       | ✅      |
| Auto-adjust (binary search fit)      | ✅      |
| Resume versioning (DB backend)       | ✅      |
| Immutable version snapshots          | ✅      |
| Targeting sessions                   | ✅      |
| Suggestion records (accept/reject)   | ✅      |
| SSRF protection (DNS + port)         | ✅      |
| Browser SSRF routing (Playwright)    | ✅      |
| Document size/page limits            | ✅      |
| Cooperative worker cancellation      | ✅      |
| Streaming Ollama client              | ✅      |
| Fact guard (semantic reversals)      | ✅      |
| Fact guard (deleted bullets)         | ✅      |
| Fact guard (negation detection)      | ✅      |
| Indexed bullet rewrites              | ✅      |
| Cover-letter fact-check warnings     | ✅      |
| Cover-letter target employer exempt  | ✅      |
| Salary experience calculation (DI)   | ✅      |
| Dev tooling (ruff, mypy, bandit)     | ✅      |
| CI workflow (Win/Mac/Linux)          | ✅      |
| Auto-save                            | ✅      |
| Resume duplication                   | ✅      |
| Section reorder and rename           | ✅      |
| Click issue to navigate to field     | ✅      |
| Live template switching              | ✅      |
| Export validation                    | ✅      |
| Keyboard shortcuts (Ctrl+S, etc.)    | ✅      |
| AI agent workflow                    | ✅      |
| Multi-turn agent conversations       | ✅      |
| Application tracker                  | ✅      |
| Interview preparation                | ✅      |
| Job-specific resume variants         | ✅      |
| LinkedIn data import                 | ✅      |
| Score history tracking               | ✅      |
| Application analytics dashboard      | ✅      |
| Backup and restore                   | ✅      |
| Resume comparison view               | ✅      |
| Global search                        | ✅      |
| Onboarding wizard                    | ✅      |
| Evidence Vault (save evidence)       | ✅      |
| Master Profile (career summary)      | ✅      |
| Requirement Matrix (JD comparison)   | ✅      |
| Discovery Interview (prep session)   | ✅      |
| ResumeAI contact page                | ✅      |
| Content checker (23-factor scoring)  | ✅      |
| Career embeddings (semantic search)  | ✅      |
| Profile compiler (resume from profile)| ✅     |
| Skill explorer                       | ✅      |
| Resume scorer                        | ✅      |
| Optional encrypted sensitive fields  | 🔭      |
| Optional job-board integrations      | 🔭      |

---

## 3. TECH_STACK

### Core Runtime

| Package        | Version Policy         | Purpose                               |
| -------------- | ---------------------- | ------------------------------------- |
| Python         | 3.12+                  | Application runtime                   |
| PySide6        | Compatible 6.x release | Qt desktop GUI                        |
| SQLAlchemy     | Compatible 2.x release | ORM and SQLite access                 |
| Pydantic       | Compatible 2.x release | Validation and structured AI output   |
| PyMuPDF        | Compatible 1.x release | PDF extraction, rendering, and export |
| python-docx    | Compatible 1.x release | DOCX import and export                |
| requests       | Compatible 2.x release | Ollama HTTP communication             |
| beautifulsoup4 | Compatible 4.x release | HTML parsing for URL job fetch        |
| lxml           | Compatible 5.x release | Fast HTML parser backend              |
| Alembic        | Compatible 1.x release | Database schema migrations            |
| circuitbreaker | Compatible 2.x release | Ollama circuit breaker                |

### Dev Tooling

| Package    | Purpose                            | Status |
| ---------- | ---------------------------------- | ------ |
| pytest     | Automated testing                  | ✅      |
| pytest-cov | Coverage reporting                 | ✅      |
| ruff       | Linting and formatting             | ✅      |
| mypy       | Static type checking               | ✅      |
| bandit     | Security scanning                  | ✅      |
| pip-audit  | Dependency vulnerability scanning  | ✅      |

### Packaging

| Tool                         | Purpose                                               |
| ---------------------------- | ----------------------------------------------------- |
| `pyproject.toml`             | Project metadata, dependencies, tooling configuration |
| PyInstaller                  | Standalone application builds                         |
| GitHub Actions               | Automated tests and security scanning                 |
| Alembic                      | Database upgrade compatibility                        |

---

## 4. SYSTEM_CONTEXT

```text
┌────────────────────────────────────────────────────────────┐
│                         USER                               │
└──────────────┬─────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────────┐
│                 PySide6 Desktop UI (ResumeAI)               │
│                                                            │
│ Sidebar │ Top Nav │ Section Tabs │ Content Stack           │
│ Dashboard │ Studio │ Resumes │ Jobs │ Analysis │ Optimize  │
│ Agent │ Letters │ Skill Gap │ Salary │ Apps │ Library     │
│ Interview │ LinkedIn │ Compare │ Vault │ Matrix │ Settings │
└──────────────┬─────────────────────────────────────────────┘
               │ Commands / Queries
               ▼
┌────────────────────────────────────────────────────────────┐
│                  Application Services                      │
│                                                            │
│ ImportResumeUseCase     AnalyzeResumeUseCase               │
│ OptimizeResumeUseCase   RunPipelineUseCase                 │
│ CompileFromProfileUseCase                                  │
└──────────┬───────────────────┬─────────────────────┬───────┘
           │                   │                     │
           ▼                   ▼                     ▼
┌──────────────────┐ ┌───────────────────┐ ┌─────────────────┐
│ Domain Engines   │ │ AI Infrastructure │ │ Persistence     │
│                  │ │                   │ │                 │
│ ATS scoring      │ │ OllamaClient      │ │ SQLAlchemy      │
│ Keyword matching │ │ Prompt templates  │ │ Repositories    │
│ Scoring engine   │ │ Post-processor    │ │ SQLite + WAL    │
│ Fact guard       │ │ Circuit breaker   │ │ Alembic         │
│ Diff engine      │ │ Streaming NDJSON  │ │ Migrations      │
│ Auto-fit         │ │ JSON-schema out   │ │ Backup          │
│ Agent proposals  │ │                   │ │ Global search   │
│ Interview prep   │ │                   │ │ Score history   │
│ Evidence vault   │ │                   │ │ Evidence repo   │
│ Profile compiler │ │                   │ │ Master profile  │
│ Career search    │ │                   │ │ Career embed    │
│ Skill explorer   │ │                   │ │                 │
└──────────────────┘ └───────────────────┘ └─────────────────┘
           │                   │                     │
           └───────────────────┴─────────────────────┘
                               │
                               ▼
                    DOCX / PDF / Markdown
```

---

## 5. PRIMARY_SYSTEM_FLOWS

### 5.1 Resume Import

```text
Select File
    → Validate file type and size
    → Extract text (PyMuPDF / python-docx / plain text)
    → Detect extraction quality
    → Parse structured sections (heuristic or AI)
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
    → Trigger sequential analyses (ATS → Skill Gap → Salary)
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
    → Build constrained AI request (with prompt injection defense)
    → Generate structured proposed changes
    → Validate facts against source resume
    → Flag unsupported claims (semantic reversals, deleted bullets, negation)
    → Show side-by-side diff with red highlighting
    → Accept or reject individual changes
    → Save new ResumeVersion
    → Snapshot score history
```

### 5.5 Cover Letter

```text
Select Resume Version + Job
    → Select tone and length
    → Generate draft via AI
    → Run fact-check (numbers, company names, employer flags)
    → Show warnings separately from letter text
    → Edit and save
    → Export or copy
    → Browse in Cover Letter Library
```

### 5.6 Resume Studio

```text
Open Studio
    → 3-panel layout: Section Navigator | Editor + Preview | Insights
    → Section Tabs + Section Menu for section switching
    → Select section → dynamic form editor
    → Live ATS score recalculation on edit
    → Issue panel with category breakdown
    → Undo/redo for all edits
    → Keyword targeting with evidence paths
    → Bullet writer with 3 alternatives
    → Template selection (7 presets)
    → Auto-adjust to fit page target
    → Auto-save (2s debounce)
    → Duplicate resumes, create versions
    → Reorder/rename sections
    → Click issue to navigate to field
    → Revert to original snapshot
    → Editable review panel for section editing
```

### 5.7 Skill-Gap Analysis

```text
Select Resume + Target Job or Role Profile
    → Extract candidate skills
    → Extract target skills
    → Normalize aliases (SKILL_ALIASES dictionary)
    → Match exact and related skills
    → Rank gaps by importance
    → Build learning recommendations
    → Save SkillGapRun
    → Emit analysis_finished signal (triggers next sequential analysis)
```

### 5.8 Salary Guidance

```text
Role + Location + Experience
    → Calculate experience from date intervals
    → Merge overlapping periods, handle missing dates
    → Format for AI prompt
    → Generate salary range via Ollama
    → Cross-reference with salary benchmark data
    → Show confidence and data-source disclaimer
    → Save SalaryEstimateRun
    → Emit analysis_finished signal (triggers next sequential analysis)
```

### 5.9 AI Agent Workflow

```text
Select Resume + Tool
    → Agent picks appropriate tool (score, target, suggest_bullets, etc.)
    → Format tool-specific prompt
    → Call Ollama with JSON-mode structured output
    → Parse and validate response
    → Run FactGuard validation on proposed changes
    → Show proposal card (original vs proposed, Accept/Reject)
    → Persist conversation history to DB
    → Support multi-turn follow-up messages
```

### 5.10 Application Tracking

```text
Add Application
    → Link to resume + job
    → Set initial status (draft / wishlist / applied)
    → Add notes
    → Advance through workflow: applied → interview → offer/rejected
    → View analytics dashboard (total, applied, interviews, offers, rejected)
```

### 5.11 Interview Preparation

```text
Select Resume + Role + Company
    → Generate behavioral, technical, situational questions via AI
    → Display question cards with STAR outlines
    → Export questions to clipboard or save to DB
    → Review saved sessions
```

### 5.12 Resume Comparison

```text
Select Resume A (Original) + Resume B (Modified)
    → Structured field-by-field diff
    → Highlight name, headline, summary, skills changes
    → Bullet-level diff within experience entries
    → Side-by-side rendering with color-coded changes
```

### 5.13 Sequential Analysis Pipeline

```text
User saves Job Description
    → _trigger_analyses() pre-fills destination pages
    → ATS analysis runs immediately
    → Skill Gap and Salary run sequentially via analysis_finished signal chain
    → Each page stores result in AppState
    → Destination pages display cached results in on_show()
```

### 5.14 Profile Compilation

```text
Master Profile + Target Job
    → Compile resume from master profile
    → Match skills and experience to requirements
    → Generate tailored resume sections
    → Export compiled resume
```

### 5.15 Evidence Vault

```text
Save Evidence
    → Link to resume claims
    → Store supporting documents
    → Source tracking and categorization
    → Retrieve for fact-check validation
```

---

## 6. ARCHITECTURE

```text
Pattern:      Modular monolith with layered boundaries
UI:           PySide6 QMainWindow + ResumeAI sidebar nav + QStackedWidget (20 pages)
Components:   ResumeAI design system (sidebar, top_nav, section_tabs, toggle_switch,
              form_field, dropdown, card, toast, section_menu)
ViewModel:    ResumeStudioViewModel (MVVM for Studio page)
State:        Session-scoped AppState containing IDs, not full domain objects
Domain:       Pure scoring, matching, validation, and transformation logic
Services:     Application use cases, AI orchestration, and transaction coordination
Persistence:  Repository interfaces backed by SQLAlchemy (11 repositories)
Database:     SQLite with Alembic migrations (WAL, foreign keys, busy timeout)
AI:           OllamaClient with streaming, circuit breaker, JSON-schema output
Exports:      Deterministic DOCX/PDF/Markdown via PyMuPDF and python-docx
Config:       Typed Pydantic AppSettings with atomic write and .bak recovery
Logging:      Rotating application log with privacy-safe context
Tooling:      ruff (lint), mypy (types), pytest-cov (coverage), bandit (security)
CI:           GitHub Actions on Windows, macOS, Linux
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

| Module            | Responsibility                                                 |
| ----------------- | -------------------------------------------------------------- |
| `app/core/`       | Paths, typed settings (Pydantic with `onboarding_completed`), app constants |
| `app/domain/`     | Pydantic schemas: resume, analysis, salary, skill gap, pipeline, scoring, fact guard, templates, keyword targeting, bullet writer, agent, job requirements, skill lexicon, certification, evidence, master profile, requirement matrix, discovery, content check |
| `app/ai/`         | Ollama HTTP client (streaming, circuit breaker, JSON-schema), prompt templates (~600 lines), post-processor |
| `app/database/`   | ORM models (20+ tables), engine (WAL + FK enforcement), session, repositories (11), legacy CRUD facade, migration helper |
| `app/application/`| Use cases: import, analyze, optimize, pipeline, compile_from_profile |
| `app/data/`       | Salary benchmark data service                                 |
| `app/services/`   | ATS engine, scoring engine (versioned rules), optimizer, cover letter, parser, fact guard, security, HTML extraction, metadata, job fetcher, browser fetcher, document reader, salary estimator (with benchmarks), skill gap, diff highlight, auto-fit, bullet writer, keyword targeting, job context, agent, interview prep, linkedin import, backup, global search, resume comparison, score history, summary/headline generators, evidence vault, content checker, career embeddings, career search, profile compiler, requirement matrix, skill explorer, resume scorer, discovery |
| `app/exports/`    | Deterministic DOCX/PDF/Markdown export (PyMuPDF + python-docx) |
| `app/config/`     | Legacy compatibility shim (delegates to `app/core/`)           |
| `app/ui/`         | Main window (20-page nav), state, workers, theme, undo stack, components (resumeai design system + legacy), pages (20), view models, dialogs (onboarding) |

### ResumeAI Design System (`app/ui/components/resumeai/`)

| Component        | Class(es)                          | Purpose                                        |
| ---------------- | ---------------------------------- | ---------------------------------------------- |
| `sidebar.py`     | `ResumeAiSidebar`                  | Icon sidebar with tooltip labels and page map  |
| `top_nav.py`     | `ResumeAiTopNav`                   | Top bar with section tabs, resume dropdown     |
| `section_tabs.py`| `SectionTabs`, `PillCheckBox`     | Horizontal tab bar with pill-shaped checkboxes |
| `section_menu.py`| `SectionMenu`                      | Floating section visibility menu               |
| `toggle_switch.py`| `ToggleSwitch`                    | iOS-style toggle switch                        |
| `form_field.py`  | `FormField`                        | Labeled input field with error state           |
| `dropdown.py`    | `Dropdown`                         | Styled QComboBox                               |
| `card.py`        | `Card`                             | Rounded-corner container with title/subtitle   |
| `toast.py`       | `Toast`                            | Slide-in notification banner                   |

---

## 8. ACTUAL_FILE_MAP

```text
resume-optimizer-main/
├── main.py
├── pyproject.toml
├── README.md
├── PROJECT_MAP.md
├── .gitignore
├── alembic.ini
├── opencode.example.json
│
├── .github/
│   └── workflows/
│       └── ci.yml                          # CI: lint, typecheck, test matrix, security
│
├── .opencode/
│   └── agent/
│       ├── claude.md                       # Claude agent config
│       ├── gemini.md                       # Gemini agent config
│       ├── ollama.md                       # Ollama agent config
│       └── openai.md                       # OpenAI agent config
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_initial_schema.py
│       ├── 0002_add_resume_tracking.py
│       ├── 0003_add_cascade_delete.py
│       ├── 0004_add_versioning_and_targeting.py
│       ├── 0005_add_evidence_vault.py
│       └── 0006_add_master_profile.py
│
├── tasks/
│   ├── plan.md                             # Implementation plan (33 tasks, 6 phases — ALL COMPLETE)
│   ├── plan_phase7.md                      # Phase 7 plan
│   ├── plan_phase8_9.md                    # Phase 8-9 plan
│   ├── plan_rezi_ui.md                     # ResumeAI UI redesign plan
│   ├── plan_sprint3.md                     # Sprint 3 plan
│   ├── roadmap_rezi.md                     # ResumeAI roadmap
│   ├── todo.md                             # Task checklist
│   ├── todo_phase7.md                      # Phase 7 checklist
│   ├── todo_rezi_ui.md                     # ResumeAI UI checklist
│   └── todo_sprint3.md                     # Sprint 3 checklist
│
├── app/
│   ├── __init__.py
│   ├── schemas.py                          # Backward-compatible re-exports from app/domain/
│   ├── validators.py                       # ResumeData validation helpers
│   ├── logging_config.py                   # Rotating file + console logging
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── settings.py                     # Typed Pydantic AppSettings + SettingsService singleton
│   │   └── paths.py                        # DB_PATH, CONFIG_PATH, LOG_DIR, EXPORT_DIR, BACKUP_DIR
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   └── salary_benchmarks.py            # Salary benchmark data by role/location/experience
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── resume.py                       # ContactInfo, ExperienceItem, EducationItem, ProjectItem, ResumeData
│   │   ├── certification.py                # CertificationItem
│   │   ├── analysis.py                     # ATSResult domain model
│   │   ├── scoring.py                      # ScoreCategory, ResumeIssue, ResumeScoreReport
│   │   ├── fact_guard.py                   # ChangeType, ProposedChange, FactGuardResult, ParseFactGuardResult
│   │   ├── optimization.py                 # BulletRewrite, OptimizationAIOutput
│   │   ├── pipeline.py                     # PipelineResult dataclass
│   │   ├── salary.py                       # SalaryEstimate (Decimal fields, benchmark integration)
│   │   ├── skill_gap.py                    # SkillGapItem, SkillGapResult
│   │   ├── job_requirements.py             # Requirement, JobRequirements
│   │   ├── keyword_targeting.py            # KeywordStatus, KeywordTarget, JobRequirement, ResumeTextIndex
│   │   ├── bullet_writer.py                # BulletEvidence, BulletSuggestion, BulletSuggestionResult
│   │   ├── skill_lexicon.py                # SKILL_ALIASES dictionary, extract_skills()
│   │   ├── templates.py                    # TemplateManifest, FitResult, CannotFitResumeError, 7 presets
│   │   ├── agent.py                        # AgentTool enum, AgentAction, AgentProposal
│   │   ├── evidence.py                     # EvidenceItem, EvidenceSource
│   │   ├── master_profile.py               # MasterProfile, CareerEntry
│   │   ├── requirement_matrix.py           # MatrixRequirement, RequirementMatrix
│   │   ├── discovery.py                    # DiscoveryQuestion, DiscoverySession
│   │   └── content_check.py                # ContentCheckResult
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── ollama_client.py                # OllamaClient: streaming, circuit breaker, JSON-schema, cancellation
│   │   ├── prompts.py                      # All prompt templates (~600 lines, 7 agent prompts)
│   │   └── post_processor.py               # Context-aware AI text cleaning
│   │
│   ├── database/
│   │   ├── __init__.py                     # Public API exports
│   │   ├── engine.py                       # SQLAlchemy SQLite engine (WAL, FK, busy timeout)
│   │   ├── session.py                      # SessionLocal, get_session() context manager
│   │   ├── models.py                       # 20+ ORM models (Resume, ResumeVersion, JobDescription, Analysis, CoverLetter, AgentConversation, AgentMessage, JobApplication, InterviewSession, ScoreSnapshot, EvidenceItem, MasterProfile, etc.)
│   │   ├── db.py                           # Backward-compatible CRUD facade
│   │   ├── migrate.py                      # Alembic migration helper with backup
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── base.py                     # Abstract base repository
│   │       ├── resume_repository.py        # Resume CRUD + SHA-256 content hash + variants
│   │       ├── job_repository.py           # JobDescription CRUD
│   │       ├── analysis_repository.py      # Analysis CRUD with JOIN queries
│   │       ├── versioning_repository.py    # ResumeVersion, TargetingSession, SuggestionRecord, TemplatePreference CRUD
│   │       ├── agent_repository.py         # Agent conversation + message CRUD (JSON proposal serialization)
│   │       ├── application_repository.py   # JobApplication CRUD (workflow status validation)
│   │       ├── cover_letter_repository.py  # CoverLetter CRUD + full-text search
│   │       ├── evidence_repository.py      # EvidenceItem CRUD + source linking
│   │       ├── evidence_source_repository.py # EvidenceSource CRUD
│   │       └── master_profile_repository.py # MasterProfile CRUD
│   │
│   ├── application/
│   │   ├── __init__.py
│   │   ├── import_resume.py                # ImportResumeUseCase
│   │   ├── analyze_resume.py               # AnalyzeResumeUseCase
│   │   ├── optimize_resume.py              # OptimizeResumeUseCase + RunPipelineUseCase + score history snapshot
│   │   └── compile_from_profile.py         # CompileFromProfileUseCase
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ats_engine.py                   # ATS keyword analysis + scoring + custom skills
│   │   ├── scoring_engine.py               # Versioned rule engine (5 categories, per-finding penalties)
│   │   ├── optimizer.py                    # AI resume optimization (indexed operations, safe-only apply)
│   │   ├── cover_letter.py                 # AI cover letter generation + fact checking
│   │   ├── resume_parser.py                # Heuristic + AI resume parsing
│   │   ├── fact_guard.py                   # Deterministic fact validation (SequenceMatcher, semantic reversals)
│   │   ├── parser_fact_guard.py            # Parser-specific hallucination detection
│   │   ├── document_reader.py              # PDF/DOCX/TXT extraction (page/compression limits)
│   │   ├── job_fetcher.py                  # URL fetch orchestrator with SSRF protection
│   │   ├── browser_fetcher.py              # Playwright headless Chromium for JS-heavy sites
│   │   ├── security.py                     # SSRF protection: DNS, port blocking, IP validation
│   │   ├── html_extractor.py               # HTML text extraction, noise filtering
│   │   ├── metadata.py                     # Title/company/location extraction from HTML
│   │   ├── salary_estimator.py             # AI salary estimation with DI, experience calc, benchmark integration
│   │   ├── skill_gap.py                    # AI skill gap analysis
│   │   ├── diff_highlight.py               # HTML diff (word-level and bullet-level)
│   │   ├── auto_fit.py                     # Binary search font/spacing scale for page target
│   │   ├── bullet_writer.py                # AI bullet writer (3 alternatives from evidence)
│   │   ├── keyword_targeting.py            # Deterministic keyword requirement matching
│   │   ├── job_context.py                  # Bounded JD context for AI prompts (max 12k chars)
│   │   ├── summary_generator.py            # AI standalone summary generation
│   │   ├── headline_generator.py           # AI standalone headline generation
│   │   ├── agent.py                        # AgentService.propose() pipeline (7 tools, FactGuard validation)
│   │   ├── interview_prep.py               # AI interview question generation (behavioral/technical/situational)
│   │   ├── linkedin_import.py              # LinkedIn JSON/CSV profile import
│   │   ├── backup.py                       # Database backup & restore (export/import with integrity check)
│   │   ├── global_search.py                # Cross-entity full-text search (resumes, jobs, cover letters, applications)
│   │   ├── resume_comparison.py            # Structured side-by-side resume diff
│   │   ├── score_history.py                # Score snapshot persistence for trend tracking
│   │   ├── evidence_vault.py               # Evidence storage, source tracking, categorization
│   │   ├── content_checker.py              # 23-factor content quality scoring
│   │   ├── career_embeddings.py            # Semantic embeddings for career data
│   │   ├── career_search.py                # Semantic career search (embeddings + keywords)
│   │   ├── profile_compiler.py             # Resume compilation from master profile
│   │   ├── requirement_matrix.py           # JD requirement comparison matrix
│   │   ├── skill_explorer.py               # Skill taxonomy and exploration
│   │   ├── resume_scorer.py                # Comprehensive resume scoring
│   │   └── discovery.py                    # Discovery interview session management
│   │
│   ├── exports/
│   │   ├── __init__.py
│   │   └── exporter.py                     # Deterministic DOCX/PDF/Markdown export
│   │
│   ├── config/                             # Legacy compatibility layer
│   │   ├── __init__.py
│   │   ├── config_manager.py
│   │   ├── config.json
│   │   └── settings.json
│   │
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py                  # QMainWindow with sidebar nav + QStackedWidget (20 pages)
│       ├── state.py                        # AppState (resume, job, ats, pipeline, skill_gap, salary_estimate, keywords, cancel)
│       ├── workers.py                      # Worker + PipelineWorker (QThread) + cooperative cancellation + _MISSING sentinel
│       ├── theme.py                        # ResumeAI_COLORS + DARK_STYLESHEET + LIGHT_STYLESHEET
│       ├── undo_stack.py                   # UndoStack for resume edits
│       │
│       ├── components/
│       │   ├── __init__.py
│       │   ├── ollama_status.py            # OllamaCheckerThread + OllamaStatusLabel (stale guard)
│       │   ├── loading_overlay.py          # LoadingOverlay + LoadingOverlayManager (resize-aware)
│       │   ├── section_editor.py           # Dynamic form for resume sections (None-safe)
│       │   ├── section_navigator.py        # Left panel section list
│       │   ├── resume_preview.py           # Read-only text preview
│       │   ├── resume_insights_panel.py    # Score cards, keywords, issues
│       │   ├── resume_review_panel.py      # Editable review panel for section editing
│       │   ├── bullet_writer_widget.py     # 3-alternative bullet generation widget
│       │   ├── agent_proposal_card.py      # Agent proposal card (original vs proposed, Accept/Reject)
│       │   │
│       │   └── resumeai/                   # ResumeAI design system components
│       │       ├── __init__.py             # Exports: RESUMEAI_COLORS, RESUMEAI_FONT_FAMILY, resumeai_font()
│       │       ├── sidebar.py              # ResumeAiSidebar: icon nav with tooltips
│       │       ├── top_nav.py              # ResumeAiTopNav: top bar with section tabs + resume dropdown
│       │       ├── section_tabs.py         # SectionTabs + PillCheckBox: horizontal tab bar
│       │       ├── section_menu.py         # SectionMenu: floating section visibility menu
│       │       ├── toggle_switch.py        # ToggleSwitch: iOS-style toggle
│       │       ├── form_field.py           # FormField: labeled input with error state
│       │       ├── dropdown.py             # Dropdown: styled QComboBox
│       │       ├── card.py                 # Card: rounded-corner container
│       │       └── toast.py                # Toast: slide-in notification
│       │
│       ├── dialogs/
│       │   └── onboarding.py               # First-launch onboarding wizard (3-step)
│       │
│       ├── view_models/
│       │   ├── __init__.py
│       │   └── studio_vm.py                # ResumeStudioViewModel (MVVM)
│       │
│       └── pages/
│           ├── __init__.py
│           ├── dashboard.py                # One-click pipeline, score cards, recent table
│           ├── resume_upload.py            # PDF/DOCX import + parse + save
│           ├── job_description.py          # Paste/upload/URL fetch + save + sequential analysis trigger
│           ├── ats_analysis.py             # Score cards, keyword heatmap, suggestions
│           ├── optimization.py             # Before/after ATS comparison, Accept/Reject
│           ├── studio.py                   # Resume Studio: 3-panel MVVM editor
│           ├── agent.py                    # AI agent chat interface (multi-turn, 7 tools)
│           ├── cover_letter.py             # AI cover letter + fact-check warnings
│           ├── skill_gap.py                # Skill gap analysis (analysis_finished signal)
│           ├── salary_estimate.py          # Salary estimation (analysis_finished signal)
│           ├── applications.py             # Application tracker with analytics dashboard
│           ├── cover_letter_library.py     # Cover letter library (search, browse, copy, delete)
│           ├── interview_prep.py           # Interview question generator
│           ├── import_linkedin.py          # LinkedIn JSON/CSV import
│           ├── comparison.py               # Resume comparison view (side-by-side diff)
│           ├── evidence_vault.py           # Evidence Vault: save and organize supporting evidence
│           ├── master_profile.py           # Master Profile: consolidated career summary
│           ├── requirement_matrix.py       # Requirement Matrix: JD requirement comparison
│           ├── discovery.py                # Discovery Interview: structured prep session
│           ├── resumeai_contact.py         # ResumeAI contact page
│           └── resumeai_placeholder.py     # Placeholder pages for ResumeAI sections
│
├── tests/                                  # 877 tests across 43 test files
│   ├── __init__.py
│   ├── test_agent.py                       # Agent domain, repository, service, UI
│   ├── test_ats_engine.py                  # ATS scoring, keyword extraction, skill matching
│   ├── test_backup.py                      # Backup & restore, integrity check, listing
│   ├── test_browser_fetcher.py             # Browser fetcher tests
│   ├── test_bullet_writer.py               # 3-alternative bullet generation, undo stack
│   ├── test_career_search.py               # Career semantic search tests
│   ├── test_comparison.py                  # Resume comparison service
│   ├── test_cover_letter.py                # Fact checking, tuple warnings, DI
│   ├── test_cv_import_regressions.py       # CV import regression tests
│   ├── test_diff_highlight.py              # Side-by-side diff rendering
│   ├── test_discovery.py                   # Discovery interview tests
│   ├── test_document_reader.py             # PDF/DOCX/TXT extraction limits
│   ├── test_evidence_vault.py              # Evidence vault tests
│   ├── test_exporter.py                    # Markdown export structure
│   ├── test_fact_guard.py                  # Normalization, entities, skills, changes
│   ├── test_global_search.py               # Cross-entity search
│   ├── test_job_fetcher.py                 # SSRF protection, HTML extraction, metadata
│   ├── test_keyword_targeting.py           # Keyword requirement matching
│   ├── test_master_profile.py              # Master profile tests
│   ├── test_migrations.py                  # Schema, backup, restore, cascade delete, FK
│   ├── test_ollama_cancellation.py         # Cancellation, streaming cancel, no retry
│   ├── test_ollama_client.py               # Ollama client, circuit breaker
│   ├── test_onboarding.py                  # Onboarding wizard navigation and settings
│   ├── test_optimizer.py                   # Safe-only apply, accepted changes
│   ├── test_p0_regression.py               # P0 regression tests
│   ├── test_parser.py                      # Resume parsing
│   ├── test_parser_fact_guard.py           # Parser hallucination detection
│   ├── test_parser_fallback.py             # OllamaError fallback, edge cases
│   ├── test_phase6.py                      # Application tracker, cover letter library, variants, LinkedIn import, interview prep
│   ├── test_phase9.py                      # Phase 9 tests
│   ├── test_post_processor.py              # AI text post-processing
│   ├── test_profile_compiler.py            # Profile compiler tests
│   ├── test_requirement_matrix.py          # Requirement matrix tests
│   ├── test_salary_estimator.py            # Experience calculation, DI, benchmark integration
│   ├── test_scoring_engine.py              # Versioned rule engine scoring
│   ├── test_settings.py                    # Atomic write, backup, recovery, concurrency
│   ├── test_skill_gap.py                   # Skill gap analysis
│   ├── test_skill_gap_salary.py            # Skill gap + salary estimation
│   ├── test_studio.py                      # Studio ViewModel, components
│   ├── test_studio_review.py               # Studio review panel tests
│   ├── test_templates.py                   # Template manifests, auto-fit
│   ├── test_versioning.py                  # Resume versions, targeting, suggestions
│   └── test_workers.py                     # Worker timeout, cancellation, signals
```

---

## 9. DATABASE

### ORM Models (20+ tables)

| Table                 | Purpose                                                         |
| --------------------- | --------------------------------------------------------------- |
| resumes               | Resume metadata (name, target role)                             |
| resume_versions       | Immutable snapshots with version_number                         |
| job_descriptions      | Job posting data (title, content)                               |
| analyses              | ATS analysis results                                            |
| optimizations         | Optimization run records                                        |
| cover_letters         | Generated cover letters                                         |
| cover_letter_versions | Cover letter snapshots                                          |
| skill_gap_runs        | Skill gap analysis runs                                         |
| salary_estimate_runs  | Salary estimation runs                                          |
| ai_runs               | AI operation audit trail                                        |
| interview_sessions    | Interview prep sessions                                         |
| interview_questions   | Generated interview questions                                   |
| job_applications      | Application tracker (draft → applied → interview → offer/rejected) |
| template_preferences  | Per-resume template choices                                     |
| targeting_sessions    | Resume-to-job targeting records                                 |
| suggestion_records    | Keyword suggestion accept/reject state                          |
| agent_conversations   | AI agent conversation metadata                                  |
| agent_messages        | Agent conversation messages (JSON proposals)                    |
| score_snapshots       | ATS score history for trend tracking                            |
| schema_metadata       | Migration version tracking                                      |

### Database Requirements

* Foreign-key enforcement enabled via `PRAGMA foreign_keys=ON`
* WAL mode enabled via `PRAGMA journal_mode=WAL`
* Busy timeout 5000ms via `PRAGMA busy_timeout=5000`
* Automatic migrations via Alembic (6 migration scripts)
* Backup before destructive migrations
* Connection via `get_session()` context manager with rollback

---

## 10. NAVIGATION

### Sidebar Navigation (icon index → page)

| Icon Index | Page Name         | Class                | Responsibility                                      |
| ---------- | ----------------- | -------------------- | --------------------------------------------------- |
|          0 | Resume Upload     | `ResumeUploadPage`   | Import PDF/DOCX, parse, save                        |
|          1 | Dashboard         | `DashboardPage`      | One-click pipeline, score cards, recent analyses    |
|          2 | Optimization      | `OptimizationPage`   | Before/after ATS comparison, AI diff, Accept/Reject |
|          3 | Resume Studio     | `ResumeStudioPage`   | 3-panel MVVM editor with section tabs               |
|          4 | Cover Letter      | `CoverLetterPage`    | Generate tailored cover letter via AI               |
|          5 | Applications      | `ApplicationsPage`   | Application tracker with analytics dashboard        |
|          6 | Settings          | `SettingsPage`       | Ollama URL, model, temperature, theme, backup/restore |

### Full Page Stack (20 pages)

| Stack Index | Page Name             | Class                    | Responsibility                                              |
| ----------- | --------------------- | ------------------------ | ----------------------------------------------------------- |
|           0 | Dashboard             | `DashboardPage`          | One-click pipeline, score cards, recent analyses            |
|           1 | Resume Upload         | `ResumeUploadPage`       | Import PDF/DOCX, parse, save                                |
|           2 | Job Description       | `JobDescriptionPage`     | Paste, upload, or fetch job description from URL            |
|           3 | ATS Analysis          | `ATSAnalysisPage`        | Keyword heatmap, score cards, suggestions                   |
|           4 | Optimization          | `OptimizationPage`       | Before/after ATS comparison, AI diff, Accept/Reject         |
|           5 | Resume Studio         | `ResumeStudioPage`       | 3-panel MVVM editor with section tabs                       |
|           6 | Agent                 | `AgentPage`              | AI agent chat interface, multi-turn conversations, 7 tools  |
|           7 | Cover Letter          | `CoverLetterPage`        | Generate tailored cover letter via AI                       |
|           8 | Skill Gap             | `SkillGapPage`           | Match skills vs market demand, learning recommendations     |
|           9 | Salary Estimate       | `SalaryEstimatePage`     | Salary range estimation via AI                              |
|          10 | Applications          | `ApplicationsPage`       | Application tracker with analytics dashboard                |
|          11 | Cover Letter Library  | `CoverLetterLibraryPage` | Browse, search, copy, and delete saved cover letters        |
|          12 | Interview Prep        | `InterviewPrepPage`      | Generate behavioral/technical/situational questions         |
|          13 | LinkedIn Import       | `LinkedInImportPage`     | Import LinkedIn JSON/CSV profile data                       |
|          14 | Compare Resumes       | `ComparisonPage`         | Side-by-side structured diff between two resumes            |
|          15 | Evidence Vault        | `EvidenceVaultPage`      | Save and organize supporting evidence                       |
|          16 | Master Profile        | `MasterProfilePage`      | Consolidated career summary                                 |
|          17 | Requirement Matrix    | `RequirementMatrixPage`  | JD requirement comparison                                   |
|          18 | Discovery Interview   | `DiscoveryPage`          | Structured interview prep session                           |
|          19 | Settings              | `SettingsPage`           | Ollama URL, model, temperature, theme, backup/restore       |

### Section Tabs (Resume Studio sections)

| Tab Name         | Studio Destination | Page Key                |
| ---------------- | ------------------ | ----------------------- |
| CONTACT          | Contact            | `resumeai_contact`      |
| EXPERIENCE       | Experience         | `resumeai_experience`   |
| PROJECT          | Project            | `resumeai_project`      |
| EDUCATION        | Education          | `resumeai_education`    |
| CERTIFICATIONS   | Certifications     | `resumeai_certifications`|
| COURSEWORK       | Coursework         | `resumeai_coursework`   |
| INVOLVEMENT      | Involvement        | `resumeai_involvement`  |
| SKILLS           | Skills             | `resumeai_skills`       |
| SUMMARY          | Summary            | `resumeai_summary`      |

### Global Search

A search bar in the sidebar nav (above the page list) provides cross-entity search across resumes, jobs, cover letters, and applications. Clicking a result navigates to the corresponding page.

### Keyboard Shortcuts

| Shortcut         | Action                          |
| ---------------- | ------------------------------- |
| Ctrl+S           | Force save current page         |
| Ctrl+E           | Export current resume           |
| Ctrl+N           | New resume                      |
| Escape           | Dismiss overlay / close popup   |

---

## 11. BACKGROUND_WORKERS

### Worker Classes

```text
Worker(QThread)           — generic background task with timeout
PipelineWorker(QThread)   — full optimization pipeline with progress
CancellationToken         — threading.Event wrapper for cooperative cancel
OllamaCheckerThread       — periodic Ollama health check (stale-response guard)
```

### Worker._emit_once Pattern

```text
Worker._emit_once(signal, value)
    → If value is _MISSING sentinel: signal.emit() (no args)
    → Otherwise: signal.emit(value)
    → Prevents NoneType crash when service returns None
```

### Cancellation Model

```text
User clicks Cancel
    → PipelineWorker.cancel()
    → CancellationToken.cancel()  (sets threading.Event)
    → OllamaClient._check_cancelled()  (checked per streaming line)
    → OllamaCancelledError raised
    → OperationCancelled propagated
    → Worker cancelled signal emitted
```

Key guarantees:
* Never calls `QThread.terminate()`
* Each Worker has its own CancellationToken (not global)
* Cancel event is passed through to OllamaClient via `set_cancel_event()`
* Cancelled requests are not retried

### Sequential Analysis Chain

```text
JobDescriptionPage._trigger_analyses()
    → Pre-fills SkillGap and Salary Estimate input fields
    → Runs ATS analysis immediately
    → Connects SkillGap.analysis_finished → SalaryEstimate.run_analysis (SingleShotConnection)
    → Each run_analysis() returns bool (False = skipped, triggers next immediately)
    → analysis_finished emitted in both _on_done and _on_error (try/finally)
```

---

## 12. SECURITY

### SSRF Protection

```text
URL input
    → validate_scheme() — http/https only
    → validate_port() — blocks 21,22,23,25,110,135,139,445,1433,3306,3389,5432,5900,6379,6443,11211,27017
    → resolve_and_validate() — DNS resolution, rejects private/reserved/loopback/multicast IPs
    → Browser route handler (_secure_route) enforces same checks on every subrequest
    → Blocks image/media/font resource types in browser
```

### Document Limits

```text
MAX_DOCUMENT_BYTES     = 15 MB
MAX_PDF_PAGES          = 60
MAX_DOCX_EXPANDED_BYTES = 75 MB
MAX_DOCX_COMPRESSION_RATIO = 100
MAX_AI_PARSE_CHARACTERS = 40,000
```

---

## 13. TEST_STRATEGY

### Test Count: 877 tests across 43 test files

| Test File                         | Focus                                                      |
| --------------------------------- | ---------------------------------------------------------- |
| test_agent.py                     | Agent domain, repository, service, UI                      |
| test_ats_engine.py                | ATS scoring, keyword extraction, skill matching            |
| test_backup.py                    | Backup & restore, integrity check, listing                 |
| test_browser_fetcher.py           | Browser fetcher tests                                      |
| test_bullet_writer.py             | 3-alternative bullet generation, undo stack                |
| test_career_search.py             | Career semantic search tests                               |
| test_comparison.py                | Resume comparison service                                  |
| test_cover_letter.py              | Fact checking, tuple warnings, DI                          |
| test_cv_import_regressions.py     | CV import regression tests                                 |
| test_diff_highlight.py            | Side-by-side diff rendering                                |
| test_discovery.py                 | Discovery interview tests                                  |
| test_document_reader.py           | PDF/DOCX/TXT extraction limits                             |
| test_evidence_vault.py            | Evidence vault tests                                       |
| test_exporter.py                  | Markdown export structure                                  |
| test_fact_guard.py                | Normalization, entities, skills, changes                   |
| test_global_search.py             | Cross-entity search                                        |
| test_job_fetcher.py               | SSRF protection, HTML extraction, metadata                 |
| test_keyword_targeting.py         | Keyword requirement matching                               |
| test_master_profile.py            | Master profile tests                                       |
| test_migrations.py                | Schema, backup, restore, cascade delete, FK                |
| test_ollama_cancellation.py       | Cancellation, streaming cancel, no retry                   |
| test_ollama_client.py             | Ollama client, circuit breaker                             |
| test_onboarding.py                | Onboarding wizard navigation and settings                  |
| test_optimizer.py                 | Safe-only apply, accepted changes                          |
| test_p0_regression.py             | P0 regression tests                                        |
| test_parser.py                    | Resume parsing                                             |
| test_parser_fact_guard.py         | Parser hallucination detection                             |
| test_parser_fallback.py           | OllamaError fallback, edge cases                           |
| test_phase6.py                    | Application tracker, cover letter library, variants, LinkedIn import, interview prep |
| test_phase9.py                    | Phase 9 tests                                              |
| test_post_processor.py            | AI text post-processing                                    |
| test_profile_compiler.py          | Profile compiler tests                                     |
| test_requirement_matrix.py        | Requirement matrix tests                                   |
| test_salary_estimator.py          | Experience calculation, DI, benchmark integration          |
| test_scoring_engine.py            | Versioned rule engine scoring                              |
| test_settings.py                  | Atomic write, backup, recovery, concurrency                |
| test_skill_gap.py                 | Skill gap analysis                                         |
| test_skill_gap_salary.py          | Skill gap + salary estimation                              |
| test_studio.py                    | Studio ViewModel, components                               |
| test_studio_review.py             | Studio review panel tests                                  |
| test_templates.py                 | Template manifests, auto-fit                               |
| test_versioning.py                | Resume versions, targeting, suggestions                    |
| test_workers.py                   | Worker timeout, cancellation, signals                      |

### Quality Gates

```bash
ruff check app/ tests/        # Lint
mypy app/ --ignore-missing-imports  # Type check
pytest --cov=app --cov-report=term-missing  # Tests + coverage
bandit -r app/ -c pyproject.toml  # Security scan
pip-audit                     # Dependency audit
```

---

## 14. IMPLEMENTATION_ROADMAP

All 33 tasks across 6 phases are **complete**. See `tasks/plan.md` for the original plan.

### Phase 1: Regression Tests + Tooling ✅

* [x] Task 1: Set up dev tooling (ruff, mypy, pytest-cov, bandit, pip-audit)
* [x] Task 2: CI workflow (Windows, macOS, Linux)
* [x] Tasks 3-10: Regression tests

### Phase 2: Resume Studio Completion ✅

* [x] Auto-save (2s debounce)
* [x] Resume duplication (deep copy with "(Copy)" suffix)
* [x] Resume versions UI (save version button)
* [x] Section reorder and rename
* [x] Click issue to navigate to field

### Phase 3: Targeting & Writing Tools ✅

* [x] Standalone summary generator
* [x] Standalone headline generator
* [x] Skill suggestions UI (accept/reject)
* [x] Side-by-side diff
* [x] One-click rollback to original

### Phase 4: Templates & Export ✅

* [x] Live template switching (7 presets)
* [x] Page target UI (auto-fit binary search)
* [x] Template-aware PDF/DOCX export
* [x] Export validation

### Phase 5: AI Agent ✅

* [x] Agent tool definitions (7 tools)
* [x] Agent service — proposal pipeline with FactGuard
* [x] Agent UI — chat-style interface with proposal cards
* [x] Agent repository (conversation + message CRUD)
* [x] Multi-turn agent conversations

### Phase 6: Broader Career Features ✅

* [x] Application tracker (workflow: draft → applied → interview → offer/rejected)
* [x] Cover-letter library (search, browse, copy, delete)
* [x] Job-specific resume variants (create_variant)
* [x] Interview question generator (behavioral/technical/situational)
* [x] LinkedIn data import (JSON + CSV)

### Phase 7: Evidence Vault & Master Profile ✅

* [x] Evidence Vault (save, organize, source tracking)
* [x] Master Profile (consolidated career summary)
* [x] Evidence repository + source repository
* [x] Master profile repository
* [x] Database migrations (0005, 0006)

### Phase 8: Export & Templates ✅

* [x] Export theme system
* [x] Page auto-resizer
* [x] Studio export UI

### Phase 9: AI Content Engine ✅

* [x] Content checker (23-factor scoring)
* [x] Skill explorer (taxonomy and exploration)
* [x] Resume scorer (comprehensive scoring)

### ResumeAI UI Overhaul ✅

* [x] Dark navy theme (RESUMEAI_COLORS palette)
* [x] ResumeAI design system (sidebar, top_nav, section_tabs, toggle_switch, form_field, dropdown, card, toast, section_menu)
* [x] Section tabs with pill checkboxes
* [x] Floating section visibility menu
* [x] Sequential analysis chain (analysis_finished signal pattern)
* [x] Pipeline result display on destination pages
* [x] Ollama checker lifecycle fix (stale guard, single-shot cleanup)
* [x] Worker._emit_once None-safety fix (_MISSING sentinel)
* [x] ATS multi-word keyword highlighting
* [x] Cover Letter, Skill Gap, Salary Estimate pipeline result caching

### New Features ✅

* [x] Career embeddings (semantic search)
* [x] Career search (embeddings + keywords)
* [x] Profile compiler (resume from master profile)
* [x] Requirement matrix (JD requirement comparison)
* [x] Discovery interview (structured prep session)
* [x] Salary benchmark data service
* [x] Editable review panel in Studio
* [x] Resume scorer
* [x] Content checker

### Future Enhancements ✅

* [x] Keyboard shortcuts (Ctrl+S, Ctrl+E, Ctrl+N, Escape)
* [x] Score history tracking (ScoreSnapshot after each optimization)
* [x] Application analytics dashboard (total, applied, interviews, offers, rejected)
* [x] Backup & restore (export/import DB with integrity check)
* [x] Resume comparison view (structured side-by-side diff)
* [x] Global search (cross-entity search with result navigation)
* [x] Onboarding wizard (3-step first-launch flow)

---

## 15. DEFINITION_OF_DONE

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
* `ruff check` passes clean
* All tests pass with `pytest`
