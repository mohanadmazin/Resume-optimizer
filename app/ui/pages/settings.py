"""Settings page: Ollama URL, model selection and temperature."""

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
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

from app.core.settings import settings_service


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


        self.refresh_btn = QPushButton(
            "Refresh Models"
        )

        self.refresh_btn.clicked.connect(
            self._refresh
        )


        model_row.addWidget(
            self.model_combo,
            1
        )

        model_row.addWidget(
            self.refresh_btn
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

        backup_group = QHBoxLayout()
        backup_label = QLabel("Data Backup")
        backup_label.setStyleSheet("font-weight: bold; margin-top: 12px;")
        backup_group.addWidget(backup_label)
        backup_group.addStretch()
        layout.addLayout(backup_group)

        backup_row = QHBoxLayout()
        self._backup_btn = QPushButton("Export Backup")
        self._backup_btn.clicked.connect(self._on_backup)
        self._restore_btn = QPushButton("Import Backup")
        self._restore_btn.clicked.connect(self._on_restore)
        backup_row.addWidget(self._backup_btn)
        backup_row.addWidget(self._restore_btn)
        layout.addLayout(backup_row)

        layout.addStretch()



    def on_show(self):

        settings = settings_service.settings


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
        client = OllamaClient(base_url=url or None)
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Refreshing...")
        self._worker = Worker(client.list_models)
        self._worker.result.connect(self._on_models)
        self._worker.error.connect(
            lambda msg: (
                self.refresh_btn.setEnabled(True),
                self.refresh_btn.setText("Refresh Models"),
                QMessageBox.warning(self, "Ollama unreachable", msg),
            )
        )
        self._worker.start()

    def _on_models(self, models: list):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh Models")

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

        current = settings_service.settings

        models = [
            self.model_combo.itemText(i)
            for i in range(
                self.model_combo.count()
            )
        ]


        model = (
            self.model_combo.currentText().strip()
            or current.ai.model
        )


        if model not in models:

            models.append(model)

        updated = current.model_copy(deep=True)
        updated.ai.ollama_url = (
            self.url_edit.text().strip()
            or current.ai.ollama_url
        )
        updated.ai.model = model
        updated.ai.available_models = models
        updated.ai.temperature = round(
            self.temp_spin.value(), 2
        )

        settings_service.save(updated)

        self.window.state.reload_settings()

        self.window.notify(
            "Settings saved."
        )

    def _on_backup(self) -> None:
        from app.infrastructure.backup import backup_database

        ts_path = None
        try:
            ts_path = backup_database()
            QMessageBox.information(
                self,
                "Backup Complete",
                f"Database exported to:\n{ts_path}",
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Backup Failed",
                str(exc),
            )

    def _on_restore(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Select Backup File",
            str(Path.home()),
            "SQLite Database (*.db)",
        )
        if not path_str:
            return

        from app.infrastructure.backup import restore_database

        reply = QMessageBox.question(
            self,
            "Confirm Restore",
            "This will replace your current data with the backup.\n"
            "A safety copy of the current database will be saved.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            restore_database(Path(path_str))
            QMessageBox.information(
                self,
                "Restore Complete",
                "Database restored successfully.\n"
                "Please restart the application for changes to take effect.",
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Restore Failed",
                str(exc),
            )