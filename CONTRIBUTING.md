# Contributing to ResumeAI

Thank you for helping improve ResumeAI! Contributions are welcome, from bug fixes and tests to documentation and new features.

## Before you start

- Check existing Issues and Pull Requests to avoid duplicate work.
- For significant changes, open an issue first so the approach can be discussed.
- Never commit API keys, tokens, personal resumes, job applications, databases, browser profiles, or other private data.

## Development setup

ResumeAI requires Python 3.12+ and uses Ollama for optional local AI features.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,browser]"
python -m playwright install chromium
```

Run the test suite:

```bash
pytest
```

Run linting and type checks:

```bash
ruff check app/ tests/
mypy app/ --ignore-missing-imports
```

## Pull requests

1. Create a focused branch from `main`.
2. Make the smallest complete change that solves the problem.
3. Add or update tests when behavior changes.
4. Update documentation when user-facing behavior changes.
5. Run tests, Ruff, and MyPy locally.
6. Open a pull request with a clear summary and testing notes.

## Commit messages

Prefer short, descriptive commits such as:

- `fix: handle malformed resume upload`
- `feat: add application status filter`
- `docs: improve installation instructions`

## Security

If you discover a security vulnerability, please do not publish sensitive exploit details in a public issue. Contact the maintainer privately through the repository owner's GitHub profile so the issue can be assessed and fixed responsibly.

## Code style

Keep business logic testable and separate from UI concerns. Preserve the project's local-first design and avoid introducing unnecessary external services or telemetry.

## License

By contributing, you agree that your contributions will be licensed under the MIT License included in this repository.
