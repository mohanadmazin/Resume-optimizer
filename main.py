"""Resume Optimizer - local AI-powered ATS resume optimizer."""

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from app.database.db import init_db
from app.ui.main_window import MainWindow


def main():

    init_db()


    app = QApplication(
        sys.argv
    )


    app.setApplicationName(
        "Resume Optimizer"
    )


    app.setFont(
        QFont(
            "Segoe UI",
            10
        )
    )


    window = MainWindow()

    window.show()


    return app.exec()



if __name__ == "__main__":

    sys.exit(
        main()
    )