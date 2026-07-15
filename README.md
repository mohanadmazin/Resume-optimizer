# Resume Optimizer

A local, offline, AI-powered desktop application for ATS resume optimization and tailoring - a lightweight alternative to Rezi.ai. All processing happens on your machine: parsing, scoring, and AI rewriting via [Ollama](https://ollama.com). No cloud, no accounts, no data leaves your computer.

## Features

- **Resume import**: PDF and DOCX, parsed into structured JSON (contact, summary, skills, experience, education, certifications)
- **Job description input**: paste text or upload PDF/DOCX
- **ATS analysis**: score (0-100), keyword match %, skills match %, missing keywords, improvement suggestions
- **AI optimization**: rewrites your summary and experience bullets to improve keyword coverage and grammar - facts, employers, dates and certifications are never invented or altered
- **Job match analysis**: match %, missing skills and keywords, recommendations
- **Cover letter generator**: tailored letter from your resume + the job description
- **Export**: DOCX, PDF and Markdown
- **Model support**: `qwen3` and `llama3.1` (or any Ollama model), selectable in Settings
- **Local SQLite database**: resumes, job descriptions, ATS scores and optimization history
- **Modern dark-theme UI** with Dashboard, Resume Upload, Job Description, ATS Analysis, Optimization, Cover Letter and Settings pages

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
  config.py              # settings stored in ~/.resume_optimizer/config.json
  schemas.py             # Pydantic models for structured resume data
  ai/                    # Ollama client and prompt templates
  database/              # SQLAlchemy schema + CRUD helpers (SQLite)
  services/              # document reader, resume parser, ATS engine, optimizer, cover letter
  exports/               # DOCX / PDF / Markdown exporters
  ui/                    # PySide6 dark-theme UI (pages, workers, theme)
tests/                   # pytest suite (parser, ATS engine, exporter)
```

User data (SQLite database and config) is stored in `~/.resume_optimizer/`.

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
