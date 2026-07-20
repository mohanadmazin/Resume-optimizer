# app/ui/pages/rezi_contact.py
"""Rezi-style contact form page."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.components.rezi.card import ReziCard
from app.ui.components.rezi.dropdown import ReziDropdown
from app.ui.components.rezi.form_field import ReziFormField
from app.ui.components.rezi.toast import ReziToast
from app.ui.theme import REZI_COLORS


REZI_FONT_FAMILY = "Inter, Arial, Segoe UI, sans-serif"


class ReziContactPage(QWidget):
    """Contact information form with Rezi-style dark theme."""

    def __init__(self, state=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._toast = ReziToast("", self)

        # Scroll area wrapper
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(75, 25, 75, 25)
        main_layout.setSpacing(0)

        # ── Card ──
        card = ReziCard()

        # Two-column grid
        grid = QHBoxLayout()
        grid.setSpacing(28)

        left_col = QVBoxLayout()
        left_col.setSpacing(18)
        right_col = QVBoxLayout()
        right_col.setSpacing(18)

        # Row 1
        self._name_field = ReziFormField("Full Name", value="Mohanad Mazin A. Fathi")
        left_col.addWidget(self._name_field)

        self._email_field = ReziFormField("Email Address", value="mohanad.a.fathi@gmail.com")
        right_col.addWidget(self._email_field)

        # Row 2
        self._phone_field = ReziFormField("Phone Number", value="(+60)1127670002")
        left_col.addWidget(self._phone_field)

        self._linkedin_field = ReziFormField(
            "LinkedIn URL",
            value="https://linkedin.com/in/mohanad-a-fathi",
            show_icon=True,
            icon_tooltip="Open LinkedIn profile",
        )
        self._linkedin_field.icon_clicked.connect(self._open_linkedin)
        right_col.addWidget(self._linkedin_field)

        # Row 3
        self._website_field = ReziFormField(
            "Personal Website or Relevant Link",
            placeholder="https://www.example.com",
        )
        left_col.addWidget(self._website_field)

        self._country_dropdown = ReziDropdown(
            "Country",
            value="Malaysia",
            items=["Malaysia", "United States", "United Kingdom", "Canada", "Australia",
                   "Germany", "France", "Japan", "Singapore", "UAE", "India"],
        )
        right_col.addWidget(self._country_dropdown)

        # Row 4
        self._state_dropdown = ReziDropdown(
            "State",
            value="Kuala Lumpur",
            items=["Kuala Lumpur", "Selangor", "Johor", "Penang", "Perak", "Sarawak", "Sabah"],
        )
        left_col.addWidget(self._state_dropdown)

        self._city_dropdown = ReziDropdown(
            "City",
            value="Kuala Lumpur",
            items=["Kuala Lumpur", "Petaling Jaya", "Shah Alam", "Subang Jaya", "George Town", "Johor Bahru"],
        )
        right_col.addWidget(self._city_dropdown)

        # ── Build grid ──
        grid.addLayout(left_col, 1)
        grid.addLayout(right_col, 1)
        card.card_layout.addLayout(grid)

        # ── Save button ──
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 24, 0, 0)
        btn_row.addStretch()

        self._save_btn = QPushButton("SAVE BASIC INFO")
        self._save_btn.setFixedSize(160, 48)
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {REZI_COLORS['primary']};"
            f"  color: {REZI_COLORS['dark_text']};"
            f"  font-family: {REZI_FONT_FAMILY};"
            f"  font-size: 13px;"
            f"  font-weight: 900;"
            f"  border: none;"
            f"  border-radius: 7px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {REZI_COLORS['primary_hover']};"
            f"}}"
            f"QPushButton:pressed {{"
            f"  background-color: {REZI_COLORS['primary_pressed']};"
            f"}}"
        )
        self._save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self._save_btn)
        card.card_layout.addLayout(btn_row)

        main_layout.addWidget(card)
        main_layout.addStretch()

        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_save(self) -> None:
        """Validate and save form data to JSON."""
        name = self._name_field.value().strip()
        email = self._email_field.value().strip()

        if not name or not email:
            self._toast.setText("Please fill in at least Full Name and Email.")
            self._toast.show_toast()
            return

        data = {
            "full_name": name,
            "email": email,
            "phone": self._phone_field.value(),
            "linkedin": self._linkedin_field.value(),
            "website": self._website_field.value(),
            "country": self._country_dropdown.value(),
            "state": self._state_dropdown.value(),
            "city": self._city_dropdown.value(),
            "show_country": True,
            "show_state": True,
            "show_city": False,
        }

        # Save to file
        save_path = Path.home() / ".resume_optimizer" / "contact.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Update state if available
        if self._state is not None:
            from app.domain.resume import ContactInfo
            self._state.resume = type(self._state.resume).model_copy(
                update={"contact": ContactInfo(
                    name=name, email=email, phone=data["phone"],
                    linkedin=data["linkedin"], website=data["website"],
                )} if self._state.resume else {}
            ) if self._state.resume else None

        self._toast.setText(f"Saved to {save_path}")
        self._toast.show_toast()

    def _open_linkedin(self) -> None:
        """Open LinkedIn URL in default browser."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        url = self._linkedin_field.value().strip()
        if url:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            QDesktopServices.openUrl(QUrl(url))
