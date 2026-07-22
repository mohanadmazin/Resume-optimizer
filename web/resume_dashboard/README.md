# ResumeAI — Shared Resume Builder

A responsive, dependency-free editor mounted inside the ResumeAI FastAPI application at `/builder/`.

## Sections

1. Contact
2. Experience
3. Projects
4. Education
5. Certifications
6. Coursework
7. Skills
8. Summary
9. Finish Up & Preview
10. Quick Cover Letter Draft

## Key behavior

- Loads the selected SQLite resume through `/api/builder/state`.
- Debounced autosave updates the same record used by ATS and optimization.
- Explicit Save creates a resume version.
- Save & Continue opens Target Jobs.
- Falls back to browser `localStorage` if the backend cannot be reached.
- Supports add/remove sections, live preview, browser print/PDF, plain-text download, JSON backup, copy/download of a quick deterministic cover-letter draft, and reset confirmation.
- The tailored AI cover-letter action opens the main ResumeAI cover-letter workflow.

## Run

From the project root:

```bash
python -m pip install -e ".[web]"
python web_main.py
```

Open `http://127.0.0.1:8000/builder/`.
