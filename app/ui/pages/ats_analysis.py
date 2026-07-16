from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database import db
from app.schemas import ResumeData
from app.services.ats_engine import analyze


def _card(title: str) -> tuple[QFrame, QLabel]:
    frame = QFrame()
    frame.setObjectName("card")

    layout = QVBoxLayout(frame)

    label = QLabel(title.upper())
    label.setObjectName("cardTitle")

    value = QLabel("--")
    value.setObjectName("scoreValue")
    value.setAlignment(Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(label)
    layout.addWidget(value)

    return frame, value


class ATSAnalysisPage(QWidget):

    def __init__(self, window):
        super().__init__()

        self.window = window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("ATS Analysis")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        run_btn = QPushButton("Run ATS Analysis")
        run_btn.clicked.connect(self._run)
        layout.addWidget(run_btn)

        # Score cards
        cards = QHBoxLayout()

        card1, self.score_value = _card("ATS Score")
        card2, self.keyword_value = _card("Keyword Match")
        card3, self.skills_value = _card("Skills Match")

        for card in (card1, card2, card3):
            cards.addWidget(card)

        layout.addLayout(cards)

        # Main columns
        columns = QHBoxLayout()

        # Keywords side
        left = QVBoxLayout()

        left.addWidget(QLabel("Missing keywords:"))

        self.select_all_checkbox = QCheckBox(
            "Select / Unselect All ATS Words"
        )
        self.select_all_checkbox.stateChanged.connect(
            self._toggle_all_keywords
        )

        left.addWidget(self.select_all_checkbox)

        self.keywords_list = QListWidget()
        self.keywords_list.itemChanged.connect(
            self._update_select_all_checkbox
        )

        left.addWidget(self.keywords_list)

        # Suggestions side
        right = QVBoxLayout()

        right.addWidget(QLabel("Improvement suggestions:"))

        self.suggestions = QTextEdit()
        self.suggestions.setReadOnly(True)

        right.addWidget(self.suggestions)

        columns.addLayout(left, 1)
        columns.addLayout(right, 1)

        layout.addLayout(columns, 1)


    def _update_select_all_checkbox(self):
        if self.keywords_list.count() == 0:
            return

        all_checked = all(
            self.keywords_list.item(i).checkState()
            == Qt.CheckState.Checked
            for i in range(self.keywords_list.count())
        )

        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setChecked(all_checked)
        self.select_all_checkbox.blockSignals(False)


    def _toggle_all_keywords(self, state):
        checked = (
            state == Qt.CheckState.Checked.value
        )

        self.keywords_list.blockSignals(True)

        for i in range(self.keywords_list.count()):
            item = self.keywords_list.item(i)

            item.setCheckState(
                Qt.CheckState.Checked
                if checked
                else Qt.CheckState.Unchecked
            )

        self.keywords_list.blockSignals(False)


    def _load_fallbacks(self) -> None:
        state = self.window.state

        if state.resume is None:
            row = db.latest_resume()

            if row:
                state.resume = ResumeData.model_validate_json(
                    row["data_json"]
                )
                state.resume_id = row["id"]

        if not state.job_text:
            row = db.latest_job()

            if row:
                state.job_text = row["content"]
                state.job_title = row["title"]
                state.job_id = row["id"]


    def on_show(self):
        """Load resume and job when page is shown."""
        self._load_fallbacks()

    def _run(self) -> None:
        self.run_analysis()

    def run_analysis(self, silent: bool = False) -> None:
        """Run ATS analysis — can be called internally or from another page."""
        state = self.window.state

        self._load_fallbacks()

        if state.resume is None or not state.job_text.strip():
            if not silent:
                QMessageBox.warning(
                    self,
                    "Missing input",
                    "Import a resume and add a job description first."
                )
            return


        result = analyze(
            state.resume,
            state.job_text
        )

        state.ats = result


        # Update scores
        self.score_value.setText(
            str(result.ats_score)
        )

        self.keyword_value.setText(
            f"{result.keyword_match_pct}%"
        )

        self.skills_value.setText(
            f"{result.skills_match_pct}%"
        )


        # Load keywords
        self.keywords_list.blockSignals(True)

        self.keywords_list.clear()


        for keyword in result.missing_keywords:

            item = QListWidgetItem(keyword)

            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
            )

            # Default selected
            item.setCheckState(
                Qt.CheckState.Checked
            )

            self.keywords_list.addItem(item)


        self.keywords_list.blockSignals(False)


        # Master checkbox selected
        self.select_all_checkbox.blockSignals(True)

        self.select_all_checkbox.setChecked(True)

        self.select_all_checkbox.blockSignals(False)


        # Show suggestions
        self.suggestions.clear()

        if result.suggestions:

            self.suggestions.setPlainText(
                "\n".join(
                    f"• {s}"
                    for s in result.suggestions
                )
            )

        else:

            self.suggestions.setPlainText(
                "No improvement suggestions available."
            )


        # Save analysis
        if state.resume_id is None:

            state.resume_id = db.save_resume(
                state.resume.contact.name
                or "Resume",

                state.resume.model_dump_json(),

                state.resume.raw_text,
            )


        if state.job_id is None:

            state.job_id = db.save_job(
                state.job_title
                or "Untitled Job",

                state.job_text,
            )


        db.save_analysis(
            state.resume_id,
            state.job_id,
            result.to_dict()
        )


        self.window.notify(
            f"ATS analysis complete - score {result.ats_score}/100."
        )