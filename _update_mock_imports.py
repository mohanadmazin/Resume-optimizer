"""Update mock.patch string paths after services restructuring."""
import pathlib

REPLACEMENTS = {
    # Engines
    'app.services.ats_engine' : 'app.engines.ats_engine',
    'app.services.scoring_engine' : 'app.engines.scoring_engine',
    'app.services.fact_guard' : 'app.engines.fact_guard',
    'app.services.parser_fact_guard' : 'app.engines.parser_fact_guard',
    'app.services.diff_highlight' : 'app.engines.diff_highlight',
    'app.services.auto_fit' : 'app.engines.auto_fit',
    'app.services.keyword_targeting' : 'app.engines.keyword_targeting',
    'app.services.resume_scorer' : 'app.engines.resume_scorer',
    'app.services.content_checker' : 'app.engines.content_checker',
    # Infrastructure
    'app.services.browser_fetcher' : 'app.infrastructure.browser_fetcher',
    'app.services.job_fetcher' : 'app.infrastructure.job_fetcher',
    'app.services.security' : 'app.infrastructure.security',
    'app.services.html_extractor' : 'app.infrastructure.html_extractor',
    'app.services.document_reader' : 'app.infrastructure.document_reader',
    'app.services.resume_parser' : 'app.infrastructure.resume_parser',
    'app.services.backup' : 'app.infrastructure.backup',
    'app.services.global_search' : 'app.infrastructure.global_search',
    'app.services.metadata' : 'app.infrastructure.metadata',
    'app.services.linkedin_import' : 'app.infrastructure.linkedin_import',
}

ROOTS = ["tests"]

def main():
    updated = 0
    for root in ROOTS:
        for path in pathlib.Path(root).rglob("*.py"):
            if "__pycache__" in str(path):
                continue
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
    print(f"\nUpdated {updated} test files.")

if __name__ == "__main__":
    main()
