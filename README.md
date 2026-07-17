# Resume Optimizer

A local, offline, AI-powered desktop application for ATS resume optimization and tailoring - a lightweight alternative to Rezi.ai. All processing happens on your machine: parsing, scoring, and AI rewriting via [Ollama](https://ollama.com). No cloud, no accounts, no data leaves your computer.

## Features

- **Resume import**: PDF, DOCX, TXT - parsed into structured JSON (contact, summary, skills, experience, education, certifications, projects)
- **Job description input**: paste text, upload PDF/DOCX, or fetch from URL (with SSRF protection)
- **ATS analysis**: deterministic score (0-100), keyword match %, skills match %, heatmap, missing keywords, improvement suggestions
- **AI optimization**: rewrites your summary and experience bullets to improve keyword coverage and grammar - facts, employers, dates and certifications are never invented or altered
- **Per-change review**: accept or reject each AI suggestion individually; fact guard detects unsupported claims
- **Skill gap analysis**: matches your skills against job requirements with learning recommendations
- **Salary estimation**: AI-based salary range estimation with explicit data-source disclaimer
- **Cover letter generator**: tailored letter from your resume + the job description, with fact-check warnings
- **One-click pipeline**: runs ATS analysis → optimization → cover letter in sequence with progress tracking
- **Export**: DOCX, PDF and Markdown
- **Model support**: `qwen3` and `llama3.1` (or any Ollama model), selectable in Settings
- **Local SQLite database**: resumes, job descriptions, ATS scores and optimization history
- **Modern UI** with Dashboard, Resume Upload, Job Description, ATS Analysis, Optimization, Cover Letter, Skill Gap, Salary, and Settings pages

## Requirements

- Python 3.12+
- [Ollama](https://ollama.com) installed and running locally

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Pull at least one model
ollama pull qwen3
ollama pull llama3.1             # optional
```

## Run

```bash
python main.py
```

Typical workflow:

1. **Resume Upload** - import your PDF/DOCX (optionally with AI parsing) and save it
2. **Job Description** - paste or upload the target posting and save it
3. **ATS Analysis** - run the analysis to get your score, missing keywords and suggestions
4. **Optimization** - let the AI rewrite your summary and bullets, then export to DOCX/PDF/Markdown
5. **Cover Letter** - generate and save a tailored cover letter

## Tests

```bash
pytest
```

## Project structure

```
main.py                  # entry point
app/
  core/
    settings.py          # typed Pydantic AppSettings + SettingsService singleton
    paths.py             # DB_PATH, CONFIG_PATH, LOG_DIR
  domain/
    resume.py            # ContactInfo, ExperienceItem, EducationItem, ProjectItem, ResumeData
    analysis.py          # ATSResult domain model
    skill_gap.py         # SkillGapItem, SkillGapResult
    salary.py            # SalaryEstimate (Decimal fields)
    fact_guard.py        # ChangeType, ProposedChange, FactGuardResult
    pipeline.py          # PipelineResult dataclass
    job_requirements.py  # JobRequirements domain model
  ai/
    ollama_client.py     # OllamaClient: generate, generate_json, pre_warm, cancel
    prompts.py           # all prompt templates
  database/
    engine.py            # SQLAlchemy SQLite engine
    session.py           # get_session() context manager
    models.py            # Resume, JobDescription, Analysis ORM
    db.py                # backward-compatible CRUD facade
    migrate.py           # Alembic migration helper
    repositories/        # base, resume, job, analysis repositories
  application/
    import_resume.py     # ImportResumeUseCase
    analyze_resume.py    # AnalyzeResumeUseCase
    optimize_resume.py   # OptimizeResumeUseCase + RunPipelineUseCase
  services/
    ats_engine.py        # ATS keyword analysis + scoring
    optimizer.py         # AI resume optimization (safe-only apply + fact guard)
    cover_letter.py      # AI cover letter generation + fact checking
    resume_parser.py     # heuristic + AI resume parsing
    fact_guard.py        # deterministic fact validation (SequenceMatcher)
    job_fetcher.py       # URL fetch with SSRF protection
    document_reader.py   # PDF/DOCX/TXT text extraction
    salary_estimator.py  # AI salary estimation
    skill_gap.py         # AI skill gap analysis
    diff_highlight.py    # HTML diff between original and optimized
    exporter.py          # DOCX/PDF/Markdown export
  ui/
    main_window.py       # QMainWindow with sidebar nav + stack
    state.py             # AppState (resume, job, ats, pipeline, keywords, cancel)
    workers.py           # Worker + PipelineWorker (QThread) + global cancel
    theme.py             # DARK_STYLESHEET + LIGHT_STYLESHEET
    components/
      ollama_status.py   # OllamaCheckerThread + OllamaStatusLabel
      loading_overlay.py # LoadingOverlay + LoadingOverlayManager
    pages/
      dashboard.py       # one-click pipeline, score cards
      resume_upload.py   # PDF/DOCX import + parse + save
      job_description.py # paste/upload/URL fetch + save
      ats_analysis.py    # score cards, keyword heatmap, suggestions
      optimization.py    # before/after ATS comparison, Accept/Reject
      cover_letter.py    # AI cover letter + fact-check warnings
      skill_gap.py       # skill gap analysis with disclaimer
      salary_estimate.py # salary estimation with disclaimer
      settings.py        # Ollama URL, model, temperature, theme
tests/                   # 156 tests across 11 test files
  test_ats_engine.py     # 15 tests
  test_cover_letter.py   # 11 tests
  test_exporter.py       #  2 tests
  test_fact_guard.py     # 22 tests
  test_job_fetcher.py    # 30 tests (SSRF protection)
  test_migrations.py     # 23 tests
  test_optimizer.py      #  7 tests
  test_parser.py         #  4 tests
  test_parser_fallback.py#  8 tests
  test_settings.py       # 29 tests
  test_skill_gap_salary.py# 5 tests
```

User data (SQLite database and settings) is stored in `~/.resume_optimizer/`.

## Build a desktop executable (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --name ResumeOptimizer --windowed --onefile main.py
```

The executable is written to `dist/`. Notes:

- If Qt plugins are missing at runtime, add `--collect-all PySide6`
- If PyMuPDF resources are missing, add `--collect-all fitz`
- Ollama is a separate service and is **not** bundled - it must be installed and running on the target machine

## Configuration

Open the **Settings** page to change:

- **Ollama URL** (default `http://localhost:11434`)
- **Model** (default `qwen3`; click *Refresh Models* to list everything installed in Ollama)
- **Temperature** (default `0.3`)
