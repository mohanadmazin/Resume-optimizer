# Windows setup

From PowerShell in the project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -c "from app.database.migrate import run_migrations; run_migrations()"
pytest -q
python main.py
```

For local Ollama features, start Ollama and select an installed model in the
application Settings page.

## Resume workflow

1. Import or create a resume.
2. Use the sections in the top bar to edit the same structured resume.
3. Select **Review** or **Finish Up & Preview**.
4. Resolve blockers and approve the current revision.
5. Export DOCX, PDF, or Markdown.

Any edit after approval disables export until the new revision is approved.
