# Implementation Plan: Feature Parity Roadmap + Regression Tests

## Overview

Complete the feature parity roadmap (Milestones 1-6) for the local-first resume optimizer, deliver 30 required regression tests, set up tooling (ruff, mypy, pytest-cov, bandit, pip-audit), and create a cross-platform CI workflow. The regression tests and tooling are the release blocker and must be completed first.

## Current State

### Regression Tests
- **9 of 30** already covered (tests 1-3, 10, 13-15, 25-27)
- **21 of 30** missing — largest gaps in cancellation/timeout (5-9), security (11-12), document limits (20-22), scoring/export (28, 30)

### Tooling
- No linter, type checker, coverage, security scanning, or CI configured
- Dev dependencies: only `pytest>=9.1,<10`

### Milestone Status
| Milestone | Status |
|-----------|--------|
| M1 — Correctness & Safety | **Complete** (all 11 items) |
| M2 — Resume Studio | **Partial** (8/10 items; missing auto-save, duplication, reorder, rename, issue navigation) |
| M3 — Targeting & Writing | **Partial** (backend exists for most; no standalone generators, no UI for suggestions) |
| M4 — Templates & Export | **Partial** (manifests + auto-fit done; no live switching, no page target UI, no export validation) |
| M5 — AI Agent | **Partial** (DB schema + individual pieces exist; not integrated as agent workflow) |
| M6 — Broader Career | **Missing** (DB schemas only for tracker, interview, cover-letter library) |

## Architecture Decisions

1. **Regression tests before features** — the 21 missing tests are a release blocker; implement them first
2. **Tooling in parallel with tests** — ruff/mypy/pytest-cov/bandit/pip-audit + CI can be set up alongside test writing
3. **Vertical slicing per milestone** — each milestone delivers a complete user-facing path, not isolated components
4. **Backend-first for M2-M3** — wire existing backend pieces into UI before writing new AI prompts
5. **Export validation requires PyMuPDF + python-docx text extraction** — test infrastructure needed before export tests

## Task List

### Phase 1: Regression Tests + Tooling (Release Blocker)

#### Task 1: Set up dev tooling
**Description:** Add ruff, mypy, pytest-cov, bandit, pip-audit to dev dependencies and configure them in pyproject.toml.

**Acceptance criteria:**
- [ ] `ruff` configured in `[tool.ruff]` with sensible defaults (line-length=100, select E/F/W/I)
- [ ] `mypy` configured in `[tool.mypy]` (python_version="3.12", warn_return_any, disallow_untyped_defs for app/)
- [ ] `pytest-cov` added to dev deps, `addopts = "--cov=app --cov-report=term-missing"` in pytest config
- [ ] `bandit` added to dev deps, configured to scan app/ excluding tests
- [ ] `pip-audit` added to dev deps
- [ ] `ruff check app/ tests/` passes
- [ ] `mypy app/` passes (or acceptable baseline)

**Verification:** `pip install -e ".[dev]" && ruff check . && mypy app/ && pytest --cov`

**Dependencies:** None

**Files likely touched:**
- `pyproject.toml` (dev deps + tool configs)

**Estimated scope:** S

#### Task 2: CI workflow (Windows, macOS, Linux)
**Description:** Create `.github/workflows/ci.yml` that runs tests, lint, type check, and security scan on all three platforms.

**Acceptance criteria:**
- [ ] `.github/workflows/ci.yml` exists
- [ ] Matrix: windows-latest, macos-latest, ubuntu-latest
- [ ] Steps: checkout, setup-python, install deps, ruff, mypy, pytest --cov, bandit, pip-audit
- [ ] Playwright browser install step (conditional on browser tests)

**Verification:** Push to branch, verify CI runs green on all platforms

**Dependencies:** Task 1

**Files likely touched:**
- `.github/workflows/ci.yml` (new)

**Estimated scope:** S

#### Task 3: WAL backup integrity test
**Description:** `test_wal_database_backup_passes_integrity_check` — create a WAL-mode database, perform a backup, run `PRAGMA integrity_check` on the backup, verify it returns `"ok"`.

**Acceptance criteria:**
- [ ] Test creates SQLite DB in WAL mode
- [ ] Backup is performed via the existing backup mechanism
- [ ] `PRAGMA integrity_check` on backup returns `"ok"`
- [ ] Test passes

**Verification:** `pytest tests/test_migrations.py -k "wal_backup" -v`

**Dependencies:** None

**Files likely touched:**
- `tests/test_migrations.py`

**Estimated scope:** S

#### Task 4: Worker/timeout cancellation tests (5 tests)
**Description:** Write tests 5-9: timeout never calls QThread.terminate, cancellation is not global, cancel event reaches Ollama, cancelled Ollama request is not retried, streaming closes on cancel.

**Acceptance criteria:**
- [ ] `test_timeout_never_calls_qthread_terminate` — mock Worker, verify terminate() never called
- [ ] `test_worker_cancellation_is_not_global` — two Workers, cancel one, verify other unaffected
- [ ] `test_pipeline_cancel_event_reaches_ollama` — PipelineWorker passes cancel_event to OllamaClient
- [ ] `test_cancelled_ollama_request_is_not_retried` — OllamaCancelledError re-raised immediately
- [ ] `test_streaming_ollama_request_closes_on_cancel` — streaming loop exits on cancel

**Verification:** `pytest tests/test_workers.py tests/test_ollama_client.py -v`

**Dependencies:** None

**Files likely touched:**
- `tests/test_workers.py` (new)
- `tests/test_ollama_client.py` (extend)

**Estimated scope:** M

#### Task 5: Browser security tests (3 tests)
**Description:** Write tests 11-13: browser blocks loopback redirect, blocks private subresource, domain matching requires real suffix.

**Acceptance criteria:**
- [ ] `test_browser_blocks_loopback_redirect` — _secure_route blocks redirect to 127.0.0.1
- [ ] `test_browser_blocks_private_subresource` — _secure_route blocks resource types
- [ ] `test_browser_domain_matching_requires_real_suffix` — linkedin.com.evil.com not matched

**Verification:** `pytest tests/test_browser_fetcher.py -v`

**Dependencies:** None

**Files likely touched:**
- `tests/test_browser_fetcher.py` (extend)

**Estimated scope:** S

#### Task 6: Redirected blocked port test
**Description:** `test_redirected_blocked_port_is_rejected` — verify that a redirect chain that lands on a blocked port (e.g., 22, 3306) is rejected.

**Acceptance criteria:**
- [ ] Test simulates redirect to blocked port
- [ ] Request is rejected with appropriate error
- [ ] Test passes

**Verification:** `pytest tests/test_job_fetcher.py -k "redirected_blocked_port" -v`

**Dependencies:** None

**Files likely touched:**
- `tests/test_job_fetcher.py` (extend)

**Estimated scope:** S

#### Task 7: Document reader limit tests (3 tests)
**Description:** Write tests 20-22: PDF page limit, DOCX expansion limit, AI parser input limit.

**Acceptance criteria:**
- [ ] `test_pdf_page_limit` — PDF with >60 pages is rejected
- [ ] `test_docx_expansion_limit` — DOCX with high compression ratio rejected
- [ ] `test_ai_parser_input_limit` — input >40k chars truncated

**Verification:** `pytest tests/test_parser.py -v`

**Dependencies:** None

**Files likely touched:**
- `tests/test_parser.py` (extend)

**Estimated scope:** M

#### Task 8: Parser and fact-guard tests (4 tests)
**Description:** Write tests 16-19, 23-24: indexed operations for duplicate titles, deleted bullet review, negation review, major semantic change review, parser validates contact/bullets, invalid certification removed.

**Acceptance criteria:**
- [ ] `test_duplicate_job_titles_use_indexed_operations`
- [ ] `test_deleted_bullet_requires_review`
- [ ] `test_negation_change_requires_review`
- [ ] `test_major_semantic_change_requires_review`
- [ ] `test_parser_validates_contact_and_bullets`
- [ ] `test_invalid_certification_is_removed`

**Verification:** `pytest tests/test_fact_guard.py tests/test_parser.py tests/test_versioning.py -v`

**Dependencies:** None

**Files likely touched:**
- `tests/test_fact_guard.py` (extend)
- `tests/test_parser.py` (extend)
- `tests/test_versioning.py` (extend)

**Estimated scope:** M

#### Task 9: Scoring and export tests (2 tests)
**Description:** Write tests 28, 30: score equals visible rule results, exported PDF text matches resume model.

**Acceptance criteria:**
- [ ] `test_score_equals_visible_rule_results` — build_score_report score matches sum of category penalties
- [ ] `test_exported_pdf_text_matches_resume_model` — export PDF, extract text with PyMuPDF, compare key fields

**Verification:** `pytest tests/test_scoring_engine.py tests/test_exporter.py -v`

**Dependencies:** Task 1 (pytest-cov for coverage), Task 7 (PDF test infra)

**Files likely touched:**
- `tests/test_scoring_engine.py` (new)
- `tests/test_exporter.py` (extend)

**Estimated scope:** M

#### Task 10: Custom skills refresh test
**Description:** `test_custom_skill_changes_refresh_immediately` — change custom_skills in settings, verify ATS analysis reflects the change.

**Acceptance criteria:**
- [ ] Test modifies custom_skills in AppSettings
- [ ] Runs ATS analysis before and after
- [ ] Skills appear/disappear in results accordingly

**Verification:** `pytest tests/test_ats_engine.py -k "custom_skill" -v`

**Dependencies:** None

**Files likely touched:**
- `tests/test_ats_engine.py` (extend)

**Estimated scope:** S

### Checkpoint: Release Blocker Cleared
- [ ] All 30 regression tests pass
- [ ] ruff, mypy, pytest-cov, bandit, pip-audit configured and passing
- [ ] CI workflow running on all 3 platforms
- [ ] Full test suite passes with coverage report

---

### Phase 2: Milestone 2 — Resume Studio Completion

#### Task 11: Auto-save
**Description:** Persist ResumeData to the database automatically after edits with a debounce timer (e.g., 2 seconds after last edit).

**Acceptance criteria:**
- [ ] ViewModel emits `resume_changed` signal
- [ ] Debounce timer triggers save to DB after 2s of inactivity
- [ ] Save uses the existing repository pattern
- [ ] No save during initial load or undo/redo

**Verification:** Manual: edit a field, wait 2s, close and reopen — data persists

**Dependencies:** None

**Files likely touched:**
- `app/ui/view_models/studio_vm.py`
- `app/ui/pages/studio.py`
- `tests/test_studio.py`

**Estimated scope:** M

#### Task 12: Resume duplication
**Description:** Add a "Duplicate Resume" action that creates a deep copy of a resume with "(Copy)" appended to the name.

**Acceptance criteria:**
- [ ] Duplicate button in dashboard or studio
- [ ] Deep copies all resume data
- [ ] New resume gets a new ID
- [ ] Original is unchanged

**Verification:** `pytest tests/test_studio.py -k "duplicate" -v`

**Dependencies:** None

**Files likely touched:**
- `app/ui/pages/studio.py`
- `app/database/repositories/` (resume repository method)
- `tests/test_studio.py`

**Estimated scope:** M

#### Task 13: Resume versions UI
**Description:** Add a versions panel to the Studio that lists saved versions, allows saving a new version, and restoring a previous version.

**Acceptance criteria:**
- [ ] "Save Version" button saves current state with timestamp
- [ ] Version list shows version number, timestamp, change_summary
- [ ] "Restore" button loads a version back into the editor
- [ ] Uses existing VersioningRepository

**Verification:** `pytest tests/test_versioning.py tests/test_studio.py -v`

**Dependencies:** None (backend already exists)

**Files likely touched:**
- `app/ui/pages/studio.py`
- `app/ui/view_models/studio_vm.py`
- `tests/test_studio.py`
- `tests/test_versioning.py`

**Estimated scope:** M

#### Task 14: Reorder sections
**Description:** Add move-up/move-down buttons to the SectionNavigator to let users reorder sections.

**Acceptance criteria:**
- [ ] Up/Down buttons in SectionNavigator
- [ ] Section order persisted in ResumeData or a section_order field
- [ ] Preview updates to reflect new order
- [ ] Export respects user-defined order

**Verification:** `pytest tests/test_studio.py -k "reorder" -v`

**Dependencies:** None

**Files likely touched:**
- `app/ui/components/section_navigator.py`
- `app/ui/view_models/studio_vm.py`
- `app/ui/pages/studio.py`
- `tests/test_studio.py`

**Estimated scope:** M

#### Task 15: Rename sections
**Description:** Allow users to rename section headings (double-click in navigator or a rename field).

**Acceptance criteria:**
- [ ] Double-click on section name → editable field
- [ ] Renamed heading persists in the resume model
- [ ] Export uses the custom heading
- [ ] Reset to default option available

**Verification:** `pytest tests/test_studio.py -k "rename" -v`

**Dependencies:** Task 14

**Files likely touched:**
- `app/ui/components/section_navigator.py`
- `app/ui/view_models/studio_vm.py`
- `tests/test_studio.py`

**Estimated scope:** S

#### Task 16: Click issue to navigate
**Description:** Make issue items in ResumeInsightsPanel clickable — clicking an issue scrolls/focuses the corresponding field in SectionEditor.

**Acceptance criteria:**
- [ ] Issues rendered as clickable items (not plain text)
- [ ] Click emits a signal with section name + field identifier
- [ ] SectionEditor has `scroll_to_field(field_id)` method
- [ ] Studio page connects the signals

**Verification:** `pytest tests/test_studio.py -k "navigate" -v`

**Dependencies:** None

**Files likely touched:**
- `app/ui/components/resume_insights_panel.py`
- `app/ui/components/section_editor.py`
- `app/ui/pages/studio.py`
- `tests/test_studio.py`

**Estimated scope:** M

### Checkpoint: Studio Complete
- [ ] Auto-save works
- [ ] Resume duplication works
- [ ] Versions panel works
- [ ] Section reorder/rename works
- [ ] Issue navigation works
- [ ] All tests pass

---

### Phase 3: Milestone 3 — Targeting & Writing Tools

#### Task 17: Standalone summary generator
**Description:** Add a "Generate Summary" button to the Studio that uses a dedicated AI prompt to generate a professional summary from the resume's experience and skills.

**Acceptance criteria:**
- [ ] Dedicated prompt in `app/ai/prompts.py` for summary generation
- [ ] Service function `generate_summary(resume, jd_text?, client)` 
- [ ] UI button in Studio Summary section
- [ ] Generated summary populates the field (user can edit before accepting)
- [ ] UndoStack integration

**Verification:** `pytest tests/test_studio.py -k "summary" -v`

**Dependencies:** None

**Files likely touched:**
- `app/ai/prompts.py`
- `app/services/` (new summary service or extend optimizer)
- `app/ui/components/section_editor.py`
- `tests/test_studio.py`

**Estimated scope:** M

#### Task 18: Standalone headline generator
**Description:** Same pattern as Task 17 but for the headline/tagline field.

**Acceptance criteria:**
- [ ] Dedicated prompt for headline generation
- [ ] Service function
- [ ] UI button in Studio Contact/Headline section
- [ ] UndoStack integration

**Verification:** `pytest tests/test_studio.py -k "headline" -v`

**Dependencies:** Task 17 (pattern reuse)

**Files likely touched:**
- `app/ai/prompts.py`
- `app/services/`
- `app/ui/components/section_editor.py`
- `tests/test_studio.py`

**Estimated scope:** S

#### Task 19: Skill suggestions UI
**Description:** Surface the existing KeywordTarget.suggested_paths and requires_user_confirmation in the Studio — show suggested skills with Accept/Reject buttons.

**Acceptance criteria:**
- [ ] Suggested skills panel in Studio (or inside InsightsPanel)
- [ ] Each suggestion shows keyword + status (MISSING/PARTIAL) + placement path
- [ ] Accept/Reject buttons update SuggestionRecord in DB
- [ ] Accepted suggestions trigger field population

**Verification:** `pytest tests/test_studio.py tests/test_keyword_targeting.py -v`

**Dependencies:** None (backend exists)

**Files likely touched:**
- `app/ui/components/resume_insights_panel.py`
- `app/ui/view_models/studio_vm.py`
- `tests/test_studio.py`
- `tests/test_keyword_targeting.py`

**Estimated scope:** M

#### Task 20: Side-by-side diff tests
**Description:** Add dedicated tests for `diff_highlight.py` — verify word-level and bullet-level diff rendering.

**Acceptance criteria:**
- [ ] Test identical resumes produce no highlighting
- [ ] Test changed words are highlighted
- [ ] Test added/removed bullets are highlighted
- [ ] Test HTML output is well-formed

**Verification:** `pytest tests/test_diff_highlight.py -v`

**Dependencies:** None

**Files likely touched:**
- `tests/test_diff_highlight.py` (new)

**Estimated scope:** S

#### Task 21: One-click rollback
**Description:** Add a "Revert to Original" button that restores the pre-optimization resume from a saved snapshot.

**Acceptance criteria:**
- [ ] Save original resume before optimization pipeline runs
- [ ] "Revert" button restores the original
- [ ] Uses UndoStack or direct DB restore
- [ ] Confirmation dialog before revert

**Verification:** `pytest tests/test_studio.py -k "rollback" -v`

**Dependencies:** Task 13 (versioning infrastructure)

**Files likely touched:**
- `app/ui/pages/optimization.py`
- `app/ui/view_models/studio_vm.py`
- `app/application/optimize_resume.py`
- `tests/test_studio.py`

**Estimated scope:** M

### Checkpoint: Targeting Tools Complete
- [ ] Summary generator works
- [ ] Headline generator works
- [ ] Skill suggestions UI works
- [ ] Diff tested
- [ ] Rollback works
- [ ] All tests pass

---

### Phase 4: Milestone 4 — Templates & Export

#### Task 22: Live template switching
**Description:** Add a template selector to the Studio that applies a TemplateManifest to the resume and updates the preview.

**Acceptance criteria:**
- [ ] Template dropdown in Studio (7 presets)
- [ ] Selecting a template updates ResumePreview styling
- [ ] Preference saved to TemplatePreference table
- [ ] Preview uses template's font, sizes, margins

**Verification:** `pytest tests/test_studio.py -k "template" -v`

**Dependencies:** None (TemplateManifest already exists)

**Files likely touched:**
- `app/ui/pages/studio.py`
- `app/ui/components/resume_preview.py`
- `app/database/repositories/versioning_repository.py` (extend)
- `tests/test_studio.py`

**Estimated scope:** M

#### Task 23: Page target UI
**Description:** Add a 1-page / 2-page radio button or spinner that feeds into auto_fit.

**Acceptance criteria:**
- [ ] Page target control in Studio or Export page
- [ ] Feeds `maximum_pages` to auto_fit
- [ ] Auto-adjust button triggers binary search
- [ ] Result shows font scale applied

**Verification:** `pytest tests/test_templates.py -k "page_target" -v`

**Dependencies:** None

**Files likely touched:**
- `app/ui/pages/studio.py`
- `app/services/auto_fit.py`
- `tests/test_templates.py`

**Estimated scope:** S

#### Task 24: Template-aware PDF/DOCX export
**Description:** Refactor exporters to read styling from TemplateManifest instead of hardcoded values.

**Acceptance criteria:**
- [ ] `export_pdf(resume, template)` accepts template parameter
- [ ] `export_docx(resume, template)` accepts template parameter
- [ ] Font, sizes, margins, section order read from manifest
- [ ] Backward compatible (default template if None)

**Verification:** `pytest tests/test_exporter.py -v`

**Dependencies:** Task 22

**Files likely touched:**
- `app/exports/exporter.py`
- `app/ui/pages/optimization.py` (pass template)
- `tests/test_exporter.py`

**Estimated scope:** L

#### Task 25: Export validation
**Description:** Add round-trip validation: extract text from exported PDF/DOCX and compare with source ResumeData.

**Acceptance criteria:**
- [ ] `validate_export(resume, pdf_path)` extracts text and compares
- [ ] `validate_export(resume, docx_path)` extracts text and compares
- [ ] Key fields (name, company, skills) must appear in extracted text
- [ ] Validation runs automatically after export (optional, with warning)

**Verification:** `pytest tests/test_exporter.py -k "validate" -v`

**Dependencies:** Task 24

**Files likely touched:**
- `app/exports/exporter.py`
- `tests/test_exporter.py`

**Estimated scope:** M

### Checkpoint: Templates & Export Complete
- [ ] Live template switching works
- [ ] Page target control works
- [ ] Template-aware export works
- [ ] Export validation works
- [ ] All tests pass

---

### Phase 5: Milestone 5 — AI Agent

#### Task 26: Agent tool definitions
**Description:** Implement the AgentTool enum and AgentAction Pydantic model as specified.

**Acceptance criteria:**
- [ ] `AgentTool` enum with 7 tools
- [ ] `AgentAction` Pydantic model
- [ ] `AgentConversation` and `AgentMessage` DB models already exist — verify they match

**Verification:** `pytest tests/test_agent.py -v`

**Dependencies:** None

**Files likely touched:**
- `app/domain/agent.py` (new)
- `tests/test_agent.py` (new)

**Estimated scope:** S

#### Task 27: Agent service — proposal pipeline
**Description:** Implement the agent service that takes a resume + job description, proposes changes via typed commands, validates with fact guard, and presents a visual diff.

**Acceptance criteria:**
- [ ] `AgentService.propose(resume, jd_text, tool)` returns list of AgentAction
- [ ] Each action passes through FactGuard
- [ ] Visual diff generated for each accepted proposal
- [ ] Proposals stored as AgentMessage records

**Verification:** `pytest tests/test_agent.py -v`

**Dependencies:** Task 26

**Files likely touched:**
- `app/services/agent.py` (new)
- `tests/test_agent.py` (extend)

**Estimated scope:** L

#### Task 28: Agent UI — chat-style interface
**Description:** Create an Agent page with a chat-like interface where the user can ask the agent to score, target, suggest bullets, rewrite summary, explain issues, and apply suggestions.

**Acceptance criteria:**
- [ ] Agent page with message history + input field
- [ ] Tool selection (dropdown or command palette)
- [ ] Proposals shown as cards with Accept/Reject
- [ ] UndoStack integration for applied suggestions
- [ ] Confirmation dialog before applying changes

**Verification:** `pytest tests/test_agent.py tests/test_studio.py -v`

**Dependencies:** Task 27

**Files likely touched:**
- `app/ui/pages/agent.py` (new)
- `app/ui/components/agent_proposal_card.py` (new)
- `app/application/optimize_resume.py` (extend)
- `tests/test_agent.py` (extend)

**Estimated scope:** L

### Checkpoint: Agent Complete
- [ ] Agent tools defined
- [ ] Proposal pipeline works
- [ ] Agent UI works
- [ ] All proposals pass through fact guard
- [ ] UndoStack integration works
- [ ] All tests pass

---

### Phase 6: Milestone 6 — Broader Career Features

#### Task 29: Application tracker
**Description:** Build the application tracker using the existing JobApplication DB model.

**Acceptance criteria:**
- [ ] ApplicationsPage with list view (company, role, status, date)
- [ ] Add/edit/delete applications
- [ ] Status workflow: wishlist → applied → interview → offer → rejected
- [ ] Link to resume and job description

**Verification:** `pytest tests/test_application_tracker.py -v`

**Dependencies:** None

**Files likely touched:**
- `app/ui/pages/applications.py` (new)
- `app/database/repositories/application_repository.py` (new)
- `app/domain/application_tracker.py` (new)
- `tests/test_application_tracker.py` (new)

**Estimated scope:** L

#### Task 30: Cover-letter library
**Description:** Build a library UI for browsing, searching, and reusing previously generated cover letters.

**Acceptance criteria:**
- [ ] CoverLetterLibraryPage with list view
- [ ] Search by company/role/date
- [ ] View, copy, export saved letters
- [ ] Link to originating resume/job

**Verification:** `pytest tests/test_cover_letter_library.py -v`

**Dependencies:** None (CoverLetter model exists)

**Files likely touched:**
- `app/ui/pages/cover_letter_library.py` (new)
- `app/database/repositories/cover_letter_repository.py` (new)
- `tests/test_cover_letter_library.py` (new)

**Estimated scope:** M

#### Task 31: Job-specific resume variants
**Description:** Allow users to create and manage multiple variants of the same resume for different job applications.

**Acceptance criteria:**
- [ ] Variants listed under a resume (like git branches)
- [ ] Create variant from existing resume
- [ ] Each variant is an independent copy
- [ ] Switch between variants in Studio

**Verification:** `pytest tests/test_studio.py -k "variant" -v`

**Dependencies:** Task 12 (duplication), Task 13 (versions)

**Files likely touched:**
- `app/ui/pages/studio.py`
- `app/database/repositories/`
- `tests/test_studio.py`

**Estimated scope:** M

#### Task 32: Interview question generator
**Description:** Build an AI-powered interview question generator that produces role-specific questions and STAR response outlines.

**Acceptance criteria:**
- [ ] InterviewPrepPage with role/company input
- [ ] AI generates 10-15 questions with STAR outlines
- [ ] Questions categorized (behavioral, technical, situational)
- [ ] Export to markdown/PDF

**Verification:** `pytest tests/test_interview_prep.py -v`

**Dependencies:** None

**Files likely touched:**
- `app/ui/pages/interview_prep.py` (new)
- `app/services/interview_prep.py` (new)
- `app/ai/prompts.py` (extend)
- `tests/test_interview_prep.py` (new)

**Estimated scope:** M

#### Task 33: LinkedIn data import
**Description:** Import resume data from a LinkedIn data export (JSON or CSV) rather than scraping.

**Acceptance criteria:**
- [ ] Import page accepts LinkedIn data export file
- [ ] Parses positions, education, skills from export
- [ ] Maps to ResumeData model
- [ ] User reviews imported data before saving

**Verification:** `pytest tests/test_linkedin_import.py -v`

**Dependencies:** None

**Files likely touched:**
- `app/ui/pages/import_linkedin.py` (new)
- `app/services/linkedin_import.py` (new)
- `tests/test_linkedin_import.py` (new)

**Estimated scope:** M

### Checkpoint: Broader Career Features Complete
- [ ] Application tracker works
- [ ] Cover-letter library works
- [ ] Resume variants work
- [ ] Interview prep works
- [ ] LinkedIn import works
- [ ] All tests pass

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| PyMuPDF not installed on CI | Export tests fail | Add to optional deps, skip if not available |
| Playwright browser tests flaky | CI failures | Skip browser tests in CI, run locally |
| mypy strict mode too noisy | Blocking progress | Start with baseline, suppress known issues |
| Agent AI prompts complex | Long iteration time | Use existing prompt patterns, iterate per-tool |
| Export validation fragile | False negatives | Use fuzzy matching, not exact text comparison |
| Cross-platform font differences | Export mismatch | Use built-in fonts (already done), test on each OS |

## Open Questions

1. **Should the agent be a separate page or integrated into Studio?** Recommendation: separate page (less UI complexity, clearer mental model)
2. **Should LinkedIn import support profile scraping or only data export?** Recommendation: data export only (privacy-first, no scraping)
3. **Should the application tracker be a full CRM or lightweight list?** Recommendation: lightweight list with status workflow
4. **How should we handle mypy baseline?** Recommendation: start with `ignore_missing_imports = true` for third-party libs, add `# type: ignore` for known issues
