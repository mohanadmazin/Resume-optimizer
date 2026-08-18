# ResumeAI — Local-First Career Workspace

**Build stronger, evidence-checked resumes and career documents without sending your personal career data to a hosted AI service.**

ResumeAI is a local-first desktop and web workspace for resume building, ATS analysis, evidence-checked optimization, job applications, cover letters, and career documents. It uses SQLite for local storage and optional AI rewriting through Ollama running on your machine.

> **Open source:** ResumeAI is released under the MIT License. Contributions, bug reports, feature ideas, and improvements are welcome.

## ✨ What you can do

- 📄 **Import resumes** from PDF, DOCX, or TXT and parse them into structured data
- 🎯 **Analyze ATS compatibility** with deterministic 0–100 scoring, keyword matching, skills matching, heatmaps, and improvement suggestions
- 🤖 **Optimize resumes with local AI** using Ollama while preserving facts, employers, dates, and certifications
- 🔎 **Review every proposed change** and accept or reject suggestions individually
- 🛡️ **Guard against unsupported claims** with deterministic fact checking
- 🧩 **Find skill gaps** between your resume and a target job
- 💰 **Estimate salary ranges** with an explicit data-source disclaimer
- ✉️ **Generate tailored cover letters** from your resume and job description
- 📋 **Track applications** through wishlist, applied, interview, offer, and outcome stages
- 📝 **Create resignation letters** in English and Bahasa Melayu
- 📤 **Export** to DOCX, PDF, and Markdown
- 🌐 **Use either interface**: PySide desktop app or responsive FastAPI web workspace
- 🔒 **Stay local-first**: career data is stored in a local SQLite database; Ollama can run locally

## 🧭 Typical workflow

```text
Resume → Job Description → ATS Analysis → Optimization → Review → Export
                                      ↘ Cover Letter
                                      ↘ Skill Gap
                                      ↘ Application Tracking
```

1. Import your resume.
2. Add the target job description by pasting, uploading, or fetching a URL.
3. Run ATS analysis to identify strengths and missing keywords.
4. Generate AI optimization suggestions.
5. Review and approve individual changes.
6. Generate a tailored cover letter if needed.
7. Export the approved resume and documents.
8. Track the application in the built-in application tracker.

## 🖥️ Requirements

- Python **3.12+**
- [Ollama](https://ollama.com) installed and running locally for AI features

## 🚀 Quick start

### 1. Clone the repository

```bash
git clone https://github.com/mohanadmazin/Resume-optimizer.git
cd Resume-optimizer
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 3. Install ResumeAI

```bash
python -m pip install --upgrade pip
python -m pip install .
```

### 4. Install an Ollama model

Install Ollama, start it, then pull at least one supported model:

```bash
ollama pull qwen3
# Optional:
ollama pull llama3.1
```

### 5. Install Chromium for optional job-URL fetching

```bash
python -m playwright install chromium
```

## 🖥️ Run the desktop app

```bash
python main.py
```

## 🌐 Run the web app

```bash
python -m pip install -e ".[web]"
python web_main.py
```

Then open `http://127.0.0.1:8080`.

The web server binds to localhost by default.

## 🧪 Development

Install development and browser dependencies:

```bash
python -m pip install -e ".[dev,browser]"
python -m playwright install chromium
```

Run tests:

```bash
pytest
```

Run linting:

```bash
ruff check app/ tests/
```

Run type checking:

```bash
mypy app/ --ignore-missing-imports
```

GitHub Actions runs linting, MyPy, tests on Windows/macOS/Ubuntu, and security/dependency checks.

## 🏗️ Architecture

```text
main.py / web_main.py
        │
        ├── PySide desktop UI
        └── FastAPI web UI
                │
        Application use cases
                │
        Domain models + services
                │
        ├── ATS engine
        ├── Resume parser
        ├── Optimizer + fact guard
        ├── Cover letter generator
        ├── Skill gap analysis
        ├── Salary estimator
        ├── Document exporter
        └── Job fetcher with SSRF protection
                │
        SQLite + Ollama
```

### Main areas

- `app/domain/` — core resume, analysis, salary, skill-gap, and fact-guard models
- `app/application/` — application use cases and pipeline orchestration
- `app/services/` — ATS, parsing, optimization, fetching, exporting, and career services
- `app/ai/` — Ollama client and prompts
- `app/database/` — SQLAlchemy models, sessions, repositories, and migrations
- `app/ui/` — PySide desktop interface
- `web/` — FastAPI/Jinja web interface and shared Resume Builder
- `tests/` — unit, migration, regression, desktop, and web integration tests

## 🔐 Privacy and safety

ResumeAI is designed around a local-first workflow:

- Resume and application data are stored in a local SQLite database.
- Ollama can run locally on your machine.
- Job URL fetching includes SSRF protection.
- AI optimization includes a deterministic fact guard intended to prevent unsupported claims.
- Never commit personal resumes, job applications, API keys, tokens, databases, or browser profiles.

AI-generated salary estimates and other generated content should be independently verified before making career or financial decisions.

## 📁 User data

Application data and settings are stored under:

```text
~/.resume_optimizer/
```

## 🧰 Build a desktop executable

```bash
python -m pip install pyinstaller
pyinstaller --name ResumeOptimizer --windowed --onefile main.py
```

The executable is written to `dist/`.

Ollama is a separate service and is **not** bundled; it must be installed and running on the target machine.

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

Good first contributions include:

- Improving documentation
- Adding or improving tests
- Fixing UI/UX issues
- Improving resume parsing
- Adding ATS analysis improvements
- Improving accessibility
- Adding export formats
- Reporting reproducible bugs

Please remove all personal career information from screenshots, logs, fixtures, and issues before sharing them publicly.

## 📜 License

ResumeAI is licensed under the [MIT License](LICENSE).

## ⭐ Support the project

If ResumeAI helps you improve your job search, consider giving the repository a ⭐ on GitHub and sharing it with someone who could benefit from it.

**Repository:** https://github.com/mohanadmazin/Resume-optimizer
