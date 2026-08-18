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
| Document size/page limits             | ✅      |
| Cooperative worker cancellation      | ✅      |
| Streaming Ollama client              | ✅      |
| Fact guard (semantic reversals)       | ✅      |
| Fact guard (deleted bullets)          | ✅      |
| Fact guard (negation detection)       | ✅      |
| Indexed bullet rewrites               | ✅      |
| Cover-letter fact-check warnings      | ✅      |
| Cover-letter target employer exempt   | ✅      |
| Salary experience calculation (DI)    | ✅      |
| Dev tooling (ruff, mypy, bandit)      | ✅      |
| CI workflow (Win/Mac/Linux)           | ✅      |
| Auto-save                             | ✅      |
| Resume duplication                    | ✅      |
| Section reorder and rename            | ✅      |
| Click issue to navigate to field      | ✅      |
| Live template switching               | ✅      |
| Export validation                     | ✅      |
| Keyboard shortcuts (Ctrl+S, etc.)     | ✅      |
| AI agent workflow                     | ✅      |
| Multi-turn agent conversations        | ✅      |
| Application tracker                   | ✅      |
| Interview preparation                 | ✅      |
| Job-specific resume variants          | ✅      |
| LinkedIn data import                  | ✅      |
| Score history tracking                | ✅      |
| Application analytics dashboard       | ✅      |
| Backup and restore                    | ✅      |
| Resume comparison view                | ✅      |
| Global search                         | ✅      |
| Onboarding wizard                     | ✅      |
| Evidence Vault (save evidence)        | ✅      |
| Master Profile (career summary)       | ✅      |
| Requirement Matrix (JD comparison)    | ✅      |
| Discovery Interview (prep session)    | ✅      |
| ResumeAI contact page                 | ✅      |
| Content checker (23-factor scoring)   | ✅      |
| Career embeddings (semantic search)   | ✅      |
| Profile compiler (resume from profile) | ✅     |
| Skill explorer                        | ✅      |
| Resume scorer                          | ✅      |
| FastAPI web interface (`web_main.py`) | ✅      |
| Web dashboard with resume, jobs, ATS, optimize, cover letter, applications | ✅ |
| Web resignation letter generator      | ✅      |
| Web DOCX export (same template as optimize endpoint) | ✅ |
| Encrypted sensitive fields (optional) | 🔭      |
| Data export/delete (privacy)           | 🔭      |
| Job discovery/search                   | 🔭      |
| Job matching against Master Profile   | 🔭      |
| Saved searches                         | 🔭      |
| Career progression dashboard           | 🔭      |
| Skill development roadmap              | 🔭      |
| Market-demand trends                   | 🔭      |
| Salary trend history                   | 🔭      |
| Resume A/B comparison experiment       | 🔭      |
| Web/desktop feature parity             | 🔭      |
| Portable career-profile import/export  | 🔭      |
| Optional job-board integrations        | 🔭      |

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
| FastAPI        | Compatible 0.115.x     | Web API for the browser interface     |
| uvicorn        | Compatible 0.34.x      | ASGI server for the web app           |
| Jinja2         | Compatible 3.1.x       | HTML templating for the web app       |
| python-multipart| Compatible 0.0.18     | Multipart form parsing (web uploads)  |

### Dev Tooling

| Package    | Purpose                            | Status |
| ---------- | ---------------------------------- | ------ |
| pytest     | Automated testing                  | ✅      |
| pytest-cov | Coverage reporting                 | ✅      |
| pytest-qt  | Qt GUI testing                     | ✅      |
| ruff       | Linting and formatting (pinned 0.15.*) | ✅  |
| mypy       | Static type checking               | ✅      |
| bandit     | Security scanning                  | ✅      |
| pip-audit  | Dependency vulnerability scanning  | ✅      |
| playwright | Browser fetching (SSRF-safe) + web e2e | ✅  |

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
               │
               ▼
┌────────────────────────────────────────────────────────────┐
│                 FastAPI Web UI (web_main.py)               │
│   Dashboard │ Resumes │ Jobs │ ATS │ Optimize │ Letters    │
│   Applications │ Resignation Letter │ Settings │ Upload    │
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

---

## 6. FUTURE_PLANS

The roadmap intentionally stays within the current **single-user, local-first modular-monolith architecture**. Features that require a fundamentally different multi-user/server deployment model are not treated as near-term roadmap commitments.

### Phase 1 — Reliability, Privacy, and Release Quality

1. **Encrypted sensitive fields** — optionally encrypt especially sensitive local database fields while preserving the local-first model.
2. **Privacy data controls** — add explicit user-facing export, selective deletion, and complete data deletion workflows.
3. **Release automation** — produce versioned, reproducible desktop builds with checksums and clearer upgrade guidance.
4. **CI hardening** — keep Windows/macOS/Linux green, expand web/desktop regression coverage, and keep dependency/security audits automated.
5. **Onboarding and diagnostics** — improve first-run setup, Ollama diagnostics, migration recovery, and actionable error messages.

### Phase 2 — Job Discovery and Matching

6. **Job discovery/search** — build a local job-search domain around normalized job records and imported job descriptions.
7. **Job matching against Master Profile** — score jobs against the user's Master Profile, skills, experience, evidence, and preferences.
8. **Saved searches** — save reusable search criteria, filters, and matching preferences locally.
9. **Optional job-board integrations** — add integrations only where they can be implemented safely and compatibly; imported/manual jobs remain a first-class path.
10. **Job-specific intelligence** — connect job matches to Requirement Matrix, skill gaps, resume variants, cover letters, and application tracking.

### Phase 3 — Career Analytics

11. **Career progression dashboard** — visualize applications, interviews, offers, skills, resume quality, and outcomes over time.
12. **Salary trend history** — retain timestamped benchmark observations and show historical changes with source attribution.
13. **Market-demand trends** — track normalized skill/role demand from supported data sources and expose source/date context.
14. **Skill development roadmap** — turn skill gaps into prioritized development plans and connect them to the user's Master Profile.
15. **Resume A/B comparison experiments** — compare resume variants against deterministic ATS and application outcomes without losing immutable versions.

### Phase 4 — Cross-Interface and Portability

16. **Web/desktop feature parity** — progressively expose existing domain capabilities through the FastAPI web interface while keeping domain logic shared.
17. **Portable career-profile import/export** — define a versioned, privacy-conscious portable format for Master Profile, evidence, skills, preferences, and selected resume metadata.
18. **Shared domain contracts** — keep desktop and web interfaces thin so new capabilities are implemented once in application/domain services.

### Phase 5 — Extensibility

19. **Plugin architecture** — introduce explicit extension points for job sources, ATS scoring rules, exporters, resume templates, AI providers, and career-data providers.
20. **Configurable ATS profiles** — allow industry/job-family-specific scoring weights and rules without changing core scoring code.
21. **Custom resume templates** — support user-created template manifests while retaining validation and export safeguards.
22. **Pluggable AI providers** — preserve Ollama as the local-first default while allowing carefully isolated alternative providers.
23. **Integration adapters** — standardize connectors around explicit permissions, local storage, rate limits, provenance, and failure handling.

### Explicitly Out of Scope for the Current Architecture

The following are **not** planned as native features of the current single-user local-first application because they require a fundamentally different server/deployment and identity model:

- Multi-device synchronization
- Team/reviewer collaboration
- Community template repository
- Community integrations marketplace

They can be reconsidered later as a separate hosted/self-hosted platform architecture rather than being forced into the current desktop-first model.

### Roadmap Principles

- Prefer features that reuse existing domain models and services.
- Keep personal career data local by default.
- Make external integrations optional and explicit.
- Preserve explainable deterministic scoring alongside AI features.
- Never let AI silently overwrite source facts.
- Maintain immutable resume/application history.
- Add migrations and tests before expanding stored-data models.
- Do not introduce a server dependency merely to implement a feature that can remain local.

---

## 7. ARCHITECTURAL_BOUNDARIES

The project should continue to preserve the following boundaries as future features are added:

1. **UI layers** (PySide6 and FastAPI/Jinja) should call application services rather than duplicating domain logic.
2. **Domain engines** should remain deterministic where scoring, validation, privacy, and fact preservation are concerned.
3. **AI infrastructure** should remain replaceable and should never become a hard dependency for core resume operations.
4. **Persistence** should remain local-first and migration-safe.
5. **External integrations** should be isolated behind adapters with explicit provenance and failure handling.
6. **Plugins** should depend on stable interfaces rather than internal implementation details.

The project should not adopt synchronization, collaboration, or community-marketplace infrastructure unless the product explicitly moves to a separate server-capable architecture.
