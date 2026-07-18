"""Bullet writer widget — Rezi-style 3-alternative generation with keyword highlighting."""
from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.bullet_writer import BulletEvidence, BulletSuggestion


def _highlight_keywords(text: str, keywords: list[str]) -> str:
    """Return HTML with target keywords highlighted in bold blue."""
    if not keywords:
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"<div style='font-size:13px; line-height:1.5;'>{escaped}</div>"

    # Sort longest first to avoid partial matches
    sorted_kws = sorted(keywords, key=len, reverse=True)
    pattern = re.compile(
        "|".join(re.escape(k) for k in sorted_kws),
        re.IGNORECASE,
    )

    def _replace(m: re.Match) -> str:
        kw = m.group(0)
        return (
            f'<span style="color:#2563EB; font-weight:bold;">{kw}</span>'
        )

    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    highlighted = pattern.sub(_replace, escaped)
    return f"<div style='font-size:13px; line-height:1.5;'>{highlighted}</div>"


class BulletSuggestionCard(QFrame):
    """A single bullet suggestion card with style badge, highlighted text, and Apply button."""

    applied = Signal(str)  # emits the bullet text

    STYLE_COLORS = {
        "concise": ("#7C3AED", "Concise"),
        "achievement": ("#059669", "Achievement"),
        "technical": ("#D97706", "Technical"),
    }

    def __init__(self, suggestion: BulletSuggestion, target_keywords: list[str], parent=None):
        super().__init__(parent)
        self.suggestion = suggestion
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header: style badge + review warning
        header = QHBoxLayout()

        color, label = self.STYLE_COLORS.get(suggestion.style, ("#6B7280", suggestion.style.title()))
        badge = QLabel(label.upper())
        badge.setStyleSheet(
            f"background-color: {color}; color: white; padding: 2px 8px; "
            f"border-radius: 4px; font-size: 11px; font-weight: bold;"
        )
        header.addWidget(badge)

        if suggestion.requires_review:
            review_label = QLabel("⚠ Needs Review")
            review_label.setStyleSheet("color: #D97706; font-size: 11px; font-weight: bold;")
            header.addWidget(review_label)

        header.addStretch()
        layout.addLayout(header)

        # Bullet text with keyword highlighting
        text_label = QLabel()
        text_label.setWordWrap(True)
        text_label.setTextFormat(Qt.TextFormat.RichText)
        text_label.setText(_highlight_keywords(suggestion.text, target_keywords))
        layout.addWidget(text_label)

        # Evidence fields used
        if suggestion.evidence_fields:
            evidence_text = "Evidence: " + ", ".join(suggestion.evidence_fields)
            evidence_label = QLabel(evidence_text)
            evidence_label.setStyleSheet("color: #6B7280; font-size: 11px;")
            layout.addWidget(evidence_label)

        # Keywords used
        if suggestion.used_keywords:
            kw_text = "Keywords: " + ", ".join(suggestion.used_keywords)
            kw_label = QLabel(kw_text)
            kw_label.setStyleSheet("color: #2563EB; font-size: 11px;")
            layout.addWidget(kw_label)

        # Apply button
        apply_btn = QPushButton("Apply This Bullet")
        apply_btn.clicked.connect(lambda: self.applied.emit(suggestion.text))
        layout.addWidget(apply_btn)


class BulletWriterWidget(QWidget):
    """Widget that shows 3 bullet suggestions and emits the chosen one."""

    bullet_applied = Signal(int, str)  # (experience_index, new_bullet_text)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._evidence: BulletEvidence | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._title = QLabel("Bullet Writer")
        self._title.setObjectName("cardTitle")
        layout.addWidget(self._title)

        self._cards_container = QVBoxLayout()
        layout.addLayout(self._cards_container)

        self._empty_label = QLabel("Select a bullet and click 'Rewrite Bullet' to generate alternatives.")
        self._empty_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        layout.addWidget(self._empty_label)

    def show_suggestions(
        self,
        suggestions: list[BulletSuggestion],
        evidence: BulletEvidence,
    ) -> None:
        """Display three suggestion cards."""
        self._evidence = evidence
        self._clear_cards()
        self._empty_label.hide()

        for sug in suggestions:
            card = BulletSuggestionCard(sug, evidence.target_keywords)
            card.applied.connect(lambda text: self._on_apply(text))
            self._cards_container.addWidget(card)

    def _on_apply(self, text: str) -> None:
        if self._evidence is not None:
            self.bullet_applied.emit(self._evidence.experience_index, text)

    def _clear_cards(self) -> None:
        while self._cards_container.count():
            child = self._cards_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def clear(self) -> None:
        self._clear_cards()
        self._empty_label.show()
