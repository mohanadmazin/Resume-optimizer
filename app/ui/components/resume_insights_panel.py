"""ResumeInsightsPanel — right panel showing score, keywords, and issues."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.domain.analysis import ATSResult
from app.domain.content_check import ContentCheckResult
from app.domain.keyword_targeting import KeywordTarget
from app.domain.scoring import ResumeScoreReport
from app.engines.resume_scorer import ResumeScore


class _ScoreCard(QFrame):
    """Small labelled score card."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("scoreCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        self._title = QLabel(title.upper())
        self._title.setObjectName("cardTitle")
        self._value = QLabel("--")
        self._value.setObjectName("scoreValue")
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title)
        layout.addWidget(self._value)

    def set_value(self, text: str) -> None:
        self._value.setText(text)


class ResumeInsightsPanel(QWidget):
    """Right-hand panel showing ATS score breakdown, missing keywords, and issues."""

    issue_selected = Signal(str)
    suggestion_accepted = Signal(str)
    suggestion_rejected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("insightsPanel")
        self.setFixedWidth(280)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 8)
        root.setSpacing(8)

        header = QLabel("INSIGHTS")
        header.setObjectName("navHeader")
        root.addWidget(header)

        # ── Score cards ──────────────────────────────────────────────
        cards_row = QHBoxLayout()
        self.ats_card = _ScoreCard("ATS")
        self.match_card = _ScoreCard("Match %")
        self.skills_card = _ScoreCard("Skills %")
        cards_row.addWidget(self.ats_card)
        cards_row.addWidget(self.match_card)
        cards_row.addWidget(self.skills_card)
        root.addLayout(cards_row)

        cards_row2 = QHBoxLayout()
        self.content_card = _ScoreCard("Content")
        self.resume_score_card = _ScoreCard("Resume")
        cards_row2.addWidget(self.content_card)
        cards_row2.addWidget(self.resume_score_card)
        cards_row2.addStretch()
        root.addLayout(cards_row2)

        # ── Category breakdown ───────────────────────────────────────
        cat_label = QLabel("Category Breakdown")
        cat_label.setObjectName("sectionLabel")
        root.addWidget(cat_label)

        self._cat_frame = QFrame()
        self._cat_frame.setObjectName("catBreakdown")
        self._cat_layout = QVBoxLayout(self._cat_frame)
        self._cat_layout.setContentsMargins(4, 4, 4, 4)
        self._cat_layout.setSpacing(2)
        root.addWidget(self._cat_frame)

        # ── Missing keywords ─────────────────────────────────────────
        kw_label = QLabel("Missing Keywords")
        kw_label.setObjectName("sectionLabel")
        root.addWidget(kw_label)

        self._keywords_area = QScrollArea()
        self._keywords_area.setWidgetResizable(True)
        self._keywords_area.setFrameShape(QFrame.Shape.NoFrame)
        self._keywords_container = QWidget()
        self._keywords_layout = QVBoxLayout(self._keywords_container)
        self._keywords_layout.setContentsMargins(0, 0, 0, 0)
        self._keywords_layout.setSpacing(2)
        self._keywords_layout.addStretch()
        self._keywords_area.setWidget(self._keywords_container)
        root.addWidget(self._keywords_area, 1)

        # ── Skill suggestions ────────────────────────────────────────
        sug_label = QLabel("Skill Suggestions")
        sug_label.setObjectName("sectionLabel")
        root.addWidget(sug_label)

        self._suggestions_scroll = QScrollArea()
        self._suggestions_scroll.setWidgetResizable(True)
        self._suggestions_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._suggestions_container = QWidget()
        self._suggestions_layout = QVBoxLayout(self._suggestions_container)
        self._suggestions_layout.setContentsMargins(0, 0, 0, 0)
        self._suggestions_layout.setSpacing(4)
        self._suggestions_layout.addStretch()
        self._suggestions_scroll.setWidget(self._suggestions_container)
        root.addWidget(self._suggestions_scroll, 1)

        # ── Issues list ──────────────────────────────────────────────
        issues_label = QLabel("Issues")
        issues_label.setObjectName("sectionLabel")
        root.addWidget(issues_label)

        self._issues_scroll = QScrollArea()
        self._issues_scroll.setWidgetResizable(True)
        self._issues_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._issues_container = QWidget()
        self._issues_layout = QVBoxLayout(self._issues_container)
        self._issues_layout.setContentsMargins(0, 0, 0, 0)
        self._issues_layout.setSpacing(2)
        self._issues_layout.addStretch()
        self._issues_scroll.setWidget(self._issues_container)
        root.addWidget(self._issues_scroll)

    # ── Public update API ────────────────────────────────────────────

    def update_from_ats(self, ats: ATSResult | None) -> None:
        """Refresh all panel contents from an ATSResult."""
        if ats is None:
            self.clear()
            return

        self.ats_card.set_value(str(ats.ats_score))
        self.match_card.set_value(f"{ats.keyword_match_pct}%")
        self.skills_card.set_value(f"{ats.skills_match_pct}%")

        self._update_categories(ats.score_report)
        self._update_keywords(ats.missing_keywords)
        self._update_issues(ats)

    def clear(self) -> None:
        self.ats_card.set_value("--")
        self.match_card.set_value("--")
        self.skills_card.set_value("--")
        self.content_card.set_value("--")
        self.resume_score_card.set_value("--")
        self._clear_layout(self._cat_layout)
        self._clear_layout(self._keywords_layout)
        self._keywords_layout.addStretch()
        self._clear_layout(self._suggestions_layout)
        self._suggestions_layout.addStretch()
        self._clear_layout(self._issues_layout)
        self._issues_layout.addStretch()

    def update_from_content_check(self, result: ContentCheckResult | None) -> None:
        """Update the content quality card and add content issues to issues list."""
        if result is None:
            self.content_card.set_value("--")
            return
        self.content_card.set_value(f"{result.score}")
        if result.score < 70:
            self.content_card._value.setStyleSheet(
                "color: #ff5c5c; font-size: 16px; font-weight: bold;"
            )
        elif result.score < 85:
            self.content_card._value.setStyleSheet(
                "color: #e6a817; font-size: 16px; font-weight: bold;"
            )
        else:
            self.content_card._value.setStyleSheet(
                "color: #5adc5a; font-size: 16px; font-weight: bold;"
            )

    def update_from_resume_score(self, score: ResumeScore | None) -> None:
        """Update the resume score card."""
        if score is None:
            self.resume_score_card.set_value("--")
            return
        self.resume_score_card.set_value(f"{score.overall:.0f}")
        if score.overall < 60:
            self.resume_score_card._value.setStyleSheet(
                "color: #ff5c5c; font-size: 16px; font-weight: bold;"
            )
        elif score.overall < 80:
            self.resume_score_card._value.setStyleSheet(
                "color: #e6a817; font-size: 16px; font-weight: bold;"
            )
        else:
            self.resume_score_card._value.setStyleSheet(
                "color: #5adc5a; font-size: 16px; font-weight: bold;"
            )

    def update_from_suggestions(self, targets: list[KeywordTarget]) -> None:
        """Show keyword suggestions with Accept/Reject buttons."""
        self._clear_layout(self._suggestions_layout)
        missing = [t for t in targets if t.status.value in ("missing", "partial")]
        if not missing:
            lbl = QLabel("No suggestions available")
            lbl.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
            self._suggestions_layout.addWidget(lbl)
            self._suggestions_layout.addStretch()
            return
        for target in missing[:10]:
            row = QFrame()
            row.setObjectName("suggestionRow")
            row.setStyleSheet(
                "QFrame{suggestionRow}{border: 1px solid #444; border-radius: 3px;"
                "padding: 4px; background: #1e1e1e;}"
            )
            inner = QVBoxLayout(row)
            inner.setContentsMargins(4, 4, 4, 4)
            inner.setSpacing(2)

            name_row = QHBoxLayout()
            status_color = "#e6a817" if target.status.value == "partial" else "#ff5c5c"
            name_lbl = QLabel(
                f"<b>{target.canonical_name}</b> "
                f"<span style='color:{status_color};font-size:10px;'>"
                f"{target.status.value.upper()}</span>"
            )
            name_lbl.setStyleSheet("font-size: 11px;")
            name_row.addWidget(name_lbl)
            name_row.addStretch()
            inner.addLayout(name_row)

            if target.suggested_paths:
                path_lbl = QLabel(f"Add to: {', '.join(target.suggested_paths[:2])}")
                path_lbl.setStyleSheet("color: #999; font-size: 10px;")
                inner.addWidget(path_lbl)

            btn_row = QHBoxLayout()
            accept_btn = QPushButton("Accept")
            accept_btn.setFixedHeight(22)
            accept_btn.setStyleSheet(
                "QPushButton{font-size:10px;padding:2px 8px;border:1px solid #5a5;"
                "border-radius:3px;background:transparent;}"
                "QPushButton:hover{background:#2a4a2a;}"
            )
            accept_btn.clicked.connect(
                lambda checked=False, name=target.canonical_name: (
                    self.suggestion_accepted.emit(name)
                )
            )
            btn_row.addWidget(accept_btn)

            reject_btn = QPushButton("Reject")
            reject_btn.setFixedHeight(22)
            reject_btn.setStyleSheet(
                "QPushButton{font-size:10px;padding:2px 8px;border:1px solid #555;"
                "border-radius:3px;background:transparent;}"
                "QPushButton:hover{background:#3a2a2a;}"
            )
            reject_btn.clicked.connect(
                lambda checked=False, name=target.canonical_name: (
                    self.suggestion_rejected.emit(name)
                )
            )
            btn_row.addWidget(reject_btn)
            btn_row.addStretch()
            inner.addLayout(btn_row)

            self._suggestions_layout.addWidget(row)
        self._suggestions_layout.addStretch()

    # ── Internal ─────────────────────────────────────────────────────

    def _update_categories(self, report: ResumeScoreReport | None) -> None:
        self._clear_layout(self._cat_layout)
        if report is None:
            self._cat_layout.addStretch()
            return
        for cat in report.categories:
            row = QHBoxLayout()
            name = QLabel(cat.category.value.replace("_", " ").title())
            name.setStyleSheet("font-size: 11px;")
            bar = QLabel(f"{cat.score}")
            bar.setStyleSheet("font-size: 11px; font-weight: bold;")
            row.addWidget(name)
            row.addStretch()
            row.addWidget(bar)
            self._cat_layout.addLayout(row)
        self._cat_layout.addStretch()

    def _update_keywords(self, keywords: list[str]) -> None:
        self._clear_layout(self._keywords_layout)
        if not keywords:
            empty = QLabel("No missing keywords")
            empty.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
            self._keywords_layout.addWidget(empty)
        else:
            for kw in keywords[:15]:
                lbl = QLabel(f"• {kw}")
                lbl.setStyleSheet("font-size: 11px;")
                lbl.setWordWrap(True)
                self._keywords_layout.addWidget(lbl)
        self._keywords_layout.addStretch()

    def _update_issues(self, ats: ATSResult) -> None:
        self._clear_layout(self._issues_layout)
        _SECTION_MAP = {
            "content": "Summary",
            "format": "Contact",
            "optimization": "Skills",
            "best_practices": "Experience",
            "application_ready": "Summary",
        }
        found = False
        if ats.score_report:
            for cat in ats.score_report.categories:
                for issue in cat.issues:
                    found = True
                    section = _SECTION_MAP.get(cat.category.value, "Summary")
                    btn = QPushButton(
                        f"[{issue.severity.value.upper()}] {issue.message}"
                    )
                    btn.setObjectName("issueButton")
                    btn.setCheckable(False)
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setStyleSheet(
                        "text-align: left; padding: 4px 6px; font-size: 11px;"
                        "border: 1px solid transparent; border-radius: 3px;"
                        "background: transparent;"
                        "QPushButton:hover{border: 1px solid #555; background: #2a2a2a;}"
                    )
                    btn.clicked.connect(
                        lambda checked=False, s=section: self.issue_selected.emit(s)
                    )
                    self._issues_layout.addWidget(btn)
        if not found:
            lbl = QLabel("No issues found.")
            lbl.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
            self._issues_layout.addWidget(lbl)
        self._issues_layout.addStretch()

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            w = child.widget()
            if w is not None:
                w.deleteLater()
