# Phase 7 Task Checklist — Career Intelligence Foundation

## Phase 7A: Career Evidence Vault
- [x] Task 34: Domain models for evidence vault (`FactType`, `FactConfidence`, `CareerFact`, `EvidenceSource`)
- [x] Task 35: Database models (5 tables) + migration 0005
- [x] Task 36: `CareerFactRepository` — full CRUD + queries
- [x] Task 37: `EvidenceSourceRepository` — CRUD + source linking
- [x] Task 38: `evidence_vault.py` service — add/verify/reject/search/import facts
- [x] Task 39: Evidence vault UI — fact browser page
- [x] Task 40: Fact Guard integration with vault

## Phase 7B: Master Career Profile & Resume Compiler
- [x] Task 41: Domain models (`MasterCareerProfile`, `ResumeCompilerConfig`, `CompiledResume`)
- [x] Task 42: `MasterProfileRepository` + migration 0006
- [x] Task 43: Evidence ranking service — deterministic scoring
- [x] Task 44: Resume compilation service — page budget, rationale
- [x] Task 45: Profile import from existing resumes + vault
- [x] Task 46: Master profile UI — profile builder page
- [x] Task 47: Resume compiler UI — compile from profile
- [x] Task 48: Wire compiler into optimization pipeline

## Phase 7C: Requirement Evidence Matrix
- [x] Task 49: Domain models (`RequirementType`, `CoverageLevel`, `RequirementMatrix`)
- [x] Task 50: Matrix service — deterministic requirement-evidence matching
- [x] Task 51: Matrix UI — interactive requirement table
- [x] Task 52: Matrix integration with ATS analysis
- [x] Task 53: Matrix export (markdown/CSV)

## Phase 7D: Achievement Discovery Interview
- [x] Task 54: Domain models (`DiscoverySession`, `AchievementResult`)
- [x] Task 55: Discovery service — AI-guided interview, metric extraction
- [x] Task 56: Discovery UI — chat-style interview page
- [x] Task 57: Discovery integration with vault

## Phase 7E: Local Semantic Career Search
- [x] Task 58: TF-IDF vectorizer — pure Python, no ML deps
- [x] Task 59: Career search index — indexing + retrieval
- [x] Task 60: Semantic search UI — enhanced global search
- [x] Task 61: Auto-indexing on vault changes

## Final Checkpoint
- [x] All ~200 new tests pass
- [x] 21 pages total (16 existing + 5 new)
- [x] Ruff clean
- [ ] PROJECT_MAP.md updated
