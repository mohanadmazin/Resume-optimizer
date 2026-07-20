# Implementation Plan: Rezi-Style UI Redesign

## Overview
Redesign the existing resume-optimizer desktop app to match a professional SaaS resume builder aesthetic (rezi.ai-style). The new layout uses a narrow icon-only sidebar, horizontal section tabs in a top nav bar, and form-based editing in the main content area. The existing backend (database, services, models) is preserved; only the UI layer is replaced.

## Architecture Decisions
- **Keep existing backend**: All `app/domain/`, `app/services/`, `app/database/` remain unchanged
- **Replace UI layout**: `MainWindow` gets a new 3-region layout (sidebar + top nav + content)
- **New widget library**: Create reusable custom widgets under `app/ui/components/rezi/`
- **New theme**: Extend `app/ui/theme.py` with Rezi-specific color palette and styles
- **Existing pages preserved**: Old pages remain in `app/ui/pages/` but are not shown in the new layout by default; they can be accessed via sidebar icons
- **Inter font**: Primary font, with Arial/Segoe UI fallbacks

## Color Palette
```python
COLORS = {
    "window_bg": "#0d1729",
    "sidebar_bg": "#101c31",
    "card_bg": "#1d293d",
    "input_bg": "#1d293d",
    "border": "#34425b",
    "input_border": "#4a5a73",
    "primary": "#8190f7",
    "primary_hover": "#929fff",
    "primary_pressed": "#6e7ee5",
    "purple": "#7a22ad",
    "text_primary": "#ffffff",
    "text_secondary": "#9aa7bd",
    "text_muted": "#66738b",
    "dark_text": "#08101e",
}
```

## Task List

### Phase 1: Foundation — Layout Shell & Theme
**Goal:** Window boots with the new 3-region layout, dark theme, and placeholder content.

- [ ] **Task 1.1**: Add Rezi color palette and font config to `app/ui/theme.py`
  - New constants: `REZI_COLORS`, `REZI_FONTS`
  - New stylesheet: `REZI_DARK_STYLESHEET` (window, sidebar, top nav, cards, inputs, buttons)
  - Font family helper: `rezi_font(size, weight)` returning QFont with Inter/Arial/Segoe fallback

- [ ] **Task 1.2**: Create `app/ui/components/rezi/__init__.py` package

- [ ] **Task 1.3**: Create `app/ui/components/rezi/sidebar.py` — `ReziSidebar(QWidget)`
  - Fixed width 80–85px, background `#101c31` with subtle gradient
  - Logo button at top (42×42, purple gradient, "R" letter)
  - 7 icon buttons with 54–58px vertical spacing
  - Bottom section: REZI EXTENSION + REZI MCP labels
  - Hover: `rgba(123,139,255,0.12)` with 8px border-radius
  - Tooltips on hover
  - Signal: `page_selected(index: int)`

- [ ] **Task 1.4**: Create `app/ui/components/rezi/top_nav.py` — `ReziTopNav(QWidget)`
  - Height ~55px, top margin ~20px
  - Left: Resume dropdown button (rounded, dark, "MOHANAD RESUME 2026 ▼")
  - Center: Horizontal tab container (scrollable) with section tabs
  - Right: "FINISH UP & PREVIEW" and "AI COVER LETTER" outlined buttons
  - Signal: `section_changed(name: str)`

- [ ] **Task 1.5**: Create `app/ui/components/rezi/section_tabs.py` — `SectionTabBar(QScrollArea)`
  - Horizontal scrollable tab bar inside bordered container
  - Selected tab: `#7d8cf8` bg, dark text, bold
  - Inactive: transparent bg, white text
  - Sections: CONTACT, EXPERIENCE, PROJECT, EDUCATION, CERTIFICATIONS, COURSEWORK, INVOLVEMENT, SKILLS, SUMMARY
  - Three-dot overflow button opening a floating menu
  - Signal: `tab_selected(name: str)`

- [ ] **Task 1.6**: Refactor `app/ui/main_window.py` — New 3-region layout
  - Remove old QListWidget sidebar
  - New layout: `QHBoxLayout` with ReziSidebar + vertical panel (ReziTopNav + QStackedWidget)
  - Minimum size: 1366×768, reference: 2048×1042
  - Responsive: sidebar fixed, top nav scrolls, content fills remaining
  - Keep existing page stack for backward compatibility

**Checkpoint 1:** Window launches with dark theme, icon sidebar, section tabs, and a blank content area. Sidebar clicks change the active icon. Tab clicks emit signals.

### Phase 2: Custom Widgets
**Goal:** Reusable form controls matching the spec.

- [ ] **Task 2.1**: Create `app/ui/components/rezi/toggle_switch.py` — `ReziToggleSwitch(QWidget)`
  - Size ~35×18px
  - Enabled: track `#8191ff`, thumb `#d8ddff`
  - Disabled: track `#344258`, thumb `#172337`
  - Animated thumb transition
  - Property: `checked: bool`, signal: `toggled(bool)`

- [ ] **Task 2.2**: Create `app/ui/components/rezi/form_field.py` — `ReziFormField(QWidget)`
  - Uppercase label (16px, bold, white)
  - Input control (bg `#1d293d`, border `#485870`, radius 5px, 17px white text)
  - Height 55–58px
  - Focus: border-color `#8493ff`
  - Optional right-side icon button (e.g., chain link for LinkedIn)
  - Optional right-side "Show on resume" toggle

- [ ] **Task 2.3**: Create `app/ui/components/rezi/dropdown.py` — `ReziDropdown(QPushButton)`
  - Styled dropdown button matching form field appearance
  - Popup list with dark theme styling
  - Signal: `selected(value: str)`

- [ ] **Task 2.4**: Create `app/ui/components/rezi/card.py` — `ReziCard(QFrame)`
  - Rounded rect card: bg `#1d293d`, border `#2b3951`, radius 11px
  - Internal padding 30px horizontal, 32px vertical
  - Two-column responsive layout inside

- [ ] **Task 2.5**: Create `app/ui/components/rezi/toast.py` — `ReziToast(QLabel)`
  - Small success toast notification
  - Auto-dismiss after 2–3 seconds
  - Positioned at bottom-right of parent

**Checkpoint 2:** All custom widgets render correctly in a test harness. Toggle animates. Form fields style consistently.

### Phase 3: Contact Form Page
**Goal:** Fully functional contact form with sample data.

- [ ] **Task 3.1**: Create `app/ui/pages/rezi_contact.py` — `ReziContactPage(QWidget)`
  - Large rounded card (75px margins, 45px top margin, ~540px height)
  - Two-column responsive form layout (28px gap)
  - Switches to single column below ~1050px window width

- [ ] **Task 3.2**: Wire form fields to `ContactInfo` domain model
  - Row 1: Full Name + Email Address
  - Row 2: Phone Number + LinkedIn URL (with chain-link icon button)
  - Row 3: Personal Website + Country dropdown
  - Row 4: State dropdown + City dropdown
  - Show on resume toggles for Country, State, City
  - Pre-populate with sample data from spec

- [ ] **Task 3.3**: Implement LinkedIn icon button
  - Chain-link icon inside the LinkedIn input's right side
  - Opens URL in default browser via `QDesktopServices.openUrl()`

- [ ] **Task 3.4**: Create `app/ui/pages/rezi_experience.py` — Placeholder Experience page
  - Same card layout with experience-specific fields
  - Can be minimal stub for now

- [ ] **Task 3.5**: Create placeholder pages for other sections
  - Education, Skills, Summary, Projects, Certifications, Coursework, Involvement
  - Each can be a minimal stub with the ReziCard wrapper

**Checkpoint 3:** Contact form displays with all fields, sample data pre-filled, toggles work, LinkedIn opens browser.

### Phase 4: Section Menu
**Goal:** Floating dropdown menu from the three-dot tab.

- [ ] **Task 4.1**: Create `app/ui/components/rezi/section_menu.py` — `SectionMenu(QWidget)`
  - Size ~190×245px
  - Background `#1d293d`, border `#33425d`, radius 10px, drop shadow
  - Checked items: purple checkbox (`#8997ff` bg, `#0d101e` checkmark)
  - "Academic" and "Other" rows with list icon + chevron + submenu support
  - Closes on click outside or Escape key
  - Signal: `section_toggled(name: str, visible: bool)`

- [ ] **Task 4.2**: Wire SectionMenu to SectionTabBar's three-dot button
  - Menu appears below the three-dot button
  - Checked items add/remove tabs from the tab bar
  - Menu state persisted in AppState

**Checkpoint 4:** Three-dot button opens menu. Checking/unchecking items shows/hides tabs. Clicking outside closes menu.

### Phase 5: Responsive Behavior & Polish
**Goal:** Window resizes gracefully, animations, keyboard nav.

- [ ] **Task 5.1**: Implement responsive layout in MainWindow
  - Sidebar fixed at 80–85px
  - Top nav tabs scroll horizontally when narrow
  - Main content margins reduce dynamically
  - Form switches to single column below ~1050px
  - Save button stays right-aligned

- [ ] **Task 5.2**: Add hover effects and transitions
  - Sidebar icon hover: background fade-in
  - Tab hover: subtle background
  - Button hover/pressed states
  - Toggle thumb animation

- [ ] **Task 5.3**: Keyboard navigation
  - Tab key cycles through form fields
  - Escape closes popups/menus
  - Arrow keys navigate sidebar icons
  - Enter activates focused element

- [ ] **Task 5.4**: Tooltips on sidebar icons
  - Show page name on hover
  - Styled with dark theme

**Checkpoint 5:** Window resizes smoothly. All hover states work. Keyboard navigation functional.

### Phase 6: Save & Validation
**Goal:** Form validation, JSON save, toast feedback.

- [ ] **Task 6.1**: Implement save button functionality
  - Validate required fields (name, email)
  - Save to `AppState` and local JSON file
  - Show success toast on save
  - Do not block with large dialog

- [ ] **Task 6.2**: Implement "Show on resume" toggle persistence
  - Toggle state saved to AppState
  - Used during export to include/exclude fields

- [ ] **Task 6.3**: Wire Resume dropdown to load saved resumes
  - Dropdown lists saved resumes from database
  - Selecting one loads it into the form

**Checkpoint 6:** Save button validates, saves JSON, shows toast. Toggles persist.

### Phase 7: Integration & Testing
**Goal:** All existing tests pass, new tests added, ruff clean.

- [ ] **Task 7.1**: Write tests for new widgets
  - Toggle switch state changes
  - Form field rendering and focus
  - Section menu show/hide
  - Save validation

- [ ] **Task 7.2**: Write tests for new pages
  - Contact form renders with sample data
  - Save button produces correct JSON
  - LinkedIn button opens URL

- [ ] **Task 7.3**: Run full test suite, fix any regressions

- [ ] **Task 7.4**: Run ruff, fix lint issues

- [ ] **Task 7.5**: Push to GitHub

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Inter font not installed on user system | Low | Fallback chain: Inter → Arial → Segoe UI |
| 20 existing pages not accessible from new sidebar | Medium | Map sidebar icons to page groups; keep old nav accessible via settings |
| PySide6 native look conflicts with custom styling | Medium | Use QSS overrides for all visible widgets |
| Responsive layout complexity | Medium | Use QSplitter and minimum size policies |

## Files Likely Touched
- `app/ui/theme.py` — New Rezi palette and styles
- `app/ui/main_window.py` — New 3-region layout
- `app/ui/components/rezi/` — New package (7+ widget files)
- `app/ui/pages/rezi_contact.py` — New contact form page
- `app/ui/pages/rezi_*.py` — Placeholder pages for other sections
- `main.py` — Font update
- `tests/test_rezi_widgets.py` — New tests
