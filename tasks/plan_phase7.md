# Implementation Plan: Phase 7 — Career Intelligence Foundation

## Overview

Transform Resume Optimizer from a resume rewriting tool into an evidence-grounded career operating system. Phase 7 builds the Career Evidence Vault, Master Career Profile with Resume Compiler, Requirement Evidence Matrix, Achievement Discovery Interview, and Local Semantic Career Search.

Every AI-generated claim (bullets, cover letters, interview answers) will trace back to verified career facts with source attribution. The Master Career Profile compiles targeted resumes from ALL career history — not just one uploaded resume — by searching the evidence vault for relevant experience.

## Architecture Decisions

1. **Evidence-first design** — Every career fact has a confidence level and source link. AI outputs cite facts, not hallucinate.
2. **Vault is the source of truth** — Resumes become views over the vault. The vault survives any individual resume.
3. **Fact Guard integration** — Existing fact guard distinguishes verified vs unsupported claims using the vault.
4. **Deterministic first** — Requirement matching, evidence ranking, and resume compilation use deterministic scoring. AI is used only for generation tasks.
5. **No external embeddings dependency** — Local TF-IDF vectors for semantic search. No HuggingFace/pytorch weight. Can upgrade to local embeddings later.

---

## Phase 7A: Career Evidence Vault (Tasks 34-40)

### Task 34: Domain models for evidence vault
**Description:** Create Pydantic schemas for CareerFact, EvidenceSource, and related types.

**Acceptance criteria:**
- [ ] `app/domain/evidence.py` with: `FactType` enum (achievement, responsibility, project, metric, technology, team, budget, customer, award, certification, publication, testimonial, portfolio, employment, other), `FactConfidence` enum (verified, user_confirmed, reasonable_paraphrase, user_estimate, unsupported, contradictory), `CareerFact` model, `EvidenceSource` model, `FactVerificationEvent` model, `LinkedFact` model

**Dependencies:** None
**Files:** `app/domain/evidence.py`
**Estimated scope:** S

### Task 35: Database models for evidence vault
**Description:** Create 5 ORM models: career_facts, evidence_sources, career_fact_sources (M2M), content_fact_links, fact_verification_events.

**Acceptance criteria:**
- [ ] All 5 tables created with proper FKs, indexes, cascades
- [ ] career_facts stores: statement, fact_type, confidence, employer, project, date_from, date_to, sensitive, metrics_json
- [ ] evidence_sources stores: source_type (document, memory, workflow_log, testimonial), name, file_path, excerpt, page_reference
- [ ] content_fact_links links any content type (resume_bullet, cover_letter, interview_answer) to facts
- [ ] Migration 0005 creates all tables idempotently

**Dependencies:** Task 34
**Files:** `app/database/models.py`, `migrations/versions/0005_add_evidence_vault.py`
**Estimated scope:** M

### Task 36: Evidence vault repository
**Description:** Full CRUD repository for career facts with queries by type, confidence, employer, date range, and text search.

**Acceptance criteria:**
- [ ] `CareerFactRepository` with: create, get, update, delete, list_all, list_by_type, list_by_employer, list_by_confidence, search_by_text, get_facts_for_content, link_fact_to_content, unlink_fact_from_content
- [ ] All methods follow existing repository patterns (session injection, flush, no commit)
- [ ] Tests cover all CRUD operations and query methods

**Dependencies:** Task 35
**Files:** `app/database/repositories/evidence_repository.py`, `tests/test_evidence.py`
**Estimated scope:** M

### Task 37: Evidence source repository
**Description:** CRUD for evidence sources with file linking and excerpt extraction.

**Acceptance criteria:**
- [ ] `EvidenceSourceRepository` with: create, get, update, delete, list_all, list_by_type, get_sources_for_fact, link_source_to_fact
- [ ] Tests for all operations

**Dependencies:** Task 35
**Files:** `app/database/repositories/evidence_source_repository.py`, `tests/test_evidence.py`
**Estimated scope:** S

### Task 38: Evidence vault service
**Description:** Business logic for managing career facts: adding facts with automatic source linking, confidence scoring, fact verification workflow.

**Acceptance criteria:**
- [ ] `add_fact()` — creates fact, links sources, creates verification event
- [ ] `verify_fact()` — upgrades confidence based on evidence strength
- [ ] `reject_fact()` — marks fact as unsupported with reason
- [ ] `search_facts()` — text search with relevance ranking
- [ ] `get_facts_for_role()` — retrieves facts relevant to a job role
- [ ] `import_facts_from_resume()` — extracts facts from existing resume data
- [ ] All operations wrapped in try/except with logging

**Dependencies:** Tasks 36, 37
**Files:** `app/services/evidence_vault.py`, `tests/test_evidence.py`
**Estimated scope:** L

### Task 39: Evidence vault UI — fact browser
**Description:** Page for browsing, adding, editing, and verifying career facts with filtering.

**Acceptance criteria:**
- [ ] `EvidenceVaultPage` with: fact list (QTableWidget), type filter dropdown, confidence filter, add/edit/delete buttons
- [ ] Add/edit dialog with: statement, type, confidence, employer, project, dates, sensitive flag, source linking
- [ ] Verification workflow: buttons to upgrade/downgrade confidence
- [ ] Search bar for text filtering
- [ ] Page registered in main_window.py

**Dependencies:** Task 38
**Files:** `app/ui/pages/evidence_vault.py`, `app/ui/main_window.py`
**Estimated scope:** L

### Task 40: Fact Guard integration with vault
**Description:** Enhance FactGuard to reference career facts when validating AI claims.

**Acceptance criteria:**
- [ ] FactGuard queries vault for matching facts when validating changes
- [ ] Claims matching verified facts → "Verified" confidence
- [ ] Claims matching user_confirmed facts → "Confirmed"
- [ ] Claims with no vault match → "Needs review"
- [ ] Contradicting vault facts → "Contradiction" warning
- [ ] Existing fact guard tests still pass
- [ ] New tests for vault-aware validation

**Dependencies:** Task 38
**Files:** `app/services/fact_guard.py`, `tests/test_fact_guard.py`
**Estimated scope:** M

---

## Phase 7A Checkpoint: Evidence Vault Foundation
- [ ] All 34-40 tests pass
- [ ] Evidence vault CRUD works end-to-end
- [ ] Fact Guard integrates with vault
- [ ] Ruff clean
- [ ] Review before Phase 7B

---

## Phase 7B: Master Career Profile & Resume Compiler (Tasks 41-48)

### Task 41: Master Career Profile domain model
**Description:** Pydantic schema for the comprehensive master profile containing all career history.

**Acceptance criteria:**
- [ ] `app/domain/master_profile.py` with: `CareerEntry` (role, company, dates, bullets, facts), `MasterCareerProfile` (entries, skills, education, certifications, facts), `ResumeCompilerConfig` (max_pages, emphasis, exclude roles, include sections)
- [ ] `CompiledSection` model with: section_name, items, rationale, budget_pct
- [ ] `CompiledResume` model with: sections, exclusions, rationale, total_items

**Dependencies:** Task 34
**Files:** `app/domain/master_profile.py`
**Estimated scope:** S

### Task 42: Master profile repository
**Description:** Store and retrieve the master career profile.

**Acceptance criteria:**
- [ ] `MasterProfileRepository` with: save (upsert), get, delete
- [ ] Profile stored as JSON text in a `master_profiles` table
- [ ] Migration 0006 adds master_profiles table
- [ ] Tests for save/get/delete

**Dependencies:** Task 41
**Files:** `app/database/repositories/master_profile_repository.py`, `app/database/models.py`, `migrations/versions/0006_add_master_profile.py`, `tests/test_master_profile.py`
**Estimated scope:** M

### Task 43: Profile compiler service — evidence ranking
**Description:** Deterministic service that ranks career evidence by relevance to a job description.

**Acceptance criteria:**
- [ ] `rank_evidence(facts, job_requirements)` — scores each fact against requirements using keyword matching, recency weighting, and type importance
- [ ] Scoring: exact keyword match (+10), related skill match (+5), recency bonus (+3 if < 2 years), seniority alignment (+2)
- [ ] Returns facts sorted by relevance score
- [ ] Pure function, no AI dependency
- [ ] 10+ tests covering edge cases

**Dependencies:** Task 34
**Files:** `app/services/profile_compiler.py`, `tests/test_profile_compiler.py`
**Estimated scope:** M

### Task 44: Profile compiler service — resume generation
**Description:** Generate a targeted resume from the master profile by selecting and arranging evidence.

**Acceptance criteria:**
- [ ] `compile_resume(profile, job, config)` → `CompiledResume`
- [ ] Page budget allocation: Content 30%, Format 20%, Optimization 25%, Best Practices 15%, Application Ready 10%
- [ ] Selects top-ranked evidence per section
- [ ] Enforces page budget (configurable max pages)
- [ ] Generates rationale for each included/excluded item
- [ ] Excludes items below relevance threshold
- [ ] Returns both included items (with reasons) and excluded items (with reasons)
- [ ] 10+ tests

**Dependencies:** Task 43
**Files:** `app/services/profile_compiler.py`, `tests/test_profile_compiler.py`
**Estimated scope:** L

### Task 45: Profile import from existing resumes
**Description:** Extract all facts from existing resumes and job descriptions to populate the vault and build the master profile.

**Acceptance criteria:**
- [ ] `import_from_resume(resume_data)` — extracts experience, skills, education, certifications as career facts
- [ ] `import_from_job_analysis(analysis)` — extracts keywords, requirements as evidence
- [ ] `build_master_profile(facts)` — assembles master profile from vault facts
- [ ] Deduplication: avoids creating duplicate facts
- [ ] Links imported facts to their source resume
- [ ] Tests for import, dedup, and profile building

**Dependencies:** Task 38, Task 41
**Files:** `app/services/evidence_vault.py` (extend), `tests/test_evidence.py`
**Estimated scope:** M

### Task 46: Master profile UI — profile builder
**Description:** Page for viewing and managing the master career profile, importing from existing resumes.

**Acceptance criteria:**
- [ ] `MasterProfilePage` with: career timeline view, skill cloud, education list, import buttons
- [ ] "Import from Resume" button that extracts facts
- [ ] "Build Profile" button that assembles the master profile
- [ ] Editable career entries with inline editing
- [ ] Fact count and confidence summary
- [ ] Page registered in main_window.py

**Dependencies:** Task 42, Task 45
**Files:** `app/ui/pages/master_profile.py`, `app/ui/main_window.py`
**Estimated scope:** L

### Task 47: Resume compiler UI
**Description:** UI for compiling a targeted resume from the master profile against a job description.

**Acceptance criteria:**
- [ ] "Compile Resume" button on Master Profile page (or dedicated page)
- [ ] Job selection dropdown (existing jobs in DB)
- [ ] Configuration: max pages, emphasis (skills/experience/education), excluded roles
- [ ] Output: compiled resume preview with inclusion/exclusion rationale
- [ ] "Apply to Resume" button that creates a new resume from compiled output
- [ ] Background worker for compilation (can be slow for large profiles)
- [ ] Tests for UI logic

**Dependencies:** Task 44, Task 46
**Files:** `app/ui/pages/resume_compiler.py` (or extend master_profile.py), `app/ui/main_window.py`
**Estimated scope:** L

### Task 48: Wire compiler into optimization pipeline
**Description:** Add option to use master profile compilation as an alternative to direct resume optimization.

**Acceptance criteria:**
- [ ] Dashboard and optimization pages offer "Compile from Profile" option
- [ ] When selected, uses profile compiler instead of AI optimization
- [ ] Compiled resume can be further optimized by AI if desired
- [ ] Existing pipeline tests still pass
- [ ] New tests for compiler-integrated pipeline

**Dependencies:** Task 44, existing pipeline
**Files:** `app/application/optimize_resume.py`, `app/ui/pages/dashboard.py`
**Estimated scope:** M

---

## Phase 7B Checkpoint: Master Profile & Compiler
- [ ] All 41-48 tests pass
- [ ] Import from resume → vault → profile → compiled resume works
- [ ] Compiler rationale is visible
- [ ] Ruff clean
- [ ] Review before Phase 7C

---

## Phase 7C: Requirement Evidence Matrix (Tasks 49-53)

### Task 49: Requirement matrix domain models
**Description:** Pydantic schemas for requirements, coverage levels, and matrix results.

**Acceptance criteria:**
- [ ] `RequirementType` enum (required, preferred, responsibility, domain, tool, education, certification, location, authorization, travel, soft_skill)
- [ ] `CoverageLevel` enum (direct_evidence, related_evidence, keyword_only, user_confirmed, missing, contradictory, unknown)
- [ ] `RequirementItem` model: text, type, importance, candidate_coverage, evidence_facts, coverage_score, action_needed
- [ ] `RequirementMatrix` model: requirements list, overall_score, gaps, strengths

**Dependencies:** Task 34
**Files:** `app/domain/requirement_matrix.py`
**Estimated scope:** S

### Task 50: Requirement matrix service
**Description:** Deterministic service that builds a requirement-evidence matrix from job requirements and career facts.

**Acceptance criteria:**
- [ ] `build_matrix(job_requirements, career_facts)` → `RequirementMatrix`
- [ ] Classifies each requirement by type
- [ ] Searches vault for matching evidence
- [ ] Assigns coverage level per requirement
- [ ] Scores overall coverage (weighted by importance)
- [ ] Identifies gaps and recommends actions
- [ ] No AI dependency — pure keyword + semantic matching
- [ ] 15+ tests covering all coverage levels

**Dependencies:** Task 49, Task 38
**Files:** `app/services/requirement_matrix.py`, `tests/test_requirement_matrix.py`
**Estimated scope:** L

### Task 51: Requirement matrix UI
**Description:** Interactive matrix view showing job requirements mapped to evidence.

**Acceptance criteria:**
- [ ] `RequirementMatrixPage` with: requirement rows, coverage badges (color-coded), evidence links
- [ ] Columns: Requirement, Type, Importance, Coverage, Evidence Count, Action
- [ ] Click requirement → show linked facts
- [ ] Click "Add Evidence" → link existing fact or create new one
- [ ] Filter by coverage level (show gaps first)
- [ ] Overall score display
- [ ] Page registered in main_window.py

**Dependencies:** Task 50
**Files:** `app/ui/pages/requirement_matrix.py`, `app/ui/main_window.py`
**Estimated scope:** L

### Task 52: Matrix integration with existing analysis
**Description:** Enhance ATS analysis to use requirement matrix alongside keyword matching.

**Acceptance criteria:**
- [ ] ATS analysis page shows requirement matrix tab
- [ ] Matrix results complement keyword heatmap
- [ ] Gaps identified by matrix appear in issue panel
- [ ] Existing ATS tests still pass
- [ ] New tests for matrix-augmented analysis

**Dependencies:** Task 50, existing ATS
**Files:** `app/services/ats_engine.py`, `app/ui/pages/ats_analysis.py`
**Estimated scope:** M

### Task 53: Matrix export
**Description:** Export the requirement matrix as markdown or CSV for external review.

**Acceptance criteria:**
- [ ] `export_matrix(matrix, format)` → str
- [ ] Markdown table with color indicators
- [ ] CSV export with all columns
- [ ] Clipboard copy
- [ ] Tests for both formats

**Dependencies:** Task 50
**Files:** `app/services/requirement_matrix.py` (extend), `tests/test_requirement_matrix.py`
**Estimated scope:** S

---

## Phase 7C Checkpoint: Requirement Matrix
- [ ] All 49-53 tests pass
- [ ] Matrix builds from job + vault
- [ ] Matrix UI shows gaps and evidence
- [ ] Ruff clean

---

## Phase 7D: Achievement Discovery Interview (Tasks 54-57)

### Task 54: Interview domain models
**Description:** Pydantic schemas for the guided achievement interview.

**Acceptance criteria:**
- [ ] `InterviewQuestion` model: question_text, context, follow_ups, category
- [ ] `InterviewAnswer` model: answer_text, extracted_metrics, confidence, fact_links
- [ ] `AchievementResult` model: statement, metrics, previous_value, current_value, metric_status (verified/estimate/unavailable), tools_used
- [ ] `DiscoverySession` model: questions_asked, answers, achievements_discovered

**Dependencies:** None
**Files:** `app/domain/discovery.py`
**Estimated scope:** S

### Task 55: Achievement discovery service
**Description:** AI-powered guided interview that asks follow-up questions to uncover quantified achievements.

**Acceptance criteria:**
- [ ] `start_interview(role)` → first question
- [ ] `answer_question(answer)` → follow-up or next question
- [ ] `extract_achievements(session)` → list of AchievementResult
- [ ] `store_achievements(results, facts)` → saves to vault
- [ ] Follow-up logic: "How long did it take before?", "How many people used it?", "What tools?"
- [ ] Metric extraction: parses numbers, percentages, time durations from answers
- [ ] Never fabricates metrics — marks extracted values as "user_estimate" unless workflow evidence exists
- [ ] 10+ tests

**Dependencies:** Task 34, Task 38
**Files:** `app/services/discovery.py`, `tests/test_discovery.py`
**Estimated scope:** L

### Task 56: Discovery interview UI
**Description:** Chat-style guided interview interface.

**Acceptance criteria:**
- [ ] `DiscoveryPage` with: chat bubbles, input field, question cards
- [ ] Role selector at top
- [ ] Questions appear as AI bubbles
- [ ] User types answers
- [ ] Achievement cards appear when achievements are extracted
- [ ] "Save to Vault" button on each achievement card
- [ ] Progress indicator (questions asked / estimated total)
- [ ] Page registered in main_window.py

**Dependencies:** Task 55
**Files:** `app/ui/pages/discovery.py`, `app/ui/main_window.py`
**Estimated scope:** L

### Task 57: Discovery integration with vault
**Description:** Discovered achievements automatically create career facts in the vault.

**Acceptance criteria:**
- [ ] When user saves an achievement, it becomes a career_fact with type=achievement
- [ ] Extracted metrics stored in fact's metrics_json
- [ ] Source set to "user_interview" with interview session reference
- [ ] Confidence set to "user_confirmed"
- [ ] Tests for the integration

**Dependencies:** Task 55, Task 38
**Files:** `app/services/discovery.py` (extend), `tests/test_discovery.py`
**Estimated scope:** S

---

## Phase 7D Checkpoint: Achievement Discovery
- [ ] All 54-57 tests pass
- [ ] Interview flow works end-to-end
- [ ] Achievements save to vault
- [ ] Ruff clean

---

## Phase 7E: Local Semantic Career Search (Tasks 58-61)

### Task 58: TF-IDF vectorizer service
**Description:** Lightweight local text embedding using TF-IDF (no external ML dependencies).

**Acceptance criteria:**
- [ ] `app/services/career_embeddings.py` with: `CareerVectorizer` class
- [ ] `fit(corpus)` — builds TF-IDF vocabulary from career documents
- [ ] `transform(text)` → sparse vector
- [ ] `similarity(query, documents)` → ranked list of (document, score) tuples
- [ ] `save(path)` / `load(path)` — persist vocabulary and IDF weights
- [ ] No numpy/scipy dependency — pure Python with math module
- [ ] Handles empty corpus gracefully
- [ ] 10+ tests

**Dependencies:** None
**Files:** `app/services/career_embeddings.py`, `tests/test_career_embeddings.py`
**Estimated scope:** M

### Task 59: Semantic search index
**Description:** Index career facts and resume content for semantic retrieval.

**Acceptance criteria:**
- [ ] `CareerSearchIndex` class that indexes: career_facts, resume bullets, cover letters, job descriptions
- [ ] `index_fact(fact)` — adds fact to index
- [ ] `index_resume(resume)` — adds resume content
- [ ] `search(query, limit)` → ranked results with source info
- [ ] `rebuild()` — rebuilds entire index from vault
- [ ] Index persisted to `~/.resume_optimizer/search_index/`
- [ ] Incremental updates (add without full rebuild)
- [ ] 10+ tests

**Dependencies:** Task 58, Task 38
**Files:** `app/services/career_search.py`, `tests/test_career_search.py`
**Estimated scope:** M

### Task 60: Semantic search UI
**Description:** Search interface that uses semantic similarity alongside keyword search.

**Acceptance criteria:**
- [ ] Enhanced global search with semantic mode toggle
- [ ] Semantic results ranked by TF-IDF similarity
- [ ] Results show: source type, statement, similarity score, linked facts
- [ ] Click result → navigate to relevant page
- [ ] Fallback to keyword search when index is empty
- [ ] Tests for search UI logic

**Dependencies:** Task 59
**Files:** `app/services/global_search.py` (extend), `app/ui/main_window.py` (extend)
**Estimated scope:** M

### Task 61: Auto-indexing on vault changes
**Description:** Automatically update search index when career facts are added, modified, or deleted.

**Acceptance criteria:**
- [ ] When a career fact is created/updated/deleted, the search index is updated
- [ ] Index rebuild triggered after bulk imports
- [ ] Background rebuild option for large vaults
- [ ] Index health check (document count matches vault count)
- [ ] Tests for auto-indexing

**Dependencies:** Task 59, Task 38
**Files:** `app/services/career_search.py` (extend), `app/services/evidence_vault.py` (extend)
**Estimated scope:** S

---

## Phase 7E Checkpoint: Semantic Search
- [ ] All 58-61 tests pass
- [ ] TF-IDF vectorizer works without external ML deps
- [ ] Search returns relevant results
- [ ] Auto-indexing on vault changes
- [ ] Ruff clean

---

## Final Phase 7 Checkpoint
- [ ] All 34-61 tests pass (613 + ~200 new = ~813 total)
- [ ] Evidence vault full CRUD
- [ ] Master profile import → compile → export
- [ ] Requirement matrix from job + vault
- [ ] Achievement discovery interview saves to vault
- [ ] Semantic search returns ranked results
- [ ] Fact Guard uses vault for validation
- [ ] All new pages registered (16 + 5 = 21 pages)
- [ ] Ruff clean across all files
- [ ] PROJECT_MAP.md updated

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| TF-IDF quality insufficient for career search | Medium | Keyword fallback always available; can upgrade to local embeddings later |
| Master profile compilation too slow | Medium | Background worker with progress; cache compiled results |
| Achievement interview produces vague answers | Medium | Follow-up prompts are specific; metric extraction marks as "estimate" |
| Large vault causes slow search | Low | TF-IDF is fast; index rebuilt incrementally; pagination on results |
| Migration conflicts with existing schema | Low | Idempotent migration pattern with `_table_exists()` guards |

## Open Questions

- [ ] Should the master profile support multiple career tracks (e.g., engineering + management)?
- [ ] Should the achievement interview support voice input in the future?
- [ ] Should the requirement matrix auto-classify requirement types using AI?
