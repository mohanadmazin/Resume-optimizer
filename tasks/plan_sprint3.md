# Sprint 3: Full Studio CRUD / Reorder / Live Preview

## Overview
The Resume Studio currently supports editing existing entries and list items, but lacks the ability to add/delete experience, project, and education entries, add/delete bullets within entries, and reorder items within lists and bullets. This sprint adds full CRUD operations and a live preview that updates on every keystroke.

## Current State (what exists)
- Section navigation (left panel) ✅
- Edit existing Contact, Summary, Skills, Certifications, Languages ✅
- Edit existing Experience, Projects, Education fields ✅
- Undo/Redo ✅
- Duplicate resume, Save version ✅
- Auto-save on edit ✅
- ATS recalculation on edit ✅
- Preview tab (markdown, updates on focus-out) ✅
- Section reorder (up/down) ✅
- Section rename (custom headings) ✅
- AI summary/headline generation ✅

## What's Missing
1. Add/delete Experience entries
2. Add/delete Project entries
3. Add/delete Education entries
4. Add/delete bullets within Experience entries
5. Reorder bullets within an Experience entry (up/down)
6. Reorder items in Skills/Certifications/Languages lists (up/down)
7. Live preview — update on every keystroke, not just focus-out

---

## Task List

### Task 34: Add/Delete Experience Entries
**Description:** Add "+ Add Experience" button below the experience cards and a "Delete" button on each card. Adding creates a blank ExperienceItem and appends it to the list. Deleting removes the entry at that index. Both emit section_edited to integrate with undo.

**Acceptance criteria:**
- [ ] "+ Add Experience" button appears below all experience cards
- [ ] Clicking it appends a blank ExperienceItem and re-renders the editor
- [ ] Each experience card has a "Delete" button
- [ ] Clicking delete removes that entry and re-renders
- [ ] Both operations push to the undo stack
- [ ] ATS recalculation triggers after add/delete

**Files likely touched:**
- `app/ui/components/section_editor.py`

**Estimated scope:** S (1-2 files)

---

### Task 35: Add/Delete Project Entries
**Description:** Same pattern as Task 34 but for Projects. Add "+ Add Project" button and per-card "Delete" button.

**Acceptance criteria:**
- [ ] "+ Add Project" button appears below all project cards
- [ ] Each project card has a "Delete" button
- [ ] Both operations push to the undo stack

**Files likely touched:**
- `app/ui/components/section_editor.py`

**Estimated scope:** S (1 file)

---

### Task 36: Add/Delete Education Entries
**Description:** Same pattern as Tasks 34-35 but for Education entries.

**Acceptance criteria:**
- [ ] "+ Add Education" button appears below all education cards
- [ ] Each education card has a "Delete" button
- [ ] Both operations push to the undo stack

**Files likely touched:**
- `app/ui/components/section_editor.py`

**Estimated scope:** S (1 file)

---

### Task 37: Add/Delete Bullets in Experience
**Description:** Within each experience card, add an "+ Add Bullet" button below the bullet list and an "x" button next to each bullet to delete it. This operates at the ExperienceItem.bullets list level.

**Acceptance criteria:**
- [ ] "+ Add Bullet" button appears below bullets in each experience card
- [ ] Each bullet has a small delete (×) button to its right
- [ ] Adding creates a blank bullet and puts it in edit mode
- [ ] Deleting removes that bullet from the list
- [ ] Both operations push to the undo stack

**Files likely touched:**
- `app/ui/components/section_editor.py`

**Estimated scope:** S (1 file)

---

### Task 38: Reorder Bullets in Experience
**Description:** Add small up/down arrow buttons next to each bullet to reorder bullets within an experience entry.

**Acceptance criteria:**
- [ ] Each bullet has up (↑) and down (↓) buttons
- [ ] Clicking up moves the bullet one position earlier (unless already first)
- [ ] Clicking down moves the bullet one position later (unless already last)
- [ ] Reorder pushes to the undo stack

**Files likely touched:**
- `app/ui/components/section_editor.py`

**Estimated scope:** S (1 file)

---

### Task 39: Reorder List Items (Skills/Certifications/Languages)
**Description:** Add up/down buttons to the list editor for Skills, Certifications, and Languages so items can be reordered.

**Acceptance criteria:**
- [ ] Up/down buttons appear in the list editor button row
- [ ] Up moves the selected item one position earlier
- [ ] Down moves the selected item one position later
- [ ] Reorder pushes to the undo stack

**Files likely touched:**
- `app/ui/components/section_editor.py`

**Estimated scope:** S (1 file)

---

### Task 40: Live Preview on Keystroke
**Description:** Currently the preview only updates when the user leaves a field (focus-out). Change it to update on every keystroke in text fields (Summary, Contact fields) using a debounce timer. The preview tab should show the latest state at all times.

**Acceptance criteria:**
- [ ] Text changes in Summary or Contact fields update the preview within 300ms
- [ ] List item edits (Skills, etc.) update the preview on commit
- [ ] Experience/Project/Education field changes update the preview on commit
- [ ] No performance degradation (debounce prevents excessive re-renders)

**Files likely touched:**
- `app/ui/components/section_editor.py`
- `app/ui/pages/studio.py`

**Estimated scope:** S (2 files)

---

## Checkpoint: After Tasks 34-40
- [ ] All 783 existing tests pass
- [ ] New tests added for add/delete/reorder operations
- [ ] ruff clean
- [ ] Manual verification: can add, delete, reorder all entry types
- [ ] Live preview updates reactively

---

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Add/delete buttons clutter the UI | Medium | Use compact styling, consistent placement |
| Undo stack gets confusing with many small operations | Low | Group related operations (add = one undo step) |
| Live preview causes flicker | Low | Use debounce timer (300ms) |

## Open Questions
- None — scope is well-defined from existing patterns.
