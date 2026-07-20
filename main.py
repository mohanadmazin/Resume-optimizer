"""Resume Optimizer - local AI-powered ATS resume optimizer."""

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.database.migrate import run_migrations
from app.logging_config import setup_logging
from app.ui.main_window import MainWindow


def main():
    setup_logging()
    run_migrations()

    app = QApplication(sys.argv)
    app.setApplicationName("Resume Optimizer")
    app.setFont(QFont("Inter", 10))

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
