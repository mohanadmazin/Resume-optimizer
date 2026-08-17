"""Update all imports after splitting app/services/ into sub-packages."""
import os
import pathlib

REPLACEMENTS = {
    "from app.services.ats_engine": "from app.engines.ats_engine",
    "from app.services.scoring_engine": "from app.engines.scoring_engine",
    "from app.services.fact_guard": "from app.engines.fact_guard",
    "from app.services.parser_fact_guard": "from app.engines.parser_fact_guard",
    "from app.services.diff_highlight": "from app.engines.diff_highlight",
    "from app.services.auto_fit": "from app.engines.auto_fit",
    "from app.services.keyword_targeting": "from app.engines.keyword_targeting",
    "from app.services.resume_scorer": "from app.engines.resume_scorer",
    "from app.services.content_checker": "from app.engines.content_checker",
    "from app.services.browser_fetcher": "from app.infrastructure.browser_fetcher",
    "from app.services.job_fetcher": "from app.infrastructure.job_fetcher",
    "from app.services.security": "from app.infrastructure.security",
    "from app.services.html_extractor": "from app.infrastructure.html_extractor",
    "from app.services.document_reader": "from app.infrastructure.document_reader",
    "from app.services.resume_parser": "from app.infrastructure.resume_parser",
    "from app.services.backup": "from app.infrastructure.backup",
    "from app.services.global_search": "from app.infrastructure.global_search",
    "from app.services.metadata": "from app.infrastructure.metadata",
    "from app.services.linkedin_import": "from app.infrastructure.linkedin_import",
}

ROOTS = ["app", "tests"]

def main():
    updated = 0
    files_checked = 0
    for root in ROOTS:
        for path in pathlib.Path(root).rglob("*.py"):
            if "__pycache__" in str(path):
                continue
            files_checked += 1
            text = path.read_text(encoding="utf-8")
            changed = False
            for old, new in REPLACEMENTS.items():
                if old in text:
                    text = text.replace(old, new)
                    changed = True
            if changed:
                path.write_text(text, encoding="utf-8")
                updated += 1
                print(f"  Updated: {path}")
    print(f"\nChecked {files_checked} files, updated {updated} files.")

if __name__ == "__main__":
    main()
