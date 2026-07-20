# Rezi UI Redesign — Task Checklist

## Phase 1: Foundation — Layout Shell & Theme
- [ ] 1.1 Add Rezi color palette and font config to `app/ui/theme.py`
- [ ] 1.2 Create `app/ui/components/rezi/__init__.py` package
- [ ] 1.3 Create `app/ui/components/rezi/sidebar.py` — `ReziSidebar`
- [ ] 1.4 Create `app/ui/components/rezi/top_nav.py` — `ReziTopNav`
- [ ] 1.5 Create `app/ui/components/rezi/section_tabs.py` — `SectionTabBar`
- [ ] 1.6 Refactor `app/ui/main_window.py` — New 3-region layout

**Checkpoint 1:** Window launches with dark theme, icon sidebar, section tabs.

## Phase 2: Custom Widgets
- [ ] 2.1 Create `app/ui/components/rezi/toggle_switch.py`
- [ ] 2.2 Create `app/ui/components/rezi/form_field.py`
- [ ] 2.3 Create `app/ui/components/rezi/dropdown.py`
- [ ] 2.4 Create `app/ui/components/rezi/card.py`
- [ ] 2.5 Create `app/ui/components/rezi/toast.py`

**Checkpoint 2:** All custom widgets render correctly.

## Phase 3: Contact Form Page
- [ ] 3.1 Create `app/ui/pages/rezi_contact.py` — Main contact form
- [ ] 3.2 Wire form fields to ContactInfo domain model
- [ ] 3.3 Implement LinkedIn icon button (open in browser)
- [ ] 3.4 Create placeholder Experience page
- [ ] 3.5 Create placeholder pages for other sections

**Checkpoint 3:** Contact form displays with all fields and sample data.

## Phase 4: Section Menu
- [ ] 4.1 Create `app/ui/components/rezi/section_menu.py`
- [ ] 4.2 Wire SectionMenu to SectionTabBar's three-dot button

**Checkpoint 4:** Menu opens, toggles work, closes on outside click.

## Phase 5: Responsive Behavior & Polish
- [ ] 5.1 Implement responsive layout in MainWindow
- [ ] 5.2 Add hover effects and transitions
- [ ] 5.3 Keyboard navigation
- [ ] 5.4 Tooltips on sidebar icons

**Checkpoint 5:** Window resizes smoothly, all hover states work.

## Phase 6: Save & Validation
- [ ] 6.1 Implement save button functionality
- [ ] 6.2 Implement "Show on resume" toggle persistence
- [ ] 6.3 Wire Resume dropdown to load saved resumes

**Checkpoint 6:** Save validates, saves JSON, shows toast.

## Phase 7: Integration & Testing
- [ ] 7.1 Write tests for new widgets
- [ ] 7.2 Write tests for new pages
- [ ] 7.3 Run full test suite, fix regressions
- [ ] 7.4 Run ruff, fix lint
- [ ] 7.5 Push to GitHub
