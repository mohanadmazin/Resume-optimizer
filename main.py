"""Resume Optimizer - local AI-powered ATS resume optimizer."""

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.database.engine import init_db
from app.logging_config import setup_logging
from app.ui.main_window import MainWindow


def main():
    setup_logging()
    init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("Resume Optimizer")
    app.setFont(QFont("Segoe UI", 10))

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
