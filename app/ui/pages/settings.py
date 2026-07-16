"""Settings page: Ollama URL, model selection and temperature."""

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ai.ollama_client import OllamaClient
from app.ui.workers import Worker

from app.core.settings import load_settings, save_settings, AppSettings


class SettingsPage(QWidget):

    def __init__(self, window):
        super().__init__()

        self.window = window
        self._worker = None

        self.setup_ui()

        self.on_show()


    def setup_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            24,
            24,
            24,
            24
        )

        layout.setSpacing(12)


        title = QLabel("Settings")

        title.setObjectName(
            "pageTitle"
        )

        layout.addWidget(title)


        form = QFormLayout()


        self.url_edit = QLineEdit()

        form.addRow(
            "Ollama URL:",
            self.url_edit
        )


        model_row = QHBoxLayout()

        self.model_combo = QComboBox()

        self.model_combo.setEditable(
            True
        )


        refresh_btn = QPushButton(
            "Refresh Models"
        )

        refresh_btn.clicked.connect(
            self._refresh
        )


        model_row.addWidget(
            self.model_combo,
            1
        )

        model_row.addWidget(
            refresh_btn
        )


        form.addRow(
            "Model:",
            model_row
        )


        self.temp_spin = QDoubleSpinBox()

        self.temp_spin.setRange(
            0.0,
            1.0
        )

        self.temp_spin.setSingleStep(
            0.05
        )


        form.addRow(
            "Temperature:",
            self.temp_spin
        )


        layout.addLayout(
            form
        )


        save_btn = QPushButton(
            "Save Settings"
        )

        save_btn.clicked.connect(
            self._save
        )


        layout.addWidget(
            save_btn
        )


        layout.addStretch()



    def on_show(self):

        settings = load_settings()


        self.url_edit.setText(
            settings.ai.ollama_url
        )


        self.model_combo.clear()


        self.model_combo.addItems(
            settings.ai.available_models
        )


        self.model_combo.setCurrentText(
            settings.ai.model
        )


        self.temp_spin.setValue(
            settings.ai.temperature
        )



    def _refresh(self):

        url = self.url_edit.text().strip()


        client = OllamaClient(
            base_url=url or None
        )


        self._worker = Worker(
            client.list_models
        )


        self._worker.result.connect(
            self._on_models
        )


        self._worker.error.connect(
            lambda msg:
            QMessageBox.warning(
                self,
                "Ollama unreachable",
                msg
            )
        )


        self._worker.start()



    def _on_models(self, models: list):

        if not models:

            QMessageBox.information(
                self,
                "No models",
                "Ollama is running but no models were found."
            )

            return


        current = self.model_combo.currentText()


        self.model_combo.clear()


        self.model_combo.addItems(
            models
        )


        if current in models:

            self.model_combo.setCurrentText(
                current
            )


        self.window.notify(
            f"Found {len(models)} Ollama model(s)."
        )



    def _save(self):

        settings = load_settings()


        models = [
            self.model_combo.itemText(i)
            for i in range(
                self.model_combo.count()
            )
        ]


        model = (
            self.model_combo.currentText().strip()
            or settings.ai.model
        )


        if model not in models:

            models.append(model)


        settings.ai.ollama_url = (
            self.url_edit.text().strip()
            or settings.ai.ollama_url
        )
        settings.ai.model = model
        settings.ai.available_models = models
        settings.ai.temperature = round(
            self.temp_spin.value(), 2
        )


        save_settings(settings)

        # Update the Ollama status indicator in MainWindow
        if hasattr(self.window, 'ollama_status'):
            self.window.ollama_status.set_base_url(settings.ai.ollama_url)

        self.window.notify(
            "Settings saved."
        )