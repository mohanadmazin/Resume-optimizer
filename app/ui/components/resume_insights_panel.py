"""ResumeInsightsPanel — right panel showing score, keywords, and issues."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.analysis import ATSResult
from app.domain.scoring import ResumeScoreReport


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

        # ── Issues list ──────────────────────────────────────────────
        issues_label = QLabel("Issues")
        issues_label.setObjectName("sectionLabel")
        root.addWidget(issues_label)

        self._issues_text = QTextEdit()
        self._issues_text.setReadOnly(True)
        self._issues_text.setObjectName("issuesText")
        self._issues_text.setMaximumHeight(150)
        root.addWidget(self._issues_text)

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
        self._clear_layout(self._cat_layout)
        self._clear_layout(self._keywords_layout)
        self._keywords_layout.addStretch()
        self._issues_text.clear()

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
        lines: list[str] = []
        if ats.score_report:
            for cat in ats.score_report.categories:
                for issue in cat.issues:
                    lines.append(f"[{issue.severity.value.upper()}] {issue.message}")
        if not lines:
            lines.append("No issues found.")
        self._issues_text.setPlainText("\n".join(lines))

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            w = child.widget()
            if w is not None:
                w.deleteLater()
