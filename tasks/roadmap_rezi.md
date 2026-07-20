# Roadmap: Local Rezi.ai Equivalent

## Current State vs Rezi.ai Feature Matrix

| Feature | Rezi.ai | Ours | Gap |
|---------|---------|------|-----|
| **Resume editing (Studio)** | ✅ | ✅ | — |
| **ATS scoring (23 factors)** | ✅ | ✅ (basic) | Need 23-factor scoring |
| **Keyword targeting** | ✅ | ✅ | — |
| **AI summary generation** | ✅ | ✅ | — |
| **AI headline generation** | ✅ | ✅ | — |
| **Undo/redo** | ✅ | ✅ | — |
| **Auto-save** | ✅ | ✅ | — |
| **Version history** | ✅ | ✅ | — |
| **Multiple resumes** | ✅ | ✅ | — |
| **Live preview** | ✅ | ✅ | — |
| **Section reorder** | ✅ | ✅ | — |
| **Skill gap analysis** | ✅ | ✅ | — |
| **Career fact vault** | ❌ | ✅ | We're ahead |
| **Master profile compiler** | ❌ | ✅ | We're ahead |
| **Requirement matrix** | ❌ | ✅ | We're ahead |
| **Achievement discovery** | ❌ | ✅ | We're ahead |
| **Semantic search** | ❌ | ✅ | We're ahead |
| | | | |
| **AI Bullet Point Writer** | ✅ | ❌ | **GAP** |
| **Real-Time Content Checker** | ✅ | ❌ | **GAP** |
| **Resume Score (23 factors)** | ✅ | ❌ | **GAP** |
| **Cover Letter Generator** | ✅ | Partial | **GAP** (standalone) |
| **AI Interview Practice** | ✅ | ❌ | **GAP** |
| **PDF Export** | ✅ | ❌ | **GAP** |
| **DOCX Export** | ✅ | ❌ | **GAP** |
| **Design Control (fonts/colors)** | ✅ | ❌ | **GAP** |
| **Templates (multiple)** | ✅ | ❌ | **GAP** |
| **AI Agent / Chat** | ✅ | ❌ | **GAP** |
| **Job Search Integration** | ✅ | ❌ | **GAP** |
| **Resume Upload/Import** | ✅ | Partial | **GAP** (PDF parse) |

---

## Phased Implementation Plan

### Phase 8: Export & Polish (HIGH PRIORITY)
> Make the app production-ready with professional export.

| Task | Description | Effort |
|------|-------------|--------|
| 8.1 | PDF export (WeasyPrint or ReportLab) | M |
| 8.2 | DOCX export (python-docx) | M |
| 8.3 | Design control: font family, font size, accent color | M |
| 8.4 | Template system: 3 ATS-optimized templates (Classic, Modern, Compact) | L |
| 8.5 | Resume page count auto-resizer | S |

### Phase 9: AI Content Engine (HIGH PRIORITY)
> The core AI features that make rezi.ai useful.

| Task | Description | Effort |
|------|-------------|--------|
| 9.1 | AI Bullet Point Writer (job title + context → metrics-driven bullets) | M |
| 9.2 | Real-Time Content Checker (grammar, weak words, passive voice) | M |
| 9.3 | Resume Score: 23-factor scoring system | L |
| 9.4 | AI Summary v2: longer, more detailed, role-specific | S |
| 9.5 | AI Skills Explorer: suggest skills from job description | S |

### Phase 10: Cover Letter & Interview (MEDIUM PRIORITY)
> Standalone AI tools beyond resume editing.

| Task | Description | Effort |
|------|-------------|--------|
| 10.1 | Cover Letter Generator (standalone page, not just pipeline) | M |
| 10.2 | AI Interview Practice: generate questions from JD + resume | L |
| 10.3 | Interview answer feedback (score + improve) | L |
| 10.4 | STAR method formatter for bullet points | S |

### Phase 11: Job Search & Import (MEDIUM PRIORITY)
> Connect to the job market.

| Task | Description | Effort |
|------|-------------|--------|
| 11.1 | Better resume import (PDF → ResumeData parsing) | M |
| 11.2 | Job search: scrape LinkedIn/Indeed from app | L |
| 11.3 | One-click apply: auto-tailor resume per job | L |
| 11.4 | Job tracker dashboard (apply, interview, offer stages) | M |

### Phase 12: AI Agent / Chat (LOW PRIORITY)
> Chat-based resume guidance.

| Task | Description | Effort |
|------|-------------|--------|
| 12.1 | Chat sidebar: ask questions about your resume | M |
| 12.2 | AI Agent: proactive suggestions while editing | L |
| 12.3 | Career coaching mode (goal setting, action plans) | L |

---

## Effort Estimates

| Size | Description |
|------|-------------|
| S | 1-2 files, < 1h |
| M | 3-5 files, 2-4h |
| L | 5+ files, 4-8h |

## Recommendation

**Start with Phase 8 (Export & Polish)** — PDF export and design control are the most impactful gaps. Users can't use the app seriously without PDF output.

**Then Phase 9 (AI Content Engine)** — the bullet writer and 23-factor scoring are what make rezi.ai compelling.

Phases 10-12 can come later or be skipped depending on priorities.
